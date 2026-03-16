"""Tiered context manager for AI DM calls.

Keeps context flat at ~10000 tokens regardless of campaign length.
"""
from __future__ import annotations

import json
from typing import Any


def compute_effective_stats(character: dict, equipment: list[dict]) -> dict:
    """Compute effective stats with equipment bonuses applied."""
    stats = {
        "str": character["str"], "dex": character["dex"], "con": character["con"],
        "int_": character["int_"], "wis": character["wis"], "cha": character["cha"],
        "ac": character["ac"],
    }
    for eq in equipment:
        inst = eq.get("item_instances") or {}
        tmpl = inst.get("item_templates") or {} if isinstance(inst, dict) else {}
        bonuses = tmpl.get("stat_bonuses") or {}
        if isinstance(bonuses, dict):
            for stat_key, bonus in bonuses.items():
                if stat_key in stats and isinstance(bonus, (int, float)):
                    stats[stat_key] += int(bonus)
        if tmpl.get("ac_bonus"):
            stats["ac"] += tmpl["ac_bonus"]
    return stats


def format_character_sheet(char: dict, effective: dict | None = None) -> str:
    """Format character data into a compact text block."""
    mod = lambda s: (s - 10) // 2
    eff = effective or char

    def stat_str(key, label):
        base = char[key]
        val = eff.get(key, base)
        if val != base:
            return f"{label}: {val}({mod(val):+d}) [base {base}]"
        return f"{label}: {val}({mod(val):+d})"

    ac_base = char["ac"]
    ac_eff = eff.get("ac", ac_base)
    ac_str = f"AC: {ac_eff}" + (f" [base {ac_base}]" if ac_eff != ac_base else "")

    return (
        f"{char['name']} — Level {char['level']} {char['race']} {char['class']}\n"
        f"HP: {char['hp']}/{char['max_hp']} | {ac_str} | XP: {char['xp']}\n"
        f"{stat_str('str', 'STR')} {stat_str('dex', 'DEX')} {stat_str('con', 'CON')}\n"
        f"{stat_str('int_', 'INT')} {stat_str('wis', 'WIS')} {stat_str('cha', 'CHA')}\n"
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


def format_abilities(abilities: list[dict]) -> str:
    """Format character abilities into compact text by category."""
    if not abilities:
        return "None"
    by_cat: dict[str, list[str]] = {}
    for a in abilities:
        cat = a.get("category", "misc")
        by_cat.setdefault(cat, []).append(a.get("name_ru", a["name"]))
    cat_labels = {
        "proficiency": "Prof", "language": "Lang", "recipe": "Recipes",
        "technique": "Tech", "lore": "Lore", "feat": "Feats",
        "spell": "Learned Spells", "misc": "Other",
    }
    lines = []
    for cat, names in by_cat.items():
        lines.append(f"{cat_labels.get(cat, cat)}: {', '.join(names)}")
    return " | ".join(lines)


def format_factions(factions: list[dict]) -> str:
    """Format faction reputation."""
    if not factions:
        return "None"
    return ", ".join(f"{f['faction']}({f['reputation']:+d})" for f in factions)


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
    """Format nearby NPCs with rich detail so DM knows who they are."""
    if not npcs:
        return "None nearby"
    lines = []
    for n in npcs:
        tags = []
        if n.get("is_merchant"):
            tags.append("MERCHANT")
        if n.get("faction"):
            tags.append(n["faction"])
        tag_str = f" [{', '.join(tags)}]" if tags else ""
        name = n.get("name_ru") or n["name"]
        race = n.get("race", "")
        disp = n.get("disposition", "neutral")
        personality = n.get("personality") or ""
        backstory = n.get("backstory") or ""

        line = f"• {name} ({race}, {disp}){tag_str}"
        if personality and personality != "Mysterious stranger":
            line += f" — {personality}"
        if backstory:
            # Truncate backstory to ~100 chars for context budget
            bs = backstory[:100] + "..." if len(backstory) > 100 else backstory
            line += f" | {bs}"

        # Include last 2 memories for continuity
        memories = n.get("memories") or []
        if memories:
            recent = memories[-2:]
            line += f" | Помнит: {'; '.join(str(m) for m in recent)}"

        lines.append(line)
    return "\n".join(lines)


def format_known_npcs(npcs: list[dict]) -> str:
    """Compact list of NPCs in other locations so DM doesn't recreate them."""
    if not npcs:
        return "None"
    lines = []
    for n in npcs:
        name = n.get("name_ru") or n.get("name", "?")
        loc = n.get("location", "?")
        merchant = " [M]" if n.get("is_merchant") else ""
        lines.append(f"{name}@{loc}{merchant}")
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
    all_other_npcs: list[dict] | None = None,
    active_quests: list[dict] | None = None,
    abilities: list[dict] | None = None,
    faction_rep: list[dict] | None = None,
) -> tuple[str, list[dict]]:
    """Build the full DM system prompt from tiered context."""

    # Effective stats with equipment bonuses
    effective = compute_effective_stats(character, equipment)

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
{format_character_sheet(character, effective)}
Equipment: {format_equipment(equipment)}
Inventory: {format_inventory(inventory)}
Spells: {format_spells(character)}
Abilities: {format_abilities(abilities or [])}

