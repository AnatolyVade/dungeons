"""Shop routes — buy, sell, haggle with merchant NPCs."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import get_supabase_client, maybe_single_data
from app.core.auth import get_current_user
from app.models.schemas import (
    BuyRequest, BuyResponse, SellRequest, SellResponse,
    HaggleRequest, HaggleResponse, ShopItem, ShopResponse,
)
from app.services.ai_manager import call_npc, generate_merchant_inventory
from app.services.context_manager import build_npc_context

router = APIRouter(
    prefix="/api/campaigns/{campaign_id}/npcs/{npc_id}/shop",
    tags=["shop"],
)


async def _validate_merchant(db, campaign_id: str, npc_id: str, user_id: str):
    """Verify campaign ownership and that the NPC is a living merchant."""
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
    if not npc.get("is_merchant"):
        raise HTTPException(status_code=400, detail="This NPC is not a merchant")
    if not npc.get("is_alive", True):
        raise HTTPException(status_code=400, detail="This NPC is dead")

    character = maybe_single_data(
        db.table("characters")
        .select("*")
        .eq("campaign_id", campaign_id)
    )
    if not character:
        raise HTTPException(status_code=400, detail="No character in this campaign")

    return campaign, npc, character


async def _ensure_inventory(db, npc: dict) -> list[dict]:
    """Generate merchant inventory if empty (lazy generation)."""
    shop_inventory = npc.get("shop_inventory") or []
    if shop_inventory:
        return shop_inventory

    # Generate inventory via Claude
    items = await generate_merchant_inventory(npc)

    shop_inventory = []
    for item_data in items:
        # Insert into item_templates
        template = db.table("item_templates").insert({
            "name": item_data.get("name", "Unknown Item"),
            "name_ru": item_data.get("name_ru"),
            "type": item_data.get("type", "misc"),
            "slot": item_data.get("slot"),
            "rarity": item_data.get("rarity", "common"),
            "value": item_data.get("value", 10),
            "description_ru": item_data.get("description_ru"),
            "damage_dice": item_data.get("damage_dice"),
            "ac_bonus": item_data.get("ac_bonus", 0),
            "stackable": item_data.get("stackable", False),
            "max_stack": 10 if item_data.get("stackable") else 1,
        }).execute().data[0]

        shop_inventory.append({
            "item_template_id": template["id"],
            "quantity": 3 if item_data.get("stackable") else 1,
            "price_override": None,
        })

    # Save to NPC
    db.table("npcs").update({
        "shop_inventory": shop_inventory,
        "shop_restock_turn": 0,
    }).eq("id", npc["id"]).execute()

    return shop_inventory


def _calc_sell_multiplier(reputation: int) -> float:
    """Sell price multiplier based on NPC reputation. Range: 0.3-0.7."""
    return round(0.5 + (reputation / 500), 2)


@router.get("", response_model=ShopResponse)
async def get_shop(
    campaign_id: str,
    npc_id: str,
    user: dict = Depends(get_current_user),
):
    """Get merchant's shop inventory with prices."""
    db = get_supabase_client()
    campaign, npc, character = await _validate_merchant(db, campaign_id, npc_id, user["id"])

    # Ensure inventory exists
    shop_inventory = await _ensure_inventory(db, npc)

    # Reload NPC in case inventory was just generated
    if not npc.get("shop_inventory"):
        npc = db.table("npcs").select("*").eq("id", npc_id).single().execute().data

    # Get current discount (stored from haggling)
    discount = npc.get("shop_discount", 0) if isinstance(npc.get("shop_discount"), int) else 0

    # Build shop items
    items = []
    for entry in shop_inventory:
        if entry.get("quantity", 0) <= 0:
            continue
        template = maybe_single_data(
            db.table("item_templates")
            .select("*")
            .eq("id", entry["item_template_id"])
        )
        if not template:
            continue

        base_price = entry.get("price_override") or template.get("value", 10)
        effective_price = max(1, int(base_price * (100 - discount) / 100))

        items.append(ShopItem(
            item_template_id=template["id"],
            name=template["name"],
            name_ru=template.get("name_ru"),
            type=template["type"],
            rarity=template.get("rarity", "common"),
            description_ru=template.get("description_ru"),
            base_price=base_price,
            effective_price=effective_price,
            quantity=entry["quantity"],
            damage_dice=template.get("damage_dice"),
            ac_bonus=template.get("ac_bonus", 0),
        ))

    return ShopResponse(
        items=items,
        merchant_name=npc["name"],
        merchant_name_ru=npc.get("name_ru"),
        discount=discount,
        sell_multiplier=_calc_sell_multiplier(npc.get("reputation", 0)),
    )


