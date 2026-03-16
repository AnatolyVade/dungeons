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
    system_prompt = build_npc_context(npc, character)
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

    return {
        "dialogue": response.get("dialogue", "..."),
        "reputation_change": rep_change,
        "new_reputation": new_rep,
        "quest_offered": quest_offered,
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
