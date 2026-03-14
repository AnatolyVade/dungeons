"""Pydantic models for request/response validation."""
from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


# ── Auth ──
class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    user_id: str


# ── Campaign ──
class CampaignCreate(BaseModel):
    name: str


class CampaignOut(BaseModel):
    id: str
    name: str
    status: str
    turn_count: int
    created_at: str
    updated_at: str


# ── Character Creation ──
class CharacterCreate(BaseModel):
    name: str
    race: str = Field(..., pattern="^(Human|Elf|Dwarf|Halfling|Half-Orc|Gnome|Tiefling|Dragonborn|Half-Elf)$")
    char_class: str = Field(
        ...,
        alias="class",
        pattern="^(Fighter|Wizard|Rogue|Cleric|Ranger|Paladin|Barbarian|Bard|Druid|Monk|Sorcerer|Warlock)$",
    )
    stats: StatBlock


class StatBlock(BaseModel):
    str_: int = Field(..., alias="str", ge=3, le=18)
    dex: int = Field(ge=3, le=18)
    con: int = Field(ge=3, le=18)
    int_: int = Field(..., alias="int", ge=3, le=18)
    wis: int = Field(ge=3, le=18)
    cha: int = Field(ge=3, le=18)

    model_config = {"populate_by_name": True}


class CharacterOut(BaseModel):
    id: str
    name: str
    race: str
    char_class: str = Field(alias="class")
    level: int
    xp: int
    hp: int
    max_hp: int
    ac: int
    str_: int = Field(alias="str")
    dex: int
    con: int
    int_: int = Field(alias="int")
    wis: int
    cha: int
    gold: int
    location: str
    region: str
    conditions: list[Any]
    portrait_url: str | None
    is_alive: bool

    model_config = {"populate_by_name": True}


class StatRollResult(BaseModel):
    rolls: list[list[int]]
    totals: list[int]


# ── Game Actions ──
class ActionRequest(BaseModel):
    action: str


class DiceRoll(BaseModel):
    type: str
    value: int
    reason: str


class DMResponse(BaseModel):
    narrative: str
    dice_rolls: list[DiceRoll] = []
    hp_change: int = 0
    xp_gain: int = 0
    gold_change: int = 0
    items_gained: list[dict[str, Any]] = []
    items_lost: list[str] = []
    location: str | None = None
    region: str | None = None
    new_npcs: list[dict[str, Any]] = []
    combat_status: str = "none"
    enemies: Any = None
    suggestions: list[str] = []
    scene_image_url: str | None = None


# ── Combat ──
class CombatActionRequest(BaseModel):
    action: str = Field(..., pattern="^(attack|spell|item|flee|custom)$")
    details: str = ""


# ── Rest ──
class RestRequest(BaseModel):
    type: str = Field(..., pattern="^(short|long)$")
