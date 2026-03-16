"""Inventory management routes — equip, unequip, drop items."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import get_supabase_client, maybe_single_data
from app.core.auth import get_current_user
from app.models.schemas import EquipRequest, UnequipRequest, DropRequest

router = APIRouter(prefix="/api/campaigns/{campaign_id}/inventory", tags=["inventory"])


def _get_character(db, campaign_id: str, user_id: str) -> dict:
    """Verify campaign ownership and return character."""
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
        raise HTTPException(status_code=404, detail="No character")
    return character


@router.post("/equip")
async def equip_item(
    campaign_id: str,
    body: EquipRequest,
    user: dict = Depends(get_current_user),
):
    """Equip an item from inventory to an equipment slot."""
    db = get_supabase_client()
    character = _get_character(db, campaign_id, user["id"])

    # Verify item belongs to character
    item_instance = maybe_single_data(
        db.table("item_instances")
        .select("id, template_id, item_templates(name, name_ru, type, slot, damage_dice, ac_bonus, rarity)")
        .eq("id", body.item_instance_id)
        .eq("character_id", character["id"])
    )
    if not item_instance:
        raise HTTPException(status_code=404, detail="Item not in your inventory")

    template = item_instance.get("item_templates", {})
    if not template:
        raise HTTPException(status_code=400, detail="Item template not found")

    # Validate slot compatibility
    item_slot = template.get("slot")
    if item_slot and item_slot != body.slot:
        # Allow ring items in ring_1 or ring_2
        if not (item_slot.startswith("ring") and body.slot.startswith("ring")):
            raise HTTPException(
                status_code=400,
                detail=f"This item goes in the '{item_slot}' slot, not '{body.slot}'"
            )

    # Get the equipment slot
    eq_slot = maybe_single_data(
        db.table("equipment_slots")
        .select("id, item_id")
        .eq("character_id", character["id"])
        .eq("slot", body.slot)
    )
    if not eq_slot:
        raise HTTPException(status_code=400, detail="Invalid equipment slot")

    # If slot is occupied, unequip current item first
    if eq_slot.get("item_id"):
        db.table("equipment_slots").update({"item_id": None}).eq("id", eq_slot["id"]).execute()

    # Equip the new item
    db.table("equipment_slots").update({"item_id": body.item_instance_id}).eq("id", eq_slot["id"]).execute()

    return {"success": True, "slot": body.slot, "item_name": template.get("name_ru") or template.get("name")}


@router.post("/unequip")
async def unequip_item(
    campaign_id: str,
    body: UnequipRequest,
    user: dict = Depends(get_current_user),
):
    """Remove an item from an equipment slot back to inventory."""
    db = get_supabase_client()
    character = _get_character(db, campaign_id, user["id"])

    eq_slot = maybe_single_data(
        db.table("equipment_slots")
        .select("id, item_id")
        .eq("character_id", character["id"])
        .eq("slot", body.slot)
    )
    if not eq_slot:
        raise HTTPException(status_code=400, detail="Invalid equipment slot")
    if not eq_slot.get("item_id"):
        raise HTTPException(status_code=400, detail="Slot is already empty")

    db.table("equipment_slots").update({"item_id": None}).eq("id", eq_slot["id"]).execute()

    return {"success": True, "slot": body.slot}


@router.post("/drop")
async def drop_item(
    campaign_id: str,
    body: DropRequest,
    user: dict = Depends(get_current_user),
):
    """Drop (delete) an item from inventory. Cannot drop equipped items."""
    db = get_supabase_client()
    character = _get_character(db, campaign_id, user["id"])

    # Verify item belongs to character
    item = maybe_single_data(
        db.table("item_instances")
        .select("id")
        .eq("id", body.item_instance_id)
        .eq("character_id", character["id"])
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not in your inventory")

    # Check not equipped
    equipped = maybe_single_data(
        db.table("equipment_slots")
        .select("id")
        .eq("item_id", body.item_instance_id)
    )
    if equipped:
        raise HTTPException(status_code=400, detail="Unequip the item first")

    db.table("item_instances").delete().eq("id", body.item_instance_id).execute()

    return {"success": True}
