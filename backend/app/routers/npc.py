"""NPC conversation routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import get_supabase_client, maybe_single_data
from app.core.auth import get_current_user
from app.models.schemas import HaggleRequest
from app.services.context_manager import build_npc_context
from app.services.ai_manager import call_npc
from app.services.image_generator import generate_npc_portrait

router = APIRouter(
    prefix="/api/campaigns/{campaign_id}/npcs/{npc_id}",
    tags=["npc"],
)


@router.post("/chat")
async def chat_with_npc(
    campaign_id: str,
    npc_id: str,
    body: HaggleRequest,
    user: dict = Depends(get_current_user),
):
    """Chat with an NPC."""
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

    # Get NPC
    npc = (
        db.table("npcs")
        .select("*")
        .eq("id", npc_id)
        .eq("campaign_id", campaign_id)
        .single()
        .execute()
    ).data
    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")

    # Get character
    character = maybe_single_data(
        db.table("characters")
        .select("*")
        .eq("campaign_id", campaign_id)
    )
    if not character:
        raise HTTPException(status_code=400, detail="No character")

    # Load character abilities for NPC context
    char_abilities = (
        db.table("character_abilities")
        .select("category, name, name_ru")
        .eq("character_id", character["id"])
        .execute()
    ).data

    # Load chat history for this NPC
    chat_context = f"npc_{npc_id}"
    chat_result = (
        db.table("chat_history")
        .select("role, content")
        .eq("campaign_id", campaign_id)
        .eq("context", chat_context)
        .eq("is_archived", False)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    chat_history = list(reversed(chat_result.data))

    # Build context and call Claude as NPC
    system_prompt = build_npc_context(npc, character, abilities=char_abilities)
    response = await call_npc(system_prompt, chat_history, body.message)

    # Save chat
    db.table("chat_history").insert({
        "campaign_id": campaign_id,
        "context": chat_context,
        "role": "user",
        "content": body.message,
    }).execute()
    db.table("chat_history").insert({
        "campaign_id": campaign_id,
        "context": chat_context,
        "role": "assistant",
        "content": response.get("dialogue", ""),
    }).execute()

    # Update reputation
    rep_change = response.get("reputation_change", 0)
    new_rep = max(-100, min(100, npc.get("reputation", 0) + rep_change))
    npc_updates = {"reputation": new_rep}

    # Save memory
    if response.get("new_memory"):
        memories = npc.get("memories", [])
        memories.append(response["new_memory"])
        npc_updates["memories"] = memories

    # Update disposition
    if new_rep > 50:
        npc_updates["disposition"] = "friendly"
    elif new_rep > -30:
        npc_updates["disposition"] = "neutral"
    elif new_rep > -60:
        npc_updates["disposition"] = "unfriendly"
    else:
        npc_updates["disposition"] = "hostile"

    db.table("npcs").update(npc_updates).eq("id", npc_id).execute()

    # Save quest if NPC offered one
    quest_offered = response.get("quest_offered")
    if quest_offered and isinstance(quest_offered, dict) and quest_offered.get("title"):
        try:
            db.table("quests").insert({
                "campaign_id": campaign_id,
                "title": quest_offered.get("title", "Unknown Quest"),
                "title_ru": quest_offered.get("title_ru", quest_offered.get("title")),
                "description": quest_offered.get("description", ""),
                "description_ru": quest_offered.get("description_ru", ""),
                "objectives": quest_offered.get("objectives", []),
                "rewards": quest_offered.get("rewards", {}),
                "giver_npc_id": npc_id,
                "status": "active",
            }).execute()
        except Exception:
            pass  # Don't crash if quest insert fails

    # Handle taught ability
    taught = response.get("taught")
    taught_result = None
    if taught and isinstance(taught, dict) and taught.get("name"):
        gold_cost = taught.get("gold_cost", 0)
        can_learn = True
        if gold_cost > 0:
            if character["gold"] >= gold_cost:
                new_gold = character["gold"] - gold_cost
                db.table("characters").update({"gold": new_gold}).eq("id", character["id"]).execute()
            else:
                can_learn = False

        if can_learn:
            try:
                db.table("character_abilities").upsert({
                    "character_id": character["id"],
                    "category": taught.get("category", "misc"),
                    "name": taught["name"],
                    "name_ru": taught.get("name_ru", taught["name"]),
                    "description_ru": taught.get("description_ru"),
                    "source": f"NPC:{npc['name']}",
                    "data": taught.get("data", {}),
                }, on_conflict="character_id,category,name").execute()
                taught_result = taught

                # If spell, also add to known_spells
                if taught.get("category") == "spell" and taught.get("data", {}).get("spell_key"):
                    known = list(character.get("known_spells", []))
                    sk = taught["data"]["spell_key"]
                    if sk not in known:
                        known.append(sk)
                        db.table("characters").update({"known_spells": known}).eq("id", character["id"]).execute()
            except Exception:
                pass

    # Handle secret shared (sets world flags)
    secret = response.get("secret_shared")
    if secret and isinstance(secret, dict) and secret.get("flag_key"):
        try:
            camp_data = db.table("campaigns").select("world_state").eq("id", campaign_id).single().execute().data
            ws = camp_data.get("world_state", {})
            flags = ws.get("flags", {})
            flags[secret["flag_key"]] = secret.get("flag_value", True)
            ws["flags"] = flags
            db.table("campaigns").update({"world_state": ws}).eq("id", campaign_id).execute()
        except Exception:
            pass

    # Propagate faction reputation
    if npc.get("faction") and rep_change != 0:
        try:
            from app.core.supabase import maybe_single_data as _ms
            existing = _ms(
                db.table("faction_reputation")
                .select("*")
                .eq("campaign_id", campaign_id)
                .eq("faction", npc["faction"])
            )
            if existing:
                new_frep = max(-100, min(100, existing["reputation"] + rep_change))
                db.table("faction_reputation").update({"reputation": new_frep}).eq("id", existing["id"]).execute()
            else:
                db.table("faction_reputation").insert({
                    "campaign_id": campaign_id,
                    "faction": npc["faction"],
                    "reputation": max(-100, min(100, rep_change)),
                }).execute()
        except Exception:
            pass

    return {
        "dialogue": response.get("dialogue", "..."),
        "reputation_change": rep_change,
        "new_reputation": new_rep,
        "quest_offered": quest_offered,
        "taught": taught_result,
    }


@router.get("/portrait")
async def get_or_generate_portrait(
    campaign_id: str,
    npc_id: str,
    user: dict = Depends(get_current_user),
):
    """Get NPC portrait, generating one if needed."""
    db = get_supabase_client()

    npc = (
        db.table("npcs")
        .select("*")
        .eq("id", npc_id)
        .eq("campaign_id", campaign_id)
        .single()
        .execute()
    ).data
    if not npc:
        raise HTTPException(status_code=404, detail="NPC not found")

    if npc.get("portrait_url"):
        return {"portrait_url": npc["portrait_url"]}

    url = await generate_npc_portrait(campaign_id, npc)
    return {"portrait_url": url}
