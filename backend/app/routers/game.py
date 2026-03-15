"""Game action routes — the core DM loop."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import get_supabase_client, maybe_single_data
from app.core.auth import get_current_user
from app.models.schemas import ActionRequest, RestRequest
from app.services.context_manager import build_dm_context
from app.services.ai_manager import call_dm
from app.services.summarizer import maybe_summarize

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

    # Gold change
    if dm_response.get("gold_change", 0) != 0:
        char_updates["gold"] = max(0, character["gold"] + dm_response["gold_change"])

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

    # Create new NPCs
    for npc_data in dm_response.get("new_npcs", []):
        if npc_data.get("name"):
            db.table("npcs").insert({
                "campaign_id": campaign_id,
                "name": npc_data.get("name", "Unknown"),
                "name_ru": npc_data.get("name_ru", npc_data.get("name")),
                "race": npc_data.get("race", "Human"),
                "location": dm_response.get("location", character["location"]),
                "region": dm_response.get("region", character.get("region", "Unknown")),
                "personality": npc_data.get("personality", "Mysterious stranger"),
                "disposition": npc_data.get("disposition", "neutral"),
                "is_merchant": npc_data.get("is_merchant", False),
            }).execute()

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

    # Apply state changes
    await _apply_state_changes(db, campaign_id, character, dm_response)

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
        # Long rest: full HP, reset spell slots
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
        .select("id, name, name_ru, disposition, is_merchant, location")
        .eq("campaign_id", campaign_id)
        .eq("location", character["location"])
        .eq("is_alive", True)
        .execute()
    ).data

    return npcs
