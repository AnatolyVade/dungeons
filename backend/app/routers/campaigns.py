"""Campaign routes — CRUD."""
from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import get_supabase_client
from app.core.auth import get_current_user
from app.models.schemas import CampaignCreate

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post("")
async def create_campaign(body: CampaignCreate, user: dict = Depends(get_current_user)):
    db = get_supabase_client()
    result = (
        db.table("campaigns")
        .insert({"name": body.name, "user_id": user["id"]})
        .execute()
    )
    return result.data[0]


@router.get("")
async def list_campaigns(user: dict = Depends(get_current_user)):
    db = get_supabase_client()
    result = (
        db.table("campaigns")
        .select("id, name, status, turn_count, created_at, updated_at")
        .eq("user_id", user["id"])
        .order("updated_at", desc=True)
        .execute()
    )
    return result.data


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, user: dict = Depends(get_current_user)):
    db = get_supabase_client()
    result = (
        db.table("campaigns")
        .select("*")
        .eq("id", campaign_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Also fetch character
    char_result = (
        db.table("characters")
        .select("*")
        .eq("campaign_id", campaign_id)
        .maybe_single()
        .execute()
    )
    data = result.data
    data["character"] = char_result.data
    return data


@router.delete("/{campaign_id}")
async def abandon_campaign(campaign_id: str, user: dict = Depends(get_current_user)):
    db = get_supabase_client()
    db.table("campaigns").update({"status": "abandoned"}).eq(
        "id", campaign_id
    ).eq("user_id", user["id"]).execute()
    return {"ok": True}
