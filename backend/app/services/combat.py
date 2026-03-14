"""Combat engine — all dice rolls server-side."""
import random
import re


def roll_dice(dice_str: str) -> tuple[int, list[int]]:
    """Parse '2d6+3' -> (total, individual_rolls)."""
    match = re.match(r"(\d+)d(\d+)([+-]\d+)?", dice_str)
    if not match:
        return 0, []
    count, sides, bonus = int(match[1]), int(match[2]), int(match[3] or 0)
    rolls = [random.randint(1, sides) for _ in range(count)]
    return sum(rolls) + bonus, rolls


def calc_mod(stat: int) -> int:
    """D&D 5e ability modifier."""
    return (stat - 10) // 2


def roll_4d6_drop_lowest() -> tuple[int, list[int]]:
    """Roll 4d6, drop lowest — standard D&D stat generation."""
    rolls = sorted([random.randint(1, 6) for _ in range(4)])
    return sum(rolls[1:]), rolls


def roll_stat_block() -> dict:
    """Roll a full set of 6 ability scores."""
    results = [roll_4d6_drop_lowest() for _ in range(6)]
    return {
        "rolls": [r[1] for r in results],
        "totals": [r[0] for r in results],
    }


def attack_roll(attacker_stat: int, target_ac: int) -> dict:
    """Make an attack roll against a target AC."""
    d20 = random.randint(1, 20)
    mod = calc_mod(attacker_stat)
    total = d20 + mod
    return {
        "hit": d20 == 20 or (d20 != 1 and total >= target_ac),
        "roll": d20,
        "total": total,
        "modifier": mod,
        "is_crit": d20 == 20,
        "is_fumble": d20 == 1,
    }


def saving_throw(stat_value: int, dc: int) -> dict:
    """Make a saving throw."""
    d20 = random.randint(1, 20)
    total = d20 + calc_mod(stat_value)
    return {"success": total >= dc, "roll": d20, "total": total}


# ── Starting stats by class ──
CLASS_HP_DICE = {
    "Fighter": 10, "Barbarian": 12, "Paladin": 10, "Ranger": 10,
    "Rogue": 8, "Bard": 8, "Monk": 8, "Cleric": 8, "Druid": 8,
    "Wizard": 6, "Sorcerer": 6, "Warlock": 8,
}

CLASS_BASE_AC = {
    "Fighter": 16, "Barbarian": 13, "Paladin": 16, "Ranger": 14,
    "Rogue": 13, "Bard": 12, "Monk": 12, "Cleric": 16, "Druid": 13,
    "Wizard": 11, "Sorcerer": 11, "Warlock": 12,
}


def calculate_starting_hp(char_class: str, con: int) -> int:
    """Level 1 HP = max hit die + CON modifier."""
    hit_die = CLASS_HP_DICE.get(char_class, 8)
    return hit_die + calc_mod(con)


def calculate_starting_ac(char_class: str, dex: int) -> int:
    """Simplified starting AC based on class default armor + DEX."""
    base = CLASS_BASE_AC.get(char_class, 12)
    # Light armor classes get DEX bonus, heavy armor classes don't
    if char_class in ("Wizard", "Sorcerer", "Monk", "Bard", "Rogue", "Warlock", "Ranger"):
        return base + calc_mod(dex)
    return base


class CombatManager:
    """Handles combat mechanics."""

    async def player_attack(self, character: dict, target_enemy: dict, weapon: dict) -> dict:
        stat_key = "str" if weapon.get("type") == "melee" else "dex"
        stat = character.get(stat_key, 10)
        result = attack_roll(stat, target_enemy["ac"])
        damage = 0
        if result["is_fumble"]:
            hint = "fumble"
        elif result["hit"]:
            dmg, rolls = roll_dice(weapon.get("damage_dice", "1d6"))
            if result["is_crit"]:
                crit_dmg, _ = roll_dice(weapon.get("damage_dice", "1d6"))
                dmg += crit_dmg
                hint = "critical_hit"
            else:
                hint = "hit"
            damage = max(1, dmg + calc_mod(stat))
        else:
            hint = "miss"
        target_enemy["hp"] = max(0, target_enemy["hp"] - damage)
        return {
            "result": result,
            "damage": damage,
            "hint": hint,
            "enemy_hp": target_enemy["hp"],
            "enemy_dead": target_enemy["hp"] <= 0,
        }

    async def enemy_turn(self, enemy: dict, character: dict) -> dict:
        result = attack_roll(enemy.get("attack_stat", 14), character.get("ac", 10))
        damage = 0
        if result["hit"]:
            dmg, _ = roll_dice(enemy.get("attack_dice", "1d6"))
            damage = dmg
            character["hp"] = max(0, character["hp"] - damage)
        return {
            "result": result,
            "damage": damage,
            "player_hp": character["hp"],
            "player_dead": character["hp"] <= 0,
        }
