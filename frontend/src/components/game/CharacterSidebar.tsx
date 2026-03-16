"use client";

import type { Character } from "@/lib/api";

function mod(stat: number): string {
  const m = Math.floor((stat - 10) / 2);
  return m >= 0 ? `+${m}` : `${m}`;
}

function hpColor(hp: number, maxHp: number): string {
  const pct = hp / maxHp;
  if (pct > 0.5) return "hp-bar-high";
  if (pct > 0.25) return "hp-bar-mid";
  return "hp-bar-low";
}

export default function CharacterSidebar({ character }: { character: Character }) {
  const hpPct = Math.round((character.hp / character.max_hp) * 100);
  const xpForNext = character.level * 300;
  const xpPct = Math.round((character.xp / xpForNext) * 100);

  return (
    <div className="w-72 bg-gray-900 border-l border-gray-800 p-4 overflow-y-auto flex flex-col gap-4">
      {/* Portrait placeholder */}
      {character.portrait_url ? (
        <img
          src={character.portrait_url}
          alt={character.name}
          className="w-full aspect-square object-cover rounded-lg border border-gray-700"
        />
      ) : (
        <div className="w-full aspect-square bg-gray-800 rounded-lg border border-gray-700 flex items-center justify-center text-4xl text-gray-600">
          {character.name[0]}
        </div>
      )}

      {/* Name & class */}
      <div className="text-center">
        <h2 className="text-lg font-bold">{character.name}</h2>
        <p className="text-sm text-gray-400">
          Level {character.level} {character.race} {character.class}
        </p>
      </div>

      {/* HP bar */}
      <div>
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>HP</span>
          <span>{character.hp}/{character.max_hp}</span>
        </div>
        <div className="w-full h-3 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${hpColor(character.hp, character.max_hp)}`}
            style={{ width: `${hpPct}%` }}
          />
        </div>
      </div>

      {/* XP bar */}
      <div>
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>XP</span>
          <span>{character.xp}/{xpForNext}</span>
        </div>
        <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full bg-purple-500 transition-all duration-500"
            style={{ width: `${Math.min(100, xpPct)}%` }}
          />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          ["STR", character.str],
          ["DEX", character.dex],
          ["CON", character.con],
          ["INT", character.int_],
          ["WIS", character.wis],
          ["CHA", character.cha],
        ].map(([label, val]) => (
          <div
            key={label as string}
            className="bg-gray-800 rounded p-2 text-center"
          >
            <div className="text-[10px] text-gray-500">{label as string}</div>
            <div className="text-sm font-bold">{val as number}</div>
            <div className="text-[10px] text-gray-500">
              {mod(val as number)}
            </div>
          </div>
        ))}
      </div>

      {/* Spell Slots */}
      {character.max_spell_slots && Object.keys(character.max_spell_slots).length > 0 && (
        <div>
          <span className="text-xs text-gray-500">Spell Slots</span>
          <div className="flex gap-2 mt-1">
            {Object.entries(character.max_spell_slots).map(([level, max]) => {
              const current = character.spell_slots?.[level] ?? 0;
              return (
                <div key={level} className="bg-gray-800 rounded px-2 py-1 text-center">
                  <div className="text-[10px] text-gray-500">Lv{level}</div>
                  <div className={`text-sm font-bold ${current > 0 ? "text-purple-400" : "text-gray-600"}`}>
                    {current}/{max}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* AC & Gold */}
      <div className="flex justify-between text-sm">
        <div className="bg-gray-800 rounded px-3 py-2 text-center flex-1 mr-2">
          <div className="text-[10px] text-gray-500">AC</div>
          <div className="font-bold">{character.ac}</div>
        </div>
        <div className="bg-gray-800 rounded px-3 py-2 text-center flex-1">
          <div className="text-[10px] text-gray-500">GOLD</div>
          <div className="font-bold text-[var(--color-gold)]">{character.gold}</div>
        </div>
      </div>

      {/* Location */}
      <div className="text-xs text-gray-500">
        <span className="text-gray-400">Location:</span> {character.location}
        <br />
        <span className="text-gray-400">Region:</span> {character.region}
      </div>

      {/* Conditions */}
      {character.conditions.length > 0 && (
        <div>
          <span className="text-xs text-gray-500">Conditions:</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {character.conditions.map((c, i) => (
              <span key={i} className="text-xs bg-red-900/50 text-red-300 px-2 py-0.5 rounded">
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
