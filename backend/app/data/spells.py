"""Spell definitions and class spell slot progressions for D&D 5e."""

SPELLS = {
    # ── Cantrips (level 0) ──
    "fire_bolt": {
        "name": "Fire Bolt", "name_ru": "Огненный снаряд",
        "level": 0, "classes": ["Wizard", "Sorcerer"],
        "damage_dice": "1d10", "damage_type": "fire",
        "school": "evocation",
        "description_ru": "Огненный луч поражает цель",
    },
    "ray_of_frost": {
        "name": "Ray of Frost", "name_ru": "Луч холода",
        "level": 0, "classes": ["Wizard", "Sorcerer"],
        "damage_dice": "1d8", "damage_type": "cold",
        "school": "evocation",
        "description_ru": "Ледяной луч замедляет врага",
    },
    "sacred_flame": {
        "name": "Sacred Flame", "name_ru": "Священное пламя",
        "level": 0, "classes": ["Cleric"],
        "damage_dice": "1d8", "damage_type": "radiant", "save": "dex",
        "school": "evocation",
        "description_ru": "Божественное пламя обрушивается на врага",
    },
    "eldritch_blast": {
        "name": "Eldritch Blast", "name_ru": "Мистический заряд",
        "level": 0, "classes": ["Warlock"],
        "damage_dice": "1d10", "damage_type": "force",
        "school": "evocation",
        "description_ru": "Поток мистической энергии поражает цель",
    },
    "guidance": {
        "name": "Guidance", "name_ru": "Направление",
        "level": 0, "classes": ["Cleric", "Druid"],
        "school": "divination",
        "description_ru": "Цель получает +1d4 к следующей проверке способности",
    },
    "vicious_mockery": {
        "name": "Vicious Mockery", "name_ru": "Злая насмешка",
        "level": 0, "classes": ["Bard"],
        "damage_dice": "1d4", "damage_type": "psychic", "save": "wis",
        "school": "enchantment",
        "description_ru": "Магическое оскорбление наносит психический урон",
    },
    "produce_flame": {
        "name": "Produce Flame", "name_ru": "Сотворение пламени",
        "level": 0, "classes": ["Druid"],
        "damage_dice": "1d8", "damage_type": "fire",
        "school": "conjuration",
        "description_ru": "Пламя в руке, которое можно метнуть",
    },
    "shocking_grasp": {
        "name": "Shocking Grasp", "name_ru": "Шокирующее касание",
        "level": 0, "classes": ["Wizard", "Sorcerer"],
        "damage_dice": "1d8", "damage_type": "lightning",
        "school": "evocation",
        "description_ru": "Электрический разряд при касании",
    },
    # ── Level 1 Spells ──
    "magic_missile": {
        "name": "Magic Missile", "name_ru": "Волшебная стрела",
        "level": 1, "classes": ["Wizard", "Sorcerer"],
        "damage_dice": "3d4+3", "damage_type": "force",
        "school": "evocation", "auto_hit": True,
        "description_ru": "Три светящиеся стрелы автоматически поражают цель",
    },
    "shield": {
        "name": "Shield", "name_ru": "Щит",
        "level": 1, "classes": ["Wizard", "Sorcerer"],
        "school": "abjuration", "reaction": True,
        "description_ru": "+5 к AC до следующего хода",
    },
    "mage_armor": {
        "name": "Mage Armor", "name_ru": "Доспехи мага",
        "level": 1, "classes": ["Wizard", "Sorcerer"],
        "school": "abjuration",
        "description_ru": "AC становится 13 + модификатор Ловкости",
    },
    "cure_wounds": {
        "name": "Cure Wounds", "name_ru": "Лечение ран",
        "level": 1, "classes": ["Cleric", "Paladin", "Bard", "Druid", "Ranger"],
        "heal_dice": "1d8", "school": "evocation",
        "description_ru": "Исцеляет прикосновением",
    },
    "healing_word": {
        "name": "Healing Word", "name_ru": "Целительное слово",
        "level": 1, "classes": ["Cleric", "Bard", "Druid"],
        "heal_dice": "1d4", "school": "evocation",
        "description_ru": "Исцеление словом на расстоянии",
    },
    "guiding_bolt": {
        "name": "Guiding Bolt", "name_ru": "Направляющий заряд",
        "level": 1, "classes": ["Cleric"],
        "damage_dice": "4d6", "damage_type": "radiant",
        "school": "evocation",
        "description_ru": "Луч света поражает врага, следующая атака по нему с преимуществом",
    },
    "bless": {
        "name": "Bless", "name_ru": "Благословение",
        "level": 1, "classes": ["Cleric", "Paladin"],
        "school": "enchantment",
        "description_ru": "До 3 существ получают +1d4 к атакам и спасброскам",
    },
    "thunderwave": {
        "name": "Thunderwave", "name_ru": "Волна грома",
        "level": 1, "classes": ["Wizard", "Sorcerer", "Bard", "Druid"],
        "damage_dice": "2d8", "damage_type": "thunder", "save": "con",
        "school": "evocation",
        "description_ru": "Волна грома отбрасывает врагов",
    },
    "burning_hands": {
        "name": "Burning Hands", "name_ru": "Огненные ладони",
        "level": 1, "classes": ["Wizard", "Sorcerer"],
        "damage_dice": "3d6", "damage_type": "fire", "save": "dex",
        "school": "evocation",
        "description_ru": "Конус пламени из рук",
    },
    "hex": {
        "name": "Hex", "name_ru": "Сглаз",
        "level": 1, "classes": ["Warlock"],
        "damage_dice": "1d6", "damage_type": "necrotic",
        "school": "enchantment",
        "description_ru": "Проклятие: дополнительный урон при каждой атаке по цели",
    },
    "hunters_mark": {
        "name": "Hunter's Mark", "name_ru": "Метка охотника",
        "level": 1, "classes": ["Ranger"],
        "damage_dice": "1d6", "damage_type": "force",
        "school": "divination",
        "description_ru": "Дополнительный урон по отмеченной цели",
    },
    "smite": {
        "name": "Divine Smite", "name_ru": "Божественная кара",
        "level": 1, "classes": ["Paladin"],
        "damage_dice": "2d8", "damage_type": "radiant",
        "school": "evocation",
        "description_ru": "Божественная энергия усиливает удар оружием",
    },
    "entangle": {
        "name": "Entangle", "name_ru": "Опутывание",
        "level": 1, "classes": ["Druid", "Ranger"],
        "save": "str", "school": "conjuration",
        "description_ru": "Лианы опутывают врагов в области",
    },
    "sleep": {
        "name": "Sleep", "name_ru": "Усыпление",
        "level": 1, "classes": ["Wizard", "Sorcerer", "Bard"],
        "school": "enchantment",
        "description_ru": "Усыпляет существ с суммарно 5d8 HP",
    },
    # ── Level 2 Spells ──
    "scorching_ray": {
        "name": "Scorching Ray", "name_ru": "Палящий луч",
        "level": 2, "classes": ["Wizard", "Sorcerer"],
        "damage_dice": "2d6", "damage_type": "fire",
        "school": "evocation",
        "description_ru": "Три огненных луча поражают цели",
    },
    "misty_step": {
        "name": "Misty Step", "name_ru": "Туманный шаг",
        "level": 2, "classes": ["Wizard", "Sorcerer", "Warlock"],
        "school": "conjuration",
        "description_ru": "Телепортация на 30 футов бонусным действием",
    },
    "spiritual_weapon": {
        "name": "Spiritual Weapon", "name_ru": "Духовное оружие",
        "level": 2, "classes": ["Cleric"],
        "damage_dice": "1d8", "damage_type": "force",
        "school": "evocation",
        "description_ru": "Призрачное оружие атакует бонусным действием",
    },
    "hold_person": {
        "name": "Hold Person", "name_ru": "Удержание личности",
        "level": 2, "classes": ["Wizard", "Sorcerer", "Cleric", "Bard", "Warlock", "Druid"],
        "save": "wis", "school": "enchantment",
        "description_ru": "Парализует гуманоида",
    },
    "lesser_restoration": {
        "name": "Lesser Restoration", "name_ru": "Малое восстановление",
        "level": 2, "classes": ["Cleric", "Paladin", "Druid", "Bard", "Ranger"],
        "school": "abjuration",
        "description_ru": "Снимает болезнь, отравление, слепоту или паралич",
    },
    "shatter": {
        "name": "Shatter", "name_ru": "Дребезги",
        "level": 2, "classes": ["Wizard", "Sorcerer", "Bard", "Warlock"],
        "damage_dice": "3d8", "damage_type": "thunder", "save": "con",
        "school": "evocation",
        "description_ru": "Оглушительный звук наносит урон в области",
    },
    # ── Level 3 Spells ──
    "fireball": {
        "name": "Fireball", "name_ru": "Огненный шар",
        "level": 3, "classes": ["Wizard", "Sorcerer"],
        "damage_dice": "8d6", "damage_type": "fire", "save": "dex",
        "school": "evocation",
        "description_ru": "Взрыв пламени в области 20 футов",
    },
    "lightning_bolt": {
        "name": "Lightning Bolt", "name_ru": "Молния",
        "level": 3, "classes": ["Wizard", "Sorcerer"],
        "damage_dice": "8d6", "damage_type": "lightning", "save": "dex",
        "school": "evocation",
        "description_ru": "Молния пронзает всех на линии 100 футов",
    },
    "spirit_guardians": {
        "name": "Spirit Guardians", "name_ru": "Духовные стражи",
        "level": 3, "classes": ["Cleric"],
        "damage_dice": "3d8", "damage_type": "radiant", "save": "wis",
        "school": "conjuration",
        "description_ru": "Духи окружают вас и наносят урон врагам рядом",
    },
    "revivify": {
        "name": "Revivify", "name_ru": "Оживление",
        "level": 3, "classes": ["Cleric", "Paladin", "Druid"],
        "school": "necromancy",
        "description_ru": "Возвращает к жизни существо, умершее не более минуты назад",
    },
    "counterspell": {
        "name": "Counterspell", "name_ru": "Контрзаклинание",
        "level": 3, "classes": ["Wizard", "Sorcerer", "Warlock"],
        "school": "abjuration", "reaction": True,
        "description_ru": "Прерывает заклинание 3-го уровня или ниже",
    },
}