@router.post("/buy", response_model=BuyResponse)
async def buy_item(
    campaign_id: str,
    npc_id: str,
    body: BuyRequest,
    user: dict = Depends(get_current_user),
):
    """Buy an item from the merchant."""
    db = get_supabase_client()
    campaign, npc, character = await _validate_merchant(db, campaign_id, npc_id, user["id"])

    shop_inventory = npc.get("shop_inventory", [])

    # Find item in shop
    shop_entry = None
    shop_idx = -1
    for i, entry in enumerate(shop_inventory):
        if entry["item_template_id"] == body.item_template_id:
            shop_entry = entry
            shop_idx = i
            break

    if not shop_entry:
        raise HTTPException(status_code=404, detail="Item not in shop")
    if shop_entry["quantity"] < body.quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")

    # Get template for price
    template = (
        db.table("item_templates")
        .select("*")
        .eq("id", body.item_template_id)
        .single()
        .execute()
    ).data

    base_price = shop_entry.get("price_override") or template.get("value", 10)
    discount = min(body.haggle_discount, npc.get("shop_discount", 0))
    unit_price = max(1, int(base_price * (100 - discount) / 100))
    total_cost = unit_price * body.quantity

    if character["gold"] < total_cost:
        raise HTTPException(status_code=400, detail="Not enough gold")

    # Deduct gold
    new_gold = character["gold"] - total_cost
    db.table("characters").update({"gold": new_gold}).eq("id", character["id"]).execute()

    # Create item instance for player
    db.table("item_instances").insert({
        "template_id": body.item_template_id,
        "character_id": character["id"],
        "quantity": body.quantity,
    }).execute()

    # Decrement shop stock
    shop_inventory[shop_idx]["quantity"] -= body.quantity
    if shop_inventory[shop_idx]["quantity"] <= 0:
        shop_inventory.pop(shop_idx)
    db.table("npcs").update({"shop_inventory": shop_inventory}).eq("id", npc["id"]).execute()

    return BuyResponse(
        success=True,
        gold_spent=total_cost,
        new_gold=new_gold,
        item_name=template.get("name_ru") or template["name"],
    )


@router.post("/sell", response_model=SellResponse)
async def sell_item(
    campaign_id: str,
    npc_id: str,
    body: SellRequest,
    user: dict = Depends(get_current_user),
):
    """Sell an item to the merchant."""
    db = get_supabase_client()
    campaign, npc, character = await _validate_merchant(db, campaign_id, npc_id, user["id"])

    # Get item instance
    item_instance = maybe_single_data(
        db.table("item_instances")
        .select("*, item_templates(*)")
        .eq("id", body.item_instance_id)
        .eq("character_id", character["id"])
    )
    if not item_instance:
        raise HTTPException(status_code=404, detail="Item not found in inventory")

    # Check not equipped
    equipped = maybe_single_data(
        db.table("equipment_slots")
        .select("id")
        .eq("item_id", body.item_instance_id)
    )
    if equipped:
        raise HTTPException(status_code=400, detail="Unequip the item first")

    template = item_instance.get("item_templates", {})
    sell_multiplier = _calc_sell_multiplier(npc.get("reputation", 0))
    unit_value = max(1, int(template.get("value", 10) * sell_multiplier))
    sell_qty = min(body.quantity, item_instance.get("quantity", 1))
    gold_earned = unit_value * sell_qty

    # Add gold
    new_gold = character["gold"] + gold_earned
    db.table("characters").update({"gold": new_gold}).eq("id", character["id"]).execute()

    # Remove or reduce item
    remaining = item_instance.get("quantity", 1) - sell_qty
    if remaining <= 0:
        db.table("item_instances").delete().eq("id", body.item_instance_id).execute()
    else:
        db.table("item_instances").update({"quantity": remaining}).eq("id", body.item_instance_id).execute()

    return SellResponse(success=True, gold_earned=gold_earned, new_gold=new_gold)


@router.post("/haggle", response_model=HaggleResponse)
async def haggle(
    campaign_id: str,
    npc_id: str,
    body: HaggleRequest,
    user: dict = Depends(get_current_user),
):
    """Haggle with the merchant for a discount."""
    db = get_supabase_client()
    campaign, npc, character = await _validate_merchant(db, campaign_id, npc_id, user["id"])

    # Load NPC chat history
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

    # Build NPC context and call Claude
    system_prompt = build_npc_context(npc, character)
    response = await call_npc(system_prompt, chat_history, body.message)

    # Save chat messages
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

    # Apply discount
    new_discount = min(30, max(0, response.get("shop_discount", 0)))
    rep_change = response.get("reputation_change", 0)
    new_rep = max(-100, min(100, npc.get("reputation", 0) + rep_change))

    # Update NPC
    npc_updates = {"reputation": new_rep, "shop_discount": new_discount}

    # Save new memory
    if response.get("new_memory"):
        memories = npc.get("memories", [])
        memories.append(response["new_memory"])
        npc_updates["memories"] = memories

    # Update disposition based on reputation
    if new_rep > 50:
        npc_updates["disposition"] = "friendly"
    elif new_rep > 20:
        npc_updates["disposition"] = "neutral"
    elif new_rep > -30:
        npc_updates["disposition"] = "neutral"
    elif new_rep > -60:
        npc_updates["disposition"] = "unfriendly"
    else:
        npc_updates["disposition"] = "hostile"

    db.table("npcs").update(npc_updates).eq("id", npc["id"]).execute()

    return HaggleResponse(
        dialogue=response.get("dialogue", "..."),
        discount=new_discount,
        reputation_change=rep_change,
        new_reputation=new_rep,
    )
