"""Tiered context manager for AI DM calls.

Keeps context flat at ~6000 tokens regardless of campaign length.
"""
from __future__ import annotations

import json
from typing import Any


def format_character_sheet(char: dict) -> str:
    """Format character data into a compact text block."""
    mod = lambda s: (s - 10) // 2
    return (
        f"{char['name']} — Level {char['level']} {char['race']} {char['class']}\n"
        f"HP: {char['hp']}/{char['max_hp']} | AC: {char['ac']} | XP: {char['xp']}\n"
        f"STR: {char['str']}({mod(char['str']):+d}) DEX: {char['dex']}({mod(char['dex']):+d}) "
        f"CON: {char['con']}({mod(char['con']):+d})\n"
        f"INT: {char['int_']}({mod(char['int_']):+d}) WIS: {char['wis']}({mod(char['wis']):+d}) "
        f"CHA: {char['cha']}({mod(char['cha']):+d})\n"
        f"Gold: {char['gold']} | Conditions: {', '.join(char.get('conditions', [])) or 'None'}"
    )


def format_equipment(equipment: list[dict]) -> str:
    if not equipment:
        return "None equipped"
    lines = []
    for e in equipment:
        inst = e.get("item_instances") or {}
        tmpl = inst.get("item_templates") or {} if isinstance(inst, dict) else {}
        name = inst.get("custom_name") or tmpl.get("name_ru") or tmpl.get("name") or "Unknown"
        extra = ""
        if tmpl.get("damage_dice"):
            extra += f" ({tmpl['damage_dice']})"
        if tmpl.get("ac_bonus"):
            extra += f" (+{tmpl['ac_bonus']} AC)"
        lines.append(f"[{e['slot']}] {name}{extra}")
    return ", ".join(lines)


def format_inventory(inventory: list[dict]) -> str:
    if not inventory:
        return "Empty"
    items = []
    for i in inventory:
        tmpl = i.get("item_templates") or {}
        name = i.get("custom_name") or tmpl.get("name_ru") or tmpl.get("name") or "?"
        items.append(f"{name} x{i.get('quantity', 1)}")
    return ", ".join(items)


def format_spells(character: dict) -> str:
    """Format known spells and available spell slots."""
    known = character.get("known_spells", [])
    if not known:
        return "No spells"
    from app.data.spells import SPELLS
    slots = character.get("spell_slots", {})
    max_slots = character.get("max_spell_slots", {})
    slot_parts = []
    for k in sorted(max_slots.keys(), key=lambda x: int(x)):
        slot_parts.append(f"Lv{k}: {slots.get(k, 0)}/{max_slots.get(k, 0)}")
    slot_text = ", ".join(slot_parts) if slot_parts else "None"
    spell_names = []
    for s in known:
        sp = SPELLS.get(s, {})
        name = sp.get("name_ru", s)
        lvl = sp.get("level", 0)
        spell_names.append(f"{name}(Lv{lvl})")
    return f"Slots: {slot_text}\nKnown: {', '.join(spell_names)}"


def format_companions(companions: list[dict]) -> str:
    if not companions:
        return "None"
    lines = []
    for c in companions:
        lines.append(
            f"{c['name']} ({c.get('race', '?')} {c.get('class', '?')}) "
            f"HP: {c['hp']}/{c['max_hp']} Loyalty: {c.get('loyalty', 50)}"
        )
    return "\n".join(lines)


def format_quests(quests: list[dict]) -> str:
    if not quests:
        return "No active quests"
    lines = []
    for q in quests:
        obj_text = ""
        if q.get("objectives"):
            obj_text = " | ".join(
                o.get("text", "") for o in q["objectives"] if not o.get("completed")
            )
        lines.append(f"• {q.get('title_ru') or q['title']}: {obj_text}")
    return "\n".join(lines)


def format_nearby_npcs(npcs: list[dict]) -> str:
    if not npcs:
        return "None nearby"
    lines = []
    for n in npcs:
        merchant = " [MERCHANT]" if n.get("is_merchant") else ""
        lines.append(f"{n.get('name_ru') or n['name']} ({n.get('disposition', 'neutral')}){merchant}")
    return ", ".join(lines)


def format_combat(combat: dict) -> str:
    if not combat:
        return ""
    enemies_text = ""
    for e in combat.get("enemies", []):
        enemies_text += f"\n  {e['name']} HP: {e['hp']}/{e['max_hp']} AC: {e['ac']}"
    return (
        f"\nRound: {combat.get('round', 1)} | Turn: {combat.get('current_turn', 0)}"
        f"\nEnemies:{enemies_text}"
    )


def format_history(messages: list[dict]) -> str:
    """Format chat history for summarizer."""
    lines = []
    for m in messages:
        prefix = "Player" if m["role"] == "user" else "DM"
        lines.append(f"{prefix}: {m['content']}")
    return "\n".join(lines)


