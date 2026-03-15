"""Image generation service using Google Nano Banana 2 (Gemini 3.1 Flash Image)."""
from __future__ import annotations

import hashlib
import logging
import os
import uuid

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.supabase import get_supabase_client, maybe_single_data

logger = logging.getLogger(__name__)

STYLE_PREFIX = (
    "Dark fantasy oil painting style, dramatic cinematic lighting, "
    "D&D high fantasy art, richly detailed, atmospheric, no text, no words, no UI"
)


def _get_genai_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.google_api_key)


def _prompt_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _ensure_media_dir(campaign_id: str) -> str:
    settings = get_settings()
    path = os.path.join(settings.media_dir, campaign_id)
    os.makedirs(path, exist_ok=True)
    return path


async def generate_and_save(
    prompt: str,
    campaign_id: str,
    image_type: str,
    cache_key: str,
) -> str | None:
    """Generate image via Nano Banana 2, save to disk, cache in DB. Returns URL or None."""
    db = get_supabase_client()
    settings = get_settings()
    p_hash = _prompt_hash(cache_key)

    # Check cache (generated_images uses prompt_hash as unique key)
    cached = maybe_single_data(
        db.table("generated_images")
        .select("image_url")
        .eq("prompt_hash", p_hash)
    )
    if cached:
        return cached["image_url"]

    try:
        client = _get_genai_client()
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            ),
        )

        # Extract image data from response
        image_data = None
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_data = part.inline_data.data
                    break

        if not image_data:
            logger.warning("No image data in Nano Banana response for: %s", prompt[:100])
            return None

        # Save to disk
        media_path = _ensure_media_dir(campaign_id)
        filename = f"{uuid.uuid4().hex}.png"
        filepath = os.path.join(media_path, filename)

        with open(filepath, "wb") as f:
            f.write(image_data)

        image_url = f"{settings.media_url_prefix}/{campaign_id}/{filename}"

        # Cache in DB
        try:
            db.table("generated_images").insert({
                "prompt_hash": p_hash,
                "prompt": prompt[:500],
                "image_url": image_url,
                "type": image_type,
            }).execute()
        except Exception:
            pass  # DB cache failure shouldn't break anything

        logger.info("Generated %s image: %s", image_type, image_url)
        return image_url

    except Exception as e:
        logger.error("Image generation failed: %s", e)
        return None


async def generate_location_image(
    campaign_id: str,
    location: str,
    region: str,
    narrative: str,
) -> str | None:
    """Generate a scene image for a location. Cached per location+campaign."""
    cache_key = f"location:{campaign_id}:{location}"

    # Check cache first (fast path)
    db = get_supabase_client()
    cached = maybe_single_data(
        db.table("generated_images")
        .select("image_url")
        .eq("prompt_hash", _prompt_hash(cache_key))
    )
    if cached:
        return cached["image_url"]

    # Build detailed prompt
    prompt = (
        f"{STYLE_PREFIX}. "
        f"A vivid scene of '{location}' in the region '{region}'. "
        f"Context: {narrative[:300]}. "
        f"Wide establishing shot, rich environment details, "
        f"medieval fantasy setting, moody atmosphere."
    )

    url = await generate_and_save(prompt, campaign_id, "scene", cache_key)

    # Also save to locations table
    if url:
        try:
            db.table("locations").upsert({
                "campaign_id": campaign_id,
                "name": location,
                "region": region,
                "image_url": url,
                "image_prompt": prompt[:500],
            }, on_conflict="campaign_id,name").execute()
        except Exception:
            pass

    return url


async def generate_npc_portrait(
    campaign_id: str,
    npc: dict,
) -> str | None:
    """Generate a portrait for an NPC. Cached per NPC ID."""
    # Already has portrait
    if npc.get("portrait_url"):
        return npc["portrait_url"]

    cache_key = f"npc:{npc['id']}"

    prompt = (
        f"{STYLE_PREFIX}. "
        f"Portrait of {npc.get('name', 'Unknown')}, "
        f"a {npc.get('race', 'Human')} "
        f"{'merchant ' if npc.get('is_merchant') else ''}"
        f"in a D&D fantasy world. "
        f"Personality: {npc.get('personality', 'mysterious')}. "
        f"Location: {npc.get('location', 'town')}. "
        f"Bust shot, detailed face, expressive eyes, "
        f"medieval fantasy clothing appropriate to their role."
    )

    url = await generate_and_save(prompt, campaign_id, "portrait", cache_key)

    # Store on NPC record
    if url:
        db = get_supabase_client()
        try:
            db.table("npcs").update({
                "portrait_url": url,
                "portrait_prompt": prompt[:500],
            }).eq("id", npc["id"]).execute()
        except Exception:
            pass

    return url
