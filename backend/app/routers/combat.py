"""Combat routes — turn-based combat actions."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import get_supabase_client, maybe_single_data
from app.core.auth import get_current_user
from app.models.schemas import CombatActionRequest
from app.services.combat import (
    CombatManager, roll_dice, saving_throw, calc_mod,
)
from app.services.ai_manager import call_claude
from app.data.spells import SPELLS, CLASS_SPELL_ABILITY

router = APIRouter(prefix="/api/campaigns/{campaign_id}/combat", tags=["combat"])

cm = CombatManager()


def _load_combat_state(db, campaign_id: str, user_id: str):
    """Load character and active combat session."""
    campaign = (
        db.table("campaigns")
        .select("id")
        .eq("id", campaign_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    ).data
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    character = maybe_single_data(
        db.table("characters").select("*").eq("campaign_id", campaign_id)
    )
    if not character:
        raise HTTPException(status_code=400, detail="No character")
    if not character["is_alive"]:
        raise HTTPException(status_code=400, detail="Character is dead")

    combat = maybe_single_data(
        db.table("combat_sessions")
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("status", "active")
    )
    if not combat:
        raise HTTPException(status_code=400, detail="No active combat")

    return character, combat


def _get_equipped_weapon(db, character_id: str) -> dict:
    """Get the equipped weapon, or return a default unarmed attack."""
    slot = maybe_single_data(
        db.table("equipment_slots")
        .select("item_id, item_instances(id, item_templates(name, name_ru, damage_dice, type))")
        .eq("character_id", character_id)
        .eq("slot", "weapon")
    )
    if slot and slot.get("item_id") and slot.get("item_instances"):
        tmpl = slot["item_instances"].get("item_templates", {})
        return {
            "name": tmpl.get("name_ru") or tmpl.get("name", "Weapon"),
            "damage_dice": tmpl.get("damage_dice", "1d6"),
            "type": "melee",  # default
        }
    return {"name": "Кулак", "damage_dice": "1d4", "type": "melee"}


def _parse_target(details: str, enemies: list[dict]) -> int:
    """Parse target enemy index from action details."""
    if not details or not enemies:
        return 0
    details_lower = details.lower()
    for i, e in enumerate(enemies):
        if e.get("name", "").lower() in details_lower:
            return i
    # Try numeric index
    try:
        idx = int(details) - 1
        if 0 <= idx < len(enemies):
            return idx
    except ValueError:
        pass
    return 0


async def _combat_narrative(events: list[dict]) -> str:
    """Generate a brief combat narrative from events."""
    events_text = "\n".join(
        f"- {e.get('description', str(e))}" for e in events[-6:]
    )
    try:
        text = await call_claude(
            system="You are a D&D combat narrator. Describe the following combat events in 2-3 vivid sentences in Russian. Be dramatic but concise. No JSON, just narrative text.",
            messages=[{"role": "user", "content": events_text}],
            max_tokens=300,
        )
        return text
    except Exception:
        return "Бой продолжается..."


@router.get("/status")
async def combat_status(
    campaign_id: str,
    user: dict = Depends(get_current_user),
):
    """Get active combat state, or null if no active combat."""
    db = get_supabase_client()

    combat = maybe_single_data(
        db.table("combat_sessions")
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("status", "active")
    )
    if not combat:
        return None

    return {
        "id": combat["id"],
        "enemies": combat["enemies"],
        "round": combat.get("round", 1),
        "log": combat.get("log", []),
        "status": combat["status"],
    }


@router.post("/action")
async def combat_action(
    campaign_id: str,
    body: CombatActionRequest,
    user: dict = Depends(get_current_user),
):
    """Execute a combat action: attack, spell, item, flee, or custom."""
    db = get_supabase_client()
    character, combat = _load_combat_state(db, campaign_id, user["id"])

    enemies = combat["enemies"]
    combat_log = combat.get("log", [])
    round_num = combat.get("round", 1)
    alive_enemies = [e for e in enemies if e.get("hp", 0) > 0]

    if not alive_enemies:
        # Combat should already be over
        db.table("combat_sessions").update({"status": "victory"}).eq("id", combat["id"]).execute()
        return {"narrative": "Бой окончен.", "combat_status": "victory", "enemies": [], "round": round_num, "character_hp": character["hp"]}

    events = []
    player_result = None

    # ── PLAYER ACTION ──

    if body.action == "attack":
        target_idx = _parse_target(body.details, alive_enemies)
        target = alive_enemies[target_idx]
        weapon = _get_equipped_weapon(db, character["id"])

        result = await cm.player_attack(character, target, weapon)
        player_result = {
            "type": "attack",
            "target": target["name"],
            "weapon": weapon["name"],
            **result,
        }

        if result["hint"] == "critical_hit":
            events.append({"description": f"{character['name']} критически бьёт {target['name']} оружием {weapon['name']} на {result['damage']} урона!"})
        elif result["hint"] == "hit":
            events.append({"description": f"{character['name']} бьёт {target['name']} на {result['damage']} урона (бросок: {result['result']['roll']}+{result['result']['modifier']}={result['result']['total']})"})
        elif result["hint"] == "fumble":
            events.append({"description": f"{character['name']} критически промахивается!"})
        else:
            events.append({"description": f"{character['name']} промахивается по {target['name']} (бросок: {result['result']['roll']}+{result['result']['modifier']}={result['result']['total']} vs AC {target['ac']})"})

    elif body.action == "spell":
        spell_key = None
        details_lower = (body.details or "").lower().strip()
        known = character.get("known_spells", [])

        for key in known:
            spell = SPELLS.get(key, {})
            if (key == details_lower
                    or spell.get("name", "").lower() == details_lower
                    or spell.get("name_ru", "").lower() == details_lower):
                spell_key = key
                break

        if not spell_key:
            raise HTTPException(status_code=400, detail="Unknown spell. Available: " + ", ".join(
                SPELLS[k].get("name_ru", k) for k in known if k in SPELLS
            ))

        spell = SPELLS[spell_key]

        # Check and consume spell slot
        if spell["level"] > 0:
            slots = dict(character.get("spell_slots", {}))
            level_key = str(spell["level"])
            if slots.get(level_key, 0) <= 0:
                raise HTTPException(status_code=400, detail=f"No level {spell['level']} spell slots remaining")
            slots[level_key] = slots[level_key] - 1
            db.table("characters").update({"spell_slots": slots}).eq("id", character["id"]).execute()
            character["spell_slots"] = slots

        # Resolve spell effect
        target = alive_enemies[0]
        damage = 0
        healing = 0

        if spell.get("damage_dice"):
            if spell.get("auto_hit"):
                dmg, _ = roll_dice(spell["damage_dice"])
                damage = dmg
            elif spell.get("save"):
                # Save-based spell
                save_stat_map = {"dex": 12, "con": 12, "wis": 12, "str": 12}
                dc = 8 + 2 + calc_mod(character.get(CLASS_SPELL_ABILITY.get(character["class"], "int_"), 10))
                # Enemy saves with a flat bonus
                save_roll = saving_throw(target.get("save_bonus", 10), dc)
                dmg, _ = roll_dice(spell["damage_dice"])
                if save_roll["success"]:
                    damage = dmg // 2
                    events.append({"description": f"{target['name']} делает спасбросок (бросок {save_roll['roll']}) — половина урона!"})
                else:
                    damage = dmg
            else:
                # Attack roll spell
                spell_ability = CLASS_SPELL_ABILITY.get(character["class"], "int_")
                spell_stat = character.get(spell_ability, 10)
                from app.services.combat import attack_roll
                atk = attack_roll(spell_stat, target["ac"])
                if atk["hit"]:
                    dmg, _ = roll_dice(spell["damage_dice"])
                    damage = dmg if not atk["is_crit"] else dmg * 2
                else:
                    events.append({"description": f"{character['name']} промахивается заклинанием {spell['name_ru']}!"})

            if damage > 0:
                target["hp"] = max(0, target["hp"] - damage)
                events.append({"description": f"{character['name']} использует {spell['name_ru']} по {target['name']} на {damage} урона ({spell.get('damage_type', 'magic')})!"})

        elif spell.get("heal_dice"):
            spell_ability = CLASS_SPELL_ABILITY.get(character["class"], "wis")
            heal, _ = roll_dice(spell["heal_dice"])
            healing = heal + calc_mod(character.get(spell_ability, 10))
            healing = max(1, healing)
            character["hp"] = min(character["max_hp"], character["hp"] + healing)
            events.append({"description": f"{character['name']} использует {spell['name_ru']} и восстанавливает {healing} HP!"})
        else:
            events.append({"description": f"{character['name']} использует {spell['name_ru']}!"})

        player_result = {
            "type": "spell",
            "spell": spell["name_ru"],
            "damage": damage,
            "healing": healing,
        }

    elif body.action == "item":
        # Use a consumable item (simple HP potion logic)
        events.append({"description": f"{character['name']} использует предмет."})
        # Find a health potion in inventory
        potions = (
            db.table("item_instances")
            .select("id, item_templates(name, name_ru, consumable_effect, type)")
            .eq("character_id", character["id"])
            .execute()
        ).data
        potion = None
        for p in potions:
            tmpl = p.get("item_templates", {})
            if tmpl and tmpl.get("type") == "consumable":
                potion = p
                break

        if potion:
            effect = potion.get("item_templates", {}).get("consumable_effect") or {}
            heal = effect.get("heal", 0)
            if heal:
                heal_amount, _ = roll_dice(str(heal)) if isinstance(heal, str) else (heal, [])
            else:
                heal_amount = 8  # default potion heal
            character["hp"] = min(character["max_hp"], character["hp"] + heal_amount)
            events.append({"description": f"{character['name']} выпивает зелье и восстанавливает {heal_amount} HP!"})
            # Remove potion
            db.table("item_instances").delete().eq("id", potion["id"]).execute()
            player_result = {"type": "item", "healing": heal_amount}
        else:
            raise HTTPException(status_code=400, detail="No consumable items in inventory")

    elif body.action == "flee":
        flee_check = saving_throw(character["dex"], 12)
        if flee_check["success"]:
            db.table("combat_sessions").update({"status": "fled"}).eq("id", combat["id"]).execute()
            narrative = f"{character['name']} бросает проверку Ловкости ({flee_check['roll']}+{calc_mod(character['dex'])}={flee_check['total']} vs DC 12) — успех! Вы сбегаете из боя!"
            return {
                "narrative": narrative,
                "combat_status": "fled",
                "player_action": {"type": "flee", "success": True, "roll": flee_check},
                "enemy_actions": [],
                "enemies": alive_enemies,
                "round": round_num,
                "character_hp": character["hp"],
                "xp_gain": 0,
                "gold_change": 0,
                "items_gained": [],
            }
        else:
            events.append({"description": f"{character['name']} пытается сбежать (бросок {flee_check['roll']}+{calc_mod(character['dex'])}={flee_check['total']} vs DC 12) — не удалось!"})
            player_result = {"type": "flee", "success": False, "roll": flee_check}

    elif body.action == "custom":
        # For custom actions, just add to events and let enemies attack
        events.append({"description": f"{character['name']}: {body.details}"})
        player_result = {"type": "custom", "details": body.details}

    # ── CHECK VICTORY ──
    alive_enemies = [e for e in enemies if e.get("hp", 0) > 0]

    if not alive_enemies:
        total_xp = sum(e.get("xp_value", 50) for e in enemies)
        total_gold = sum(e.get("gold", 0) for e in enemies)

        # Update character
        new_xp = character.get("xp", 0) + total_xp
        new_gold = character.get("gold", 0) + total_gold
        char_updates = {"xp": new_xp, "gold": new_gold, "hp": character["hp"]}

        # Level up check
        new_level = (new_xp // 300) + 1
        if new_level > character.get("level", 1):
            from app.services.combat import CLASS_HP_DICE
            hit_die = CLASS_HP_DICE.get(character["class"], 8)
            hp_gain = (hit_die // 2 + 1) + calc_mod(character["con"])
            char_updates["level"] = new_level
            char_updates["max_hp"] = character["max_hp"] + hp_gain
            char_updates["hp"] = character["hp"] + hp_gain

            # Update spell slots on level up
            from app.data.spells import CLASS_SPELL_SLOTS
            new_slots = CLASS_SPELL_SLOTS.get(character["class"], {}).get(new_level, {})
            if new_slots:
                char_updates["max_spell_slots"] = new_slots
                char_updates["spell_slots"] = new_slots

        db.table("characters").update(char_updates).eq("id", character["id"]).execute()
        db.table("combat_sessions").update({
            "status": "victory",
            "enemies": enemies,
            "log": combat_log + [{"round": round_num, "events": events}],
        }).eq("id", combat["id"]).execute()

        events.append({"description": f"Победа! Получено {total_xp} XP и {total_gold} золота."})
        narrative = await _combat_narrative(events)

        return {
            "narrative": narrative,
            "combat_status": "victory",
            "player_action": player_result,
            "enemy_actions": [],
            "enemies": [],
            "round": round_num,
            "character_hp": char_updates.get("hp", character["hp"]),
            "xp_gain": total_xp,
            "gold_change": total_gold,
            "items_gained": [],
        }

    # ── ENEMY TURNS ──
    enemy_results = []
    for enemy in alive_enemies:
        result = await cm.enemy_turn(enemy, character)
        enemy_results.append({
            "enemy_name": enemy["name"],
            **result,
        })
        if result["damage"] > 0:
            events.append({"description": f"{enemy['name']} бьёт {character['name']} на {result['damage']} урона (бросок: {result['result']['roll']})"})
        else:
            events.append({"description": f"{enemy['name']} промахивается по {character['name']}"})

    # ── CHECK DEFEAT ──
    if character["hp"] <= 0:
        db.table("characters").update({"hp": 0, "is_alive": False}).eq("id", character["id"]).execute()
        db.table("combat_sessions").update({
            "status": "defeat",
            "enemies": enemies,
            "log": combat_log + [{"round": round_num, "events": events}],
        }).eq("id", combat["id"]).execute()

        events.append({"description": f"{character['name']} пал в бою..."})
        narrative = await _combat_narrative(events)

        return {
            "narrative": narrative,
            "combat_status": "defeat",
            "player_action": player_result,
            "enemy_actions": enemy_results,
            "enemies": alive_enemies,
            "round": round_num,
            "character_hp": 0,
            "xp_gain": 0,
            "gold_change": 0,
            "items_gained": [],
        }

    # ── UPDATE STATE ──
    db.table("characters").update({"hp": character["hp"]}).eq("id", character["id"]).execute()
    new_round = round_num + 1
    db.table("combat_sessions").update({
        "enemies": enemies,
        "round": new_round,
        "log": combat_log + [{"round": round_num, "events": events}],
    }).eq("id", combat["id"]).execute()

    narrative = await _combat_narrative(events)

    return {
        "narrative": narrative,
        "combat_status": "ongoing",
        "player_action": player_result,
        "enemy_actions": enemy_results,
        "enemies": alive_enemies,
        "round": new_round,
        "character_hp": character["hp"],
        "xp_gain": 0,
        "gold_change": 0,
        "items_gained": [],
    }
