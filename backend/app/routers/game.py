"""Game action routes — the core DM loop."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import get_supabase_client, maybe_single_data
from app.core.auth import get_current_user
from app.models.schemas import ActionRequest, RestRequest
from app.services.context_manager import build_dm_context
from app.services.ai_manager import call_dm
from app.services.summarizer import maybe_summarize
from app.services.image_generator import generate_location_image, generate_npc_portrait

router = APIRouter(prefix="/api/campaigns/{campaign_id}", tags=["game"])


async def _load_game_state(db, campaign_id: str, user_id: str):
    """Load all game state needed for a DM call."""
    # Campaign
    campaign = (
        db.table("campaigns")
        .select("*")
        .eq("id", campaign_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    ).data
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign["status"] != "active":
        raise HTTPException(status_code=400, detail="Campaign is not active")

    # Character
    character = maybe_single_data(
        db.table("characters")
        .select("*")
        .eq("campaign_id", campaign_id)
    )
    if not character:
        raise HTTPException(status_code=400, detail="No character — create one first")
    if not character["is_alive"]:
        raise HTTPException(status_code=400, detail="Character is dead")

    # Equipment
    equipment = (
        db.table("equipment_slots")
        .select("slot, item_instances(id, custom_name, item_templates(name, name_ru, damage_dice, ac_bonus))")
        .eq("character_id", character["id"])
        .not_.is_("item_id", "null")
        .execute()
    ).data

    # Inventory
    inventory = (
        db.table("item_instances")
        .select("id, quantity, custom_name, item_templates(name, name_ru, type, rarity)")
        .eq("character_id", character["id"])
        .execute()
    ).data

    # Companions
    companions = (
        db.table("companions")
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("is_alive", True)
        .execute()
    ).data

    # Active combat
    active_combat = maybe_single_data(
        db.table("combat_sessions")
        .select("*")
        .eq("campaign_id", campaign_id)
        .eq("status", "active")
    )

    # Recent chat (last 16 messages = 8 exchanges)
    recent_chat = (
        db.table("chat_history")
        .select("role, content")
        .eq("campaign_id", campaign_id)
        .eq("context", "dm")
        .eq("is_archived", False)
        .order("created_at", desc=True)
        .limit(16)
        .execute()
    ).data
    recent_chat = list(reversed(recent_chat))

    # Nearby NPCs
    nearby_npcs = (
        db.table("npcs")
        .select("name, name_ru, disposition, is_merchant, reputation")
        .eq("campaign_id", campaign_id)
        .eq("location", character["location"])
        .eq("is_alive", True)
        .execute()
    ).data

    # Active quests
    active_quests = (
        db.table("quests")
        .select("title, title_ru, objectives")
        .eq("campaign_id", campaign_id)
        .eq("status", "active")
        .execute()
    ).data

    return campaign, character, equipment, inventory, companions, active_combat, recent_chat, nearby_npcs, active_quests


async def _apply_state_changes(db, campaign_id: str, character: dict, dm_response: dict):
    """Apply DM response state changes to the database."""
    char_updates = {}

    # HP change
    if dm_response.get("hp_change", 0) != 0:
        new_hp = max(0, min(character["max_hp"], character["hp"] + dm_response["hp_change"]))
        char_updates["hp"] = new_hp
        if new_hp <= 0:
            char_updates["is_alive"] = False

    # XP gain
    if dm_response.get("xp_gain", 0) > 0:
        new_xp = character["xp"] + dm_response["xp_gain"]
        char_updates["xp"] = new_xp
        # Level up check (simple: 300 XP per level)
        new_level = (new_xp // 300) + 1
        if new_level > character["level"]:
            char_updates["level"] = new_level
            # HP increase on level up
            from app.services.combat import CLASS_HP_DICE, calc_mod
            hit_die = CLASS_HP_DICE.get(character["class"], 8)
            hp_gain = (hit_die // 2 + 1) + calc_mod(character["con"])
            char_updates["max_hp"] = character["max_hp"] + hp_gain
            char_updates["hp"] = character.get("hp", character["max_hp"]) + hp_gain
            # Update spell slots on level up
            from app.data.spells import CLASS_SPELL_SLOTS
            new_slots = CLASS_SPELL_SLOTS.get(character["class"], {}).get(new_level, {})
            if new_slots:
                char_updates["max_spell_slots"] = new_slots
                char_updates["spell_slots"] = new_slots

    # Gold change
    if dm_response.get("gold_change", 0) != 0:
        char_updates["gold"] = max(0, character["gold"] + dm_response["gold_change"])

    # Conditions
    current_conditions = list(character.get("conditions", []) or [])
    conditions_changed = False
    for c in dm_response.get("conditions_gained", []):
        if isinstance(c, str) and c not in current_conditions:
            current_conditions.append(c)
            conditions_changed = True
    for c in dm_response.get("conditions_lost", []):
        if isinstance(c, str) and c in current_conditions:
            current_conditions.remove(c)
            conditions_changed = True
    if conditions_changed:
        char_updates["conditions"] = current_conditions

    # Location change
    if dm_response.get("location") and dm_response["location"] != character["location"]:
        char_updates["location"] = dm_response["location"]
        # Track visited locations
        campaign = db.table("campaigns").select("world_state").eq("id", campaign_id).single().execute().data
        world_state = campaign.get("world_state", {})
        visited = world_state.get("visited_locations", [])
        if dm_response["location"] not in visited:
            visited.append(dm_response["location"])
            world_state["visited_locations"] = visited
            db.table("campaigns").update({"world_state": world_state}).eq("id", campaign_id).execute()

    if dm_response.get("region") and dm_response["region"] != character.get("region"):
        char_updates["region"] = dm_response["region"]

    # Apply character updates
    if char_updates:
        db.table("characters").update(char_updates).eq("id", character["id"]).execute()

    # Process items_gained
    for item_data in dm_response.get("items_gained", []):
        if not isinstance(item_data, dict) or not item_data.get("name"):
            continue
        try:
            # Create item template
            template = db.table("item_templates").insert({
                "name": item_data.get("name", "Unknown"),
                "name_ru": item_data.get("name_ru", item_data.get("name")),
                "type": item_data.get("type", "misc"),
                "rarity": item_data.get("rarity", "common"),
                "value": item_data.get("value", 5),
                "damage_dice": item_data.get("damage_dice"),
                "ac_bonus": item_data.get("ac_bonus", 0),
                "slot": item_data.get("slot"),
                "stackable": item_data.get("stackable", False),
            }).execute().data[0]
            # Create item instance for character
            db.table("item_instances").insert({
                "template_id": template["id"],
                "character_id": character["id"],
                "quantity": item_data.get("quantity", 1),
            }).execute()
        except Exception:
            pass  # Don't crash the game if item insert fails

    # Process items_lost
    for item_name in dm_response.get("items_lost", []):
        if not isinstance(item_name, str):
            continue
        try:
            instances = (
                db.table("item_instances")
                .select("id, item_templates(name, name_ru)")
                .eq("character_id", character["id"])
                .execute()
            ).data
            for inst in instances:
                tmpl = inst.get("item_templates") or {}
                if tmpl.get("name") == item_name or tmpl.get("name_ru") == item_name:
                    # Check not equipped
                    equipped = maybe_single_data(
                        db.table("equipment_slots").select("id").eq("item_id", inst["id"])
                    )
                    if not equipped:
                        db.table("item_instances").delete().eq("id", inst["id"]).execute()
                    break
        except Exception:
            pass

    # Create new NPCs
    for npc_data in dm_response.get("new_npcs", []):
        if isinstance(npc_data, str):
            # AI returned just a name string instead of a dict
            npc_data = {"name": npc_data, "name_ru": npc_data}
        if not isinstance(npc_data, dict):
            continue
        if npc_data.get("name"):
            # Sanitize disposition to match DB check constraint
            valid_dispositions = {"friendly", "neutral", "unfriendly", "hostile"}
            raw_disp = str(npc_data.get("disposition", "neutral")).lower()
            if raw_disp not in valid_dispositions:
                # Map common Russian/other values
                disp_map = {
                    "дружелюбная": "friendly", "дружелюбный": "friendly", "friendly": "friendly",
                    "нейтральная": "neutral", "нейтральный": "neutral",
                    "недружелюбная": "unfriendly", "недружелюбный": "unfriendly",
                    "враждебная": "hostile", "враждебный": "hostile",
                }
                raw_disp = disp_map.get(raw_disp, "neutral")
            try:
                inserted = db.table("npcs").insert({
                    "campaign_id": campaign_id,
                    "name": npc_data.get("name", "Unknown"),
                    "name_ru": npc_data.get("name_ru", npc_data.get("name")),
                    "race": npc_data.get("race", "Human"),
                    "location": dm_response.get("location", character["location"]),
                    "region": dm_response.get("region", character.get("region", "Unknown")),
                    "personality": npc_data.get("personality", "Mysterious stranger"),
                    "disposition": raw_disp,
                    "is_merchant": npc_data.get("is_merchant", False),
                }).execute()
                # Generate portrait in background
                if inserted.data:
                    asyncio.create_task(
                        generate_npc_portrait(campaign_id, inserted.data[0])
                    )
            except Exception:
                pass  # Don't crash the game if NPC insert fails

    # Handle combat initiation
    if dm_response.get("combat_status") == "started" and dm_response.get("enemies"):
        enemies = dm_response["enemies"]
        if isinstance(enemies, str):
            # AI returned a description, not structured data — create basic enemy
            enemies = [{"name": enemies, "hp": 20, "max_hp": 20, "ac": 12, "attack_dice": "1d6", "attack_stat": 12, "xp_value": 50}]
        elif isinstance(enemies, list):
            for e in enemies:
                e.setdefault("max_hp", e.get("hp", 20))
                e.setdefault("ac", 12)
                e.setdefault("attack_dice", "1d6")
                e.setdefault("attack_stat", 12)
                e.setdefault("xp_value", 50)

        db.table("combat_sessions").insert({
            "campaign_id": campaign_id,
            "enemies": enemies,
            "turn_order": [],
        }).execute()

    # Process quest_update
    quest_update = dm_response.get("quest_update")
    if quest_update and isinstance(quest_update, dict):
        title = quest_update.get("title", "")
        obj_text = quest_update.get("objective_completed", "")
        if title and obj_text:
            try:
                quests = (
                    db.table("quests")
                    .select("*")
                    .eq("campaign_id", campaign_id)
                    .eq("status", "active")
                    .execute()
                ).data
                for quest in quests:
                    if title.lower() in (quest.get("title", "").lower() + " " + (quest.get("title_ru") or "").lower()):
                        objectives = quest.get("objectives", [])
                        all_done = True
                        for obj in objectives:
                            if obj_text.lower() in obj.get("text", "").lower():
                                obj["completed"] = True
                            if not obj.get("completed"):
                                all_done = False
                        updates = {"objectives": objectives}
                        if all_done:
                            updates["status"] = "completed"
                            updates["completed_at"] = "now()"
                            # Grant quest rewards
                            rewards = quest.get("rewards", {})
                            reward_updates = {}
                            if rewards.get("xp"):
                                reward_updates["xp"] = character.get("xp", 0) + rewards["xp"]
                            if rewards.get("gold"):
                                reward_updates["gold"] = character.get("gold", 0) + rewards["gold"]
                            if reward_updates:
                                db.table("characters").update(reward_updates).eq("id", character["id"]).execute()
                        db.table("quests").update(updates).eq("id", quest["id"]).execute()
                        break
            except Exception:
                pass

    # Increment turn count
    db.rpc("increment_turn", {"cid": campaign_id}).execute()


@router.post("/action")
async def game_action(
    campaign_id: str,
    body: ActionRequest,
    user: dict = Depends(get_current_user),
):
    """Core game loop: player action -> DM response -> state update."""
    db = get_supabase_client()

    # Load state
    (campaign, character, equipment, inventory, companions,
     active_combat, recent_chat, nearby_npcs, active_quests) = await _load_game_state(
        db, campaign_id, user["id"]
    )

    # If combat is active, redirect to combat endpoint
    if active_combat:
        return {
            "narrative": "Вы находитесь в бою! Используйте боевые действия.",
            "combat_status": "ongoing",
            "enemies": active_combat.get("enemies", []),
            "suggestions": ["Атаковать", "Использовать заклинание", "Использовать предмет", "Сбежать"],
            "dice_rolls": [],
            "hp_change": 0,
            "xp_gain": 0,
            "gold_change": 0,
            "items_gained": [],
            "items_lost": [],
            "location": None,
            "region": None,
            "new_npcs": [],
            "scene_image_url": None,
        }

    # Build context
    system_prompt, chat = await build_dm_context(
        campaign=campaign,
        character=character,
        equipment=equipment,
        inventory=inventory,
        companions=companions,
        active_combat=active_combat,
        recent_chat=recent_chat,
        nearby_npcs=nearby_npcs,
        active_quests=active_quests,
    )

    # Call DM
    dm_response = await call_dm(system_prompt, chat, body.action)

    # Save chat history
    db.table("chat_history").insert({
        "campaign_id": campaign_id,
        "context": "dm",
        "role": "user",
        "content": body.action,
    }).execute()
    db.table("chat_history").insert({
        "campaign_id": campaign_id,
        "context": "dm",
        "role": "assistant",
        "content": dm_response.get("narrative", ""),
    }).execute()

    # Check if location changed before applying state
    old_location = character["location"]

    # Apply state changes
    await _apply_state_changes(db, campaign_id, character, dm_response)

    # Generate scene image if location changed
    new_location = dm_response.get("location")
    if new_location and new_location != old_location:
        scene_url = await generate_location_image(
            campaign_id,
            new_location,
            dm_response.get("region", character.get("region", "")),
            dm_response.get("narrative", ""),
        )
        if scene_url:
            dm_response["scene_image_url"] = scene_url

    # Tier 3: maybe summarize
    await maybe_summarize(campaign_id)

    return dm_response


@router.post("/action/rest")
async def rest(
    campaign_id: str,
    body: RestRequest,
    user: dict = Depends(get_current_user),
):
    """Short or long rest."""
    db = get_supabase_client()

    character = maybe_single_data(
        db.table("characters")
        .select("*")
        .eq("campaign_id", campaign_id)
    )
    if not character:
        raise HTTPException(status_code=404, detail="No character")

    if body.type == "short":
        # Recover 25% HP
        from app.services.combat import roll_dice
        heal, _ = roll_dice(f"1d{character['max_hp'] // 4 or 1}")
        new_hp = min(character["max_hp"], character["hp"] + heal)
        db.table("characters").update({"hp": new_hp}).eq("id", character["id"]).execute()
        return {"type": "short", "hp_restored": new_hp - character["hp"], "new_hp": new_hp}
    else:
        # Long rest: full HP, reset spell slots, clear conditions
        db.table("characters").update({
            "hp": character["max_hp"],
            "spell_slots": character.get("max_spell_slots", {}),
            "conditions": [],
        }).eq("id", character["id"]).execute()
        return {"type": "long", "hp_restored": character["max_hp"] - character["hp"], "new_hp": character["max_hp"]}


@router.get("/npcs")
async def get_nearby_npcs(
    campaign_id: str,
    user: dict = Depends(get_current_user),
):
    """Get NPCs at the character's current location."""
    db = get_supabase_client()

    # Verify campaign
    campaign = (
        db.table("campaigns")
        .select("id")
        .eq("id", campaign_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    ).data
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    character = maybe_single_data(
        db.table("characters")
        .select("location")
        .eq("campaign_id", campaign_id)
    )
    if not character:
        return []

    npcs = (
        db.table("npcs")
        .select("id, name, name_ru, disposition, is_merchant, location, portrait_url, personality, race, reputation")
        .eq("campaign_id", campaign_id)
        .eq("location", character["location"])
        .eq("is_alive", True)
        .execute()
    ).data

    return npcs


@router.get("/chat-history")
async def get_chat_history(
    campaign_id: str,
    user: dict = Depends(get_current_user),
):
    """Get DM chat history for the campaign."""
    db = get_supabase_client()

    # Verify campaign
    campaign = (
        db.table("campaigns")
        .select("id")
        .eq("id", campaign_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    ).data
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    messages = (
        db.table("chat_history")
        .select("role, content, created_at")
        .eq("campaign_id", campaign_id)
        .eq("context", "dm")
        .eq("is_archived", False)
        .order("created_at", desc=False)
        .execute()
    ).data

    return messages


@router.get("/quests")
async def get_quests(
    campaign_id: str,
    user: dict = Depends(get_current_user),
):
    """Get all quests for a campaign."""
    db = get_supabase_client()

    # Verify campaign
    campaign = (
        db.table("campaigns")
        .select("id")
        .eq("id", campaign_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    ).data
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    quests = (
        db.table("quests")
        .select("id, title, title_ru, description, description_ru, type, status, objectives, rewards, giver_npc_id, created_at, completed_at")
        .eq("campaign_id", campaign_id)
        .order("created_at", desc=False)
        .execute()
    ).data

    return quests
