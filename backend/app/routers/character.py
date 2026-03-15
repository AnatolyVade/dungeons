"""Character routes — creation, stat rolling, retrieval."""
from fastapi import APIRouter, Depends, HTTPException

from app.core.supabase import get_supabase_client
from app.core.auth import get_current_user
from app.models.schemas import CharacterCreate
from app.services.combat import roll_stat_block, calculate_starting_hp, calculate_starting_ac

router = APIRouter(prefix="/api/campaigns/{campaign_id}/character", tags=["character"])


@router.post("/roll-stats")
async def roll_stats(campaign_id: str, user: dict = Depends(get_current_user)):
    """Roll 4d6 drop lowest x6 for ability scores."""
    return roll_stat_block()


@router.post("")
async def create_character(
    campaign_id: str,
    body: CharacterCreate,
    user: dict = Depends(get_current_user),
):
    db = get_supabase_client()

    # Verify campaign ownership
    campaign = (
        db.table("campaigns")
        .select("id")
        .eq("id", campaign_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if not campaign.data:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Check no existing character
    existing = (
        db.table("characters")
        .select("id")
        .eq("campaign_id", campaign_id)
        .maybe_single()
        .execute()
    )
    if existing and existing.data:
        raise HTTPException(status_code=400, detail="Character already exists for this campaign")

    hp = calculate_starting_hp(body.char_class, body.stats.con)
    ac = calculate_starting_ac(body.char_class, body.stats.dex)

    char_data = {
        "campaign_id": campaign_id,
        "name": body.name,
        "race": body.race,
        "class": body.char_class,
        "hp": hp,
        "max_hp": hp,
        "ac": ac,
        "str": body.stats.str_,
        "dex": body.stats.dex,
        "con": body.stats.con,
        "int_": body.stats.int_,
        "wis": body.stats.wis,
        "cha": body.stats.cha,
    }

    result = db.table("characters").insert(char_data).execute()
    character = result.data[0]

    # Initialize equipment slots
    slots = ["head", "chest", "legs", "boots", "weapon", "offhand", "ring_1", "ring_2", "amulet"]
    for slot in slots:
        db.table("equipment_slots").insert({
            "character_id": character["id"],
            "slot": slot,
        }).execute()

    return character


@router.get("")
async def get_character(campaign_id: str, user: dict = Depends(get_current_user)):
    db = get_supabase_client()

    # Verify campaign ownership
    campaign = (
        db.table("campaigns")
        .select("id")
        .eq("id", campaign_id)
        .eq("user_id", user["id"])
        .single()
        .execute()
    )
    if not campaign.data:
        raise HTTPException(status_code=404, detail="Campaign not found")

    char_result = (
        db.table("characters")
        .select("*")
        .eq("campaign_id", campaign_id)
        .maybe_single()
        .execute()
    )
    if not char_result.data:
        raise HTTPException(status_code=404, detail="No character in this campaign")

    character = char_result.data

    # Get equipment
    equip_result = (
        db.table("equipment_slots")
        .select("slot, item_id, item_instances(id, quantity, custom_name, item_templates(name, name_ru, type, damage_dice, ac_bonus, stat_bonuses, rarity))")
        .eq("character_id", character["id"])
        .execute()
    )
    character["equipment"] = equip_result.data

    # Get inventory
    inv_result = (
        db.table("item_instances")
        .select("id, quantity, custom_name, custom_name_ru, is_identified, item_templates(name, name_ru, type, rarity, value, description_ru)")
        .eq("character_id", character["id"])
        .execute()
    )
    character["inventory"] = inv_result.data

    return character
