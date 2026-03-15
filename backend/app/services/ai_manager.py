"""AI Manager — handles all Claude API calls."""
from __future__ import annotations

import json
import hashlib

import anthropic
from openai import AsyncOpenAI

from app.core.config import get_settings


def _get_anthropic_client() -> anthropic.AsyncAnthropic:
    settings = get_settings()
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _get_openai_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def call_claude(
    system: str,
    messages: list[dict],
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 1024,
) -> str:
    """Call Claude API and return the text response."""
    client = _get_anthropic_client()
    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    return response.content[0].text


async def call_dm(system_prompt: str, recent_chat: list[dict], player_action: str) -> dict:
    """Call Claude as the DM and parse the JSON response."""
    messages = []
    for msg in recent_chat:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": player_action})

    raw = await call_claude(system=system_prompt, messages=messages)

    # Parse JSON — strip any accidental markdown
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    return json.loads(text)


async def call_npc(system_prompt: str, chat_history: list[dict], player_message: str) -> dict:
    """Call Claude as an NPC and parse the JSON response."""
    messages = []
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": player_message})

    raw = await call_claude(system=system_prompt, messages=messages, max_tokens=512)
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    return json.loads(text)


async def summarize_history(chat_text: str) -> str:
    """Compress chat history into 2-3 sentence summary."""
    return await call_claude(
        system=(
            "Compress this D&D gameplay into 2-3 sentences. "
            "Focus on: key decisions, NPCs met, enemies defeated, items found, "
            "locations visited, quest progress. Be concise. Write in Russian."
        ),
        messages=[{"role": "user", "content": chat_text}],
        max_tokens=256,
    )


async def mega_compress(text: str) -> str:
    """Compress multiple summaries into a single paragraph."""
    return await call_claude(
        system="Compress this story recap into 2 sentences. Keep only the most important events. Russian.",
        messages=[{"role": "user", "content": text}],
        max_tokens=128,
    )


# ── Image Generation ──
STYLE_PREFIX = "Dark fantasy oil painting, dramatic lighting, D&D art style, detailed, atmospheric"


def build_scene_prompt(location: str, description: str, mood: str = "dark") -> str:
    return f"{STYLE_PREFIX}, {description}, {location}, {mood} mood, no text, no words"


def build_portrait_prompt(race: str, char_class: str, appearance: str = "") -> str:
    return f"{STYLE_PREFIX}, portrait of a {race} {char_class}, {appearance}, bust shot, no text"


def build_enemy_prompt(enemy_name: str, description: str) -> str:
    return f"{STYLE_PREFIX}, {enemy_name}, {description}, menacing, battle-ready, no text"


def build_item_prompt(item_name: str, description: str, rarity: str) -> str:
    glow = "magical glow, enchanted" if rarity in ("rare", "epic", "legendary") else ""
    return f"{STYLE_PREFIX}, {item_name}, {description}, {glow}, item art, dark background, no text"


async def generate_image(prompt: str) -> str:
    """Generate an image via DALL-E 3 and return the URL."""
    client = _get_openai_client()
    response = await client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


async def generate_merchant_inventory(npc: dict) -> list[dict]:
    """Generate themed inventory for a merchant NPC. Returns list of item template dicts."""
    raw = await call_claude(
        system=(
            "You generate item inventories for D&D 5e merchant NPCs. "
            "Return a JSON array of 6-10 items. Each item has: "
            "name (English), name_ru (Russian), type (weapon|armor|consumable|material|scroll|misc), "
            "rarity (common|uncommon|rare), value (gold pieces integer), "
            "description_ru (short Russian description), "
            "damage_dice (e.g. '1d8' for weapons, null otherwise), "
            "ac_bonus (integer for armor, 0 otherwise), "
            "slot (weapon|head|chest|legs|boots|offhand for equippable, null otherwise), "
            "stackable (true for consumables/materials, false otherwise). "
            "Match the merchant's personality and location. "
            "Return JSON array only. No markdown."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Merchant: {npc.get('name', 'Unknown')} ({npc.get('race', 'Human')})\n"
                f"Personality: {npc.get('personality', 'Trader')}\n"
                f"Location: {npc.get('location', 'Town')}, {npc.get('region', 'Unknown Region')}\n"
                f"Generate their shop inventory."
            ),
        }],
        max_tokens=1024,
    )

    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    return json.loads(text)
