"""Update locations table with cached image URLs."""
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.core.supabase import get_supabase_client

db = get_supabase_client()
cid = "b0cfb5d7-2bb8-46dc-a94f-1b77a1f6c039"

locs = db.table("locations").select("*").eq("campaign_id", cid).execute().data
print(f"Found {len(locs)} locations")

for loc in locs:
    name = loc["name"]
    img = loc.get("image_url")
    print(f"  {name}: image_url={img}")
    if img:
        continue
    cache_key = f"location:{cid}:{name}"
    p_hash = hashlib.sha256(cache_key.encode()).hexdigest()
    cached = db.table("generated_images").select("image_url").eq("prompt_hash", p_hash).execute().data
    if cached:
        url = cached[0]["image_url"]
        db.table("locations").update({"image_url": url}).eq("id", loc["id"]).execute()
        print(f"    Updated -> {url}")
    else:
        print(f"    No cached image found")

print("Done!")