# Spell slots per class per character level
CLASS_SPELL_SLOTS = {
    "Wizard":   {1: {"1": 2}, 2: {"1": 3}, 3: {"1": 4, "2": 2}, 4: {"1": 4, "2": 3}, 5: {"1": 4, "2": 3, "3": 2}},
    "Sorcerer": {1: {"1": 2}, 2: {"1": 3}, 3: {"1": 4, "2": 2}, 4: {"1": 4, "2": 3}, 5: {"1": 4, "2": 3, "3": 2}},
    "Cleric":   {1: {"1": 2}, 2: {"1": 3}, 3: {"1": 4, "2": 2}, 4: {"1": 4, "2": 3}, 5: {"1": 4, "2": 3, "3": 2}},
    "Bard":     {1: {"1": 2}, 2: {"1": 3}, 3: {"1": 4, "2": 2}, 4: {"1": 4, "2": 3}, 5: {"1": 4, "2": 3, "3": 2}},
    "Druid":    {1: {"1": 2}, 2: {"1": 3}, 3: {"1": 4, "2": 2}, 4: {"1": 4, "2": 3}, 5: {"1": 4, "2": 3, "3": 2}},
    "Warlock":  {1: {"1": 1}, 2: {"1": 2}, 3: {"1": 2, "2": 1}, 4: {"1": 2, "2": 2}, 5: {"1": 2, "2": 2, "3": 1}},
    "Paladin":  {1: {}, 2: {"1": 2}, 3: {"1": 3}, 4: {"1": 3}, 5: {"1": 4, "2": 2}},
    "Ranger":   {1: {}, 2: {"1": 2}, 3: {"1": 3}, 4: {"1": 3}, 5: {"1": 4, "2": 2}},
    # Non-casters
    "Fighter":  {},
    "Barbarian": {},
    "Rogue":    {},
    "Monk":     {},
}

# Starting spells per class (known at level 1)
CLASS_STARTING_SPELLS = {
    "Wizard":   ["fire_bolt", "ray_of_frost", "magic_missile", "shield", "mage_armor"],
    "Sorcerer": ["fire_bolt", "shocking_grasp", "magic_missile", "burning_hands", "shield"],
    "Cleric":   ["sacred_flame", "guidance", "cure_wounds", "bless", "guiding_bolt"],
    "Bard":     ["vicious_mockery", "healing_word", "thunderwave", "sleep"],
    "Druid":    ["produce_flame", "guidance", "cure_wounds", "entangle"],
    "Warlock":  ["eldritch_blast", "hex", "burning_hands"],
    "Paladin":  ["cure_wounds", "bless", "smite"],
    "Ranger":   ["cure_wounds", "hunters_mark"],
    "Fighter":  [],
    "Barbarian": [],
    "Rogue":    [],
    "Monk":     [],
}

# Spellcasting ability per class
CLASS_SPELL_ABILITY = {
    "Wizard": "int_",
    "Sorcerer": "cha",
    "Cleric": "wis",
    "Bard": "cha",
    "Druid": "wis",
    "Warlock": "cha",
    "Paladin": "cha",
    "Ranger": "wis",
}