=== COMPANIONS ===
{format_companions(companions)}

=== STORY SO FAR ===
{story_so_far}

=== ACTIVE QUESTS ===
{format_quests(active_quests)}

=== CURRENT LOCATION ===
{character.get('location', 'Unknown')} (Region: {character.get('region', 'Starting Region')})

NPCs here:
{format_nearby_npcs(nearby_npcs)}

NPCs elsewhere (DO NOT recreate these): {format_known_npcs(all_other_npcs or [])}

=== WORLD STATE ===
Flags: {json.dumps(flags)}
Factions: {format_factions(faction_rep or [])}
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
  "new_npcs": [{{"name": "Name", "name_ru": "Имя", "race": "Human", "personality": "краткое описание личности и роли", "backstory": "1-2 предложения о прошлом и роли в мире", "disposition": "neutral", "is_merchant": false}}],
  "combat_status": "none",
  "enemies": null,
  "conditions_gained": [],
  "conditions_lost": [],
  "quest_update": null,
  "abilities_gained": [],
  "abilities_lost": [],
  "flags_set": {{}},
  "faction_changes": [],
  "suggestions": ["Action 1 in Russian", "Action 2", "Action 3"]
}}

quest_update format (when player completes a quest objective):
{{"title": "quest title", "objective_completed": "objective text"}}

abilities_gained format (when character learns something new from events, books, training):
[{{"category": "proficiency|language|recipe|technique|lore|feat|spell|misc", "name": "english_key", "name_ru": "Название", "description_ru": "Описание", "data": {{}}}}]
abilities_lost: list ability names when character loses knowledge (curse, etc).

faction_changes format: [{{"faction": "Faction Name", "change": -10}}]

flags_set: set world state flags when important events happen (door opened, boss defeated, secret discovered, etc).

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
- NPCs have distinct personalities, roles, and backstories. NEVER confuse one NPC with another.
- When creating new NPCs via new_npcs, ALWAYS include personality (their role and character) and backstory (1-2 sentences).
- NEVER recreate an NPC that already exists (check "NPCs elsewhere" list above). Use existing NPCs by name.
- When referencing an NPC in narrative, stay consistent with their established personality and role.
- Consequences matter. The world remembers.
- Create quest hooks from NPC interactions naturally.
- Vary encounters: combat, puzzles, traps, social, exploration.
- Reference the story so far for continuity.
- Apply conditions via conditions_gained when relevant (poison traps, fear effects, etc).
- When a quest objective is completed, set quest_update with quest title and completed objective text.
- Character abilities (proficiencies, recipes, languages, lore) are listed above. Reference them when relevant.
- When the character learns something new (from books, events, training, discoveries), add it to abilities_gained with the appropriate category.
- When proficiency is relevant to an action, apply advantage or appropriate bonus.
- Item stat bonuses are already factored into effective stats shown above.
- Set flags_set for important world state changes (doors unlocked, bosses killed, secrets found).
- Use faction_changes when actions affect faction standing (helping/attacking faction members, completing faction quests)."""

    return context, recent_chat


def build_npc_context(npc: dict, character: dict, abilities: list[dict] | None = None) -> str:
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

    abilities_text = ""
    if abilities:
        known_names = [a.get("name_ru", a["name"]) for a in abilities[:20]]
        abilities_text = f"\nPlayer already knows: {', '.join(known_names)}"

    return f"""You are {npc['name']}{', ' + npc.get('title', '') if npc.get('title') else ''}.
Race: {npc.get('race', 'Unknown')} | Location: {npc.get('location', 'Unknown')}
Personality: {npc.get('personality', 'Mysterious')}
Backstory: {npc.get('backstory', 'Unknown')}
Dialogue style: {npc.get('dialogue_style', 'Normal')}
Disposition: {npc.get('disposition', 'neutral')} (reputation: {rep})

Memories of this player:
{memories_text}

Speaking with: {character['name']}, Level {character['level']} {character['race']} {character['class']}
{abilities_text}
{merchant_block}
{hostility}

Respond in Russian. Stay in character. 2-4 sentences.

Respond as JSON only. No markdown. No backticks.
{{"dialogue": "your response in Russian",
  "reputation_change": 0,
  "new_memory": null,
  "quest_offered": null,
  "shop_discount": 0,
  "taught": null,
  "secret_shared": null}}

quest_offered format (only when NPC naturally wants to offer a quest):
{{"title": "quest title", "title_ru": "название квеста", "description": "description", "description_ru": "описание", "objectives": [{{"text": "objective text", "completed": false}}], "rewards": {{"xp": 100, "gold": 50}}}}

taught format (when NPC teaches something and it makes sense for this character):
{{"category": "proficiency|language|recipe|technique|lore|feat|spell|misc", "name": "english_key", "name_ru": "Название", "description_ru": "Краткое описание", "data": {{}}, "gold_cost": 0}}
Only teach what your character would realistically know. Charge a fair price (5-50 gold).
Do NOT teach if the player already knows it (check their known abilities above).

secret_shared format (when NPC reveals important information the DM should know):
{{"text": "the secret", "flag_key": "flag_name", "flag_value": true}}"""
