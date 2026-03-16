"use client";

import { useState, useCallback } from "react";
import {
  combatAction,
  type CombatEnemy,
  type CombatActionResponse,
} from "@/lib/api";

interface Props {
  campaignId: string;
  enemies: CombatEnemy[];
  round: number;
  knownSpells?: string[];
  spellSlots?: Record<string, number>;
  onCombatUpdate: (response: CombatActionResponse) => void;
  onCombatEnd: (status: string) => void;
}

// Spell name mapping (matches backend spells.py keys to Russian names)
const SPELL_NAMES: Record<string, string> = {
  fire_bolt: "Огненный снаряд",
  ray_of_frost: "Луч холода",
  sacred_flame: "Священное пламя",
  eldritch_blast: "Мистический заряд",
  guidance: "Направление",
  vicious_mockery: "Злая насмешка",
  produce_flame: "Сотворение пламени",
  shocking_grasp: "Шокирующее касание",
  magic_missile: "Волшебная стрела",
  shield: "Щит",
  mage_armor: "Доспехи мага",
  cure_wounds: "Лечение ран",
  healing_word: "Целительное слово",
  guiding_bolt: "Направляющий заряд",
  bless: "Благословение",
  thunderwave: "Волна грома",
  burning_hands: "Огненные ладони",
  hex: "Сглаз",
  hunters_mark: "Метка охотника",
  smite: "Божественная кара",
  entangle: "Опутывание",
  sleep: "Усыпление",
  scorching_ray: "Палящий луч",
  misty_step: "Туманный шаг",
  spiritual_weapon: "Духовное оружие",
  hold_person: "Удержание личности",
  lesser_restoration: "Малое восстановление",
  shatter: "Дребезги",
  fireball: "Огненный шар",
  lightning_bolt: "Молния",
  spirit_guardians: "Духовные стражи",
  revivify: "Оживление",
  counterspell: "Контрзаклинание",
};

export default function CombatPanel({
  campaignId,
  enemies: initialEnemies,
  round: initialRound,
  knownSpells = [],
  spellSlots = {},
  onCombatUpdate,
  onCombatEnd,
}: Props) {
  const [enemies, setEnemies] = useState<CombatEnemy[]>(initialEnemies);
  const [round, setRound] = useState(initialRound);
  const [log, setLog] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showSpells, setShowSpells] = useState(false);

  const hasSpellSlots = Object.values(spellSlots).some((v) => v > 0);

  const handleAction = useCallback(
    async (action: string, details = "") => {
      setLoading(true);
      setError("");
      setShowSpells(false);

      try {
        const response = await combatAction(campaignId, action, details);

        setLog((prev) => [...prev, response.narrative]);

        if (response.combat_status === "ongoing") {
          setEnemies(response.enemies);
          setRound(response.round);
          onCombatUpdate(response);
        } else {
          // Combat ended (victory, defeat, fled)
          setEnemies(response.enemies);
          setLog((prev) => [...prev, `-- ${response.combat_status.toUpperCase()} --`]);
          onCombatEnd(response.combat_status);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Action failed");
      } finally {
        setLoading(false);
      }
    },
    [campaignId, onCombatUpdate, onCombatEnd]
  );

  const aliveEnemies = enemies.filter((e) => e.hp > 0);

  return (
    <div className="border-t border-red-900/50 bg-gray-950/80">
      {/* Combat header */}
      <div className="flex items-center justify-between px-6 py-2 bg-red-950/30 border-b border-red-900/30">
        <span className="text-sm font-bold text-red-400">COMBAT</span>
        <span className="text-xs text-gray-500">Round {round}</span>
      </div>

      {/* Enemy list */}
      <div className="px-6 py-3 space-y-2">
        {aliveEnemies.map((enemy, i) => {
          const hpPct = Math.round((enemy.hp / enemy.max_hp) * 100);
          return (
            <div key={i} className="flex items-center gap-3">
              <span className="text-sm font-medium text-red-300 w-32 truncate">
                {enemy.name}
              </span>
              <div className="flex-1 h-3 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{
                    width: `${hpPct}%`,
                    backgroundColor: hpPct > 50 ? "#ef4444" : hpPct > 25 ? "#f97316" : "#7f1d1d",
                  }}
                />
              </div>
              <span className="text-xs text-gray-500 w-16 text-right">
                {enemy.hp}/{enemy.max_hp}
              </span>
              <span className="text-xs text-gray-600 w-10">AC {enemy.ac}</span>
            </div>
          );
        })}
      </div>

      {/* Combat log (last 3 entries) */}
      {log.length > 0 && (
        <div className="px-6 py-2 border-t border-gray-800/50 max-h-24 overflow-y-auto">
          {log.slice(-3).map((entry, i) => (
            <p key={i} className="text-xs text-gray-400 py-0.5">{entry}</p>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="px-6 py-1">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      {/* Spell selection */}
      {showSpells && (
        <div className="px-6 py-2 border-t border-gray-800/50 bg-gray-900/50">
          <div className="flex flex-wrap gap-2">
            {knownSpells.map((spellKey) => (
              <button
                key={spellKey}
                onClick={() => handleAction("spell", spellKey)}
                disabled={loading}
                className="text-xs px-3 py-1.5 bg-purple-900/40 text-purple-300 border border-purple-800/50 rounded-lg hover:bg-purple-900/60 transition disabled:opacity-40"
              >
                {SPELL_NAMES[spellKey] || spellKey}
              </button>
            ))}
          </div>
          {Object.keys(spellSlots).length > 0 && (
            <div className="flex gap-3 mt-2">
              {Object.entries(spellSlots).map(([level, count]) => (
                <span key={level} className="text-xs text-gray-500">
                  Lv{level}: <span className={count > 0 ? "text-purple-400" : "text-gray-600"}>{count}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 px-6 py-3 border-t border-gray-800">
        <button
          onClick={() => handleAction("attack")}
          disabled={loading}
          className="flex-1 py-2 text-sm font-semibold bg-red-900/60 text-red-200 border border-red-800/50 rounded-lg hover:bg-red-900/80 transition disabled:opacity-40"
        >
          {loading ? "..." : "Attack"}
        </button>
        {knownSpells.length > 0 && (
          <button
            onClick={() => setShowSpells(!showSpells)}
            disabled={loading || !hasSpellSlots}
            className="flex-1 py-2 text-sm font-semibold bg-purple-900/40 text-purple-200 border border-purple-800/50 rounded-lg hover:bg-purple-900/60 transition disabled:opacity-40"
          >
            Spell
          </button>
        )}
        <button
          onClick={() => handleAction("item")}
          disabled={loading}
          className="flex-1 py-2 text-sm font-semibold bg-green-900/40 text-green-200 border border-green-800/50 rounded-lg hover:bg-green-900/60 transition disabled:opacity-40"
        >
          Item
        </button>
        <button
          onClick={() => handleAction("flee")}
          disabled={loading}
          className="flex-1 py-2 text-sm font-semibold bg-gray-800 text-gray-300 border border-gray-700 rounded-lg hover:bg-gray-700 transition disabled:opacity-40"
        >
          Flee
        </button>
      </div>
    </div>
  );
}
