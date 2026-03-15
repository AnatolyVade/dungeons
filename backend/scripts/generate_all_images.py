"""Generate portraits for all NPCs and images for all visited locations."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.core.supabase import get_supabase_client
from app.services.image_generator import generate_npc_portrait, generate_location_image


async def main():
    db = get_supabase_client()
    campaign_id = "b0cfb5d7-2bb8-46dc-a94f-1b77a1f6c039"

    # Get all NPCs without portraits
    npcs = db.table("npcs").select("*").eq("campaign_id", campaign_id).execute().data
    print(f"Found {len(npcs)} NPCs")

    for npc in npcs:
        if npc.get("portrait_url"):
            print(f"  SKIP {npc['name']} (already has portrait)")
            continue
        print(f"  Generating portrait for {npc['name']}...")
        url = await generate_npc_portrait(campaign_id, npc)
        print(f"    -> {url}")

    # Get visited locations
    camp = db.table("campaigns").select("world_state").eq("id", campaign_id).single().execute().data
    locations = camp.get("world_state", {}).get("visited_locations", [])
    char = db.table("characters").select("region").eq("campaign_id", campaign_id).execute().data
    region = char[0].get("region", "Unknown") if char else "Unknown"

    print(f"\nFound {len(locations)} visited locations")

    for loc in locations:
        print(f"  Generating image for '{loc}'...")
        url = await generate_location_image(
            campaign_id, loc, region,
            f"A location called '{loc}' in the region '{region}', a fantasy medieval setting"
        )
        print(f"    -> {url}")

        # Also insert into locations table
        try:
            db.table("locations").insert({
                "campaign_id": campaign_id,
                "name": loc,
                "region": region,
                "image_url": url,
            }).execute()
            print(f"    Saved to locations table")
        except Exception as e:
            print(f"    Location table insert: {e}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
