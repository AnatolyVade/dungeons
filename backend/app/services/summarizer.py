"""Tier 3 summarizer — runs every 20 turns to compress history."""
from __future__ import annotations

from app.services.ai_manager import summarize_history, mega_compress
from app.services.context_manager import format_history
from app.core.supabase import get_supabase_client


async def maybe_summarize(campaign_id: str) -> None:
    """Called after every turn. Summarizes every 20 turns."""
    db = get_supabase_client()

    # Get campaign
    result = db.table("campaigns").select("*").eq("id", campaign_id).single().execute()
    campaign = result.data
    turn_count = campaign["turn_count"]

    if turn_count % 20 != 0 or turn_count == 0:
        return

    # Get last 40 messages (20 exchanges)
    chat_result = (
        db.table("chat_history")
        .select("role, content")
        .eq("campaign_id", campaign_id)
        .eq("context", "dm")
        .eq("is_archived", False)
        .order("created_at", desc=True)
        .limit(40)
        .execute()
    )
    recent = list(reversed(chat_result.data))

    if not recent:
        return

    # Summarize
    summary_text = await summarize_history(format_history(recent))

    # Update world_state
    world_state = campaign.get("world_state", {})
    summaries = world_state.get("story_summaries", [])
    summaries.append({
        "turns": f"{turn_count - 20}-{turn_count}",
        "text": summary_text,
    })

    # Mega-compress if > 10 summaries
    if len(summaries) > 10:
        oldest_text = " ".join([s["text"] for s in summaries[:5]])
        mega = await mega_compress(oldest_text)
        summaries = [
            {
                "turns": f"{summaries[0]['turns'].split('-')[0]}-{summaries[4]['turns'].split('-')[-1]}",
                "text": mega,
            }
        ] + summaries[5:]

    world_state["story_summaries"] = summaries

    # Save
    db.table("campaigns").update({"world_state": world_state}).eq("id", campaign_id).execute()

    # Archive old chat (keep last 40 messages live)
    all_chat = (
        db.table("chat_history")
        .select("id")
        .eq("campaign_id", campaign_id)
        .eq("context", "dm")
        .eq("is_archived", False)
        .order("created_at", desc=True)
        .execute()
    )
    if len(all_chat.data) > 40:
        ids_to_archive = [m["id"] for m in all_chat.data[40:]]
        for msg_id in ids_to_archive:
            db.table("chat_history").update({"is_archived": True}).eq("id", msg_id).execute()