async def build_dm_context(
    campaign: dict,
    character: dict,
    equipment: list[dict],
    inventory: list[dict],
    companions: list[dict],
    active_combat: dict | None,
    recent_chat: list[dict],
    nearby_npcs: list[dict],
    active_quests: list[dict],
) -> tuple[str, list[dict]]:
    """Build the full DM system prompt from tiered context."""

    # Tier 3: Summaries
    world_state = campaign.get("world_state", {})
    story_summaries = world_state.get("story_summaries", [])
    story_so_far = (
        "\n".join([s["text"] for s in story_summaries])
        if story_summaries
        else "The adventure has just begun."
    )

    flags = world_state.get("flags", {})
    visited = world_state.get("visited_locations", [])

    combat_block = ""
    if active_combat:
        combat_block = f"\n=== ACTIVE COMBAT ==={format_combat(active_combat)}"

    context = f"""You are a D&D 5e Dungeon Master running an open-world fantasy campaign.
ALL narration, dialogue, item names, location names, NPC speech in Russian.
JSON keys stay in English. suggested_actions in Russian.

=== CHARACTER ===
{format_character_sheet(character)}
Equipment: {format_equipment(equipment)}
Inventory: {format_inventory(inventory)}
Spells: {format_spells(character)}

=== COMPANIONS ===
{format_companions(companions)}

=== STORY SO FAR ===
{story_so_far}

=== ACTIVE QUESTS ===
{format_quests(active_quests)}

=== CURRENT LOCATION ===
{character.get('location', 'Unknown')} (Region: {character.get('region', 'Starting Region')})
Nearby NPCs: {format_nearby_npcs(nearby_npcs)}

=== WORLD STATE ===
Flags: {json.dumps(flags)}
Visited: {", ".join(visited[-20:])}
Turn: {campaign.get('turn_count', 0)}
{combat_block}

=== RESPONSE FORMAT ===
Respond with valid JSON only. No markdown. No backticks.
{{"narrative": "2-5 vivid sentences in Russian",
  "dice_rolls": [{{"type": "d20", "value": 14, "reason": "reason"}}],
  "hp_change": 0,
  "xp_gain": 0,
  "gold_change": 0,
  "items_gained": [{{"name": "Item Name", "name_ru": "Название", "type": "weapon|armor|consumable|material|quest|scroll|misc", "rarity": "common", "value": 10, "damage_dice": null, "ac_bonus": 0, "slot": null}}],
  "items_lost": ["item name"],
  "location": "Current Location",
  "region": "Current Region",
  "new_npcs": [],
  "combat_status": "none",
  "enemies": null,
  "conditions_gained": [],
  "conditions_lost": [],
  "quest_update": null,
  "suggestions": ["Action 1 in Russian", "Action 2", "Action 3"]
}}

quest_update format (when player completes a quest objective):
{{"title": "quest title", "objective_completed": "objective text"}}

items_gained: include full item data when player finds loot, receives rewards, or picks up items.
items_lost: list item names when player loses, uses, or gives away items.
conditions: poisoned, stunned, blinded, frightened, charmed, paralyzed, prone, restrained, exhausted.

=== DM RULES ===
- Open world. No linear path. Player goes wherever they want.
- Generate towns, dungeons, wilderness, NPCs organically.
- Dice rolls determine success. Use character stat modifiers.
- Combat is dangerous. Enemies attack back. Track HP.
- HP 0 = death. Make it dramatic.
- Reward XP (25-100 for encounters, 10-25 for roleplay).
- Drop loot from enemies via items_gained. Vary rarity. Include item type, value, and slot when applicable.
- NPCs have distinct personalities. Let player converse freely.
- Consequences matter. The world remembers.
- Create quest hooks from NPC interactions naturally.
- Vary encounters: combat, puzzles, traps, social, exploration.
- Reference the story so far for continuity.
- Apply conditions via conditions_gained when relevant (poison traps, fear effects, etc).
- When a quest objective is completed, set quest_update with quest title and completed objective text."""

    return context, recent_chat


def build_npc_context(npc: dict, character: dict) -> str:
    """Build system prompt for NPC conversation (used for haggling and chat)."""
    merchant_block = ""
    if npc.get("is_merchant"):
        inventory_text = json.dumps(npc.get("shop_inventory", []), ensure_ascii=False)
        merchant_block = (
            f"\nYou are a merchant. You can discuss prices and offer discounts.\n"
            f"Your inventory: {inventory_text}\n"
            f"You may offer a shop_discount (0-30) based on the player's persuasion.\n"
            f"Be shrewd but fair. High charisma players or clever arguments earn bigger discounts."
        )

    hostility = ""
    rep = npc.get("reputation", 0)
    if rep < -30:
        hostility = "\nBe hostile and unhelpful. Refuse discounts."
    elif rep > 50:
        hostility = "\nBe generous. Share secrets and tips. Offer good deals."

    memories_text = json.dumps(npc.get("memories", [])[-10:], ensure_ascii=False)

    return f"""You are {npc['name']}{', ' + npc.get('title', '') if npc.get('title') else ''}.
Race: {npc.get('race', 'Unknown')} | Location: {npc.get('location', 'Unknown')}
Personality: {npc.get('personality', 'Mysterious')}
Backstory: {npc.get('backstory', 'Unknown')}
Dialogue style: {npc.get('dialogue_style', 'Normal')}
Disposition: {npc.get('disposition', 'neutral')} (reputation: {rep})

Memories of this player:
{memories_text}

Speaking with: {character['name']}, Level {character['level']} {character['race']} {character['class']}
{merchant_block}
{hostility}

Respond in Russian. Stay in character. 2-4 sentences.

Respond as JSON only. No markdown. No backticks.
{{"dialogue": "your response in Russian",
  "reputation_change": 0,
  "new_memory": null,
  "quest_offered": null,
  "shop_discount": 0}}

quest_offered format (only when NPC naturally wants to offer a quest):
{{"title": "quest title", "title_ru": "название квеста", "description": "description", "description_ru": "описание", "objectives": [{{"text": "objective text", "completed": false}}], "rewards": {{"xp": 100, "gold": 50}}}}"""
