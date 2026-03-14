"use client";

import { useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { rollStats, createCharacter } from "@/lib/api";

const RACES = [
  "Human", "Elf", "Dwarf", "Halfling", "Half-Orc",
  "Gnome", "Tiefling", "Dragonborn", "Half-Elf",
];

const CLASSES = [
  "Fighter", "Wizard", "Rogue", "Cleric", "Ranger", "Paladin",
  "Barbarian", "Bard", "Druid", "Monk", "Sorcerer", "Warlock",
];

const STAT_NAMES = ["STR", "DEX", "CON", "INT", "WIS", "CHA"] as const;
const STAT_KEYS = ["str", "dex", "con", "int", "wis", "cha"] as const;

export default function NewCharacterPage() {
  const router = useRouter();
  const params = useSearchParams();
  const campaignId = params.get("id");

  const [name, setName] = useState("");
  const [race, setRace] = useState("Human");
  const [charClass, setCharClass] = useState("Fighter");
  const [stats, setStats] = useState<number[] | null>(null);
  const [allRolls, setAllRolls] = useState<number[][] | null>(null);
  const [rolling, setRolling] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const handleRoll = useCallback(async () => {
    if (!campaignId) return;
    setRolling(true);
    try {
      const result = await rollStats(campaignId);
      setStats(result.totals);
      setAllRolls(result.rolls);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Roll failed");
    } finally {
      setRolling(false);
    }
  }, [campaignId]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!campaignId || !stats || !name.trim()) return;
    setCreating(true);
    setError("");
    try {
      const statObj: Record<string, number> = {};
      STAT_KEYS.forEach((key, i) => {
        statObj[key] = stats[i];
      });
      await createCharacter(campaignId, {
        name: name.trim(),
        race,
        class: charClass,
        stats: statObj as { str: number; dex: number; con: number; int: number; wis: number; cha: number },
      });
      router.push(`/play/${campaignId}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Creation failed");
      setCreating(false);
    }
  }

  if (!campaignId) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <p className="text-red-400">Missing campaign ID</p>
      </main>
    );
  }

  return (
    <main className="max-w-lg mx-auto px-4 py-12">
      <h1 className="text-3xl font-bold mb-8 text-[var(--color-gold)]">
        Create Your Hero
      </h1>

      <form onSubmit={handleCreate} className="space-y-6">
        {error && <p className="text-red-400 text-sm">{error}</p>}

        {/* Name */}
        <label className="block">
          <span className="text-sm text-gray-400">Character Name</span>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-[var(--color-gold)]"
            placeholder="Aragorn, Drizzt, Gandalf..."
          />
        </label>

        {/* Race */}
        <label className="block">
          <span className="text-sm text-gray-400">Race</span>
          <select
            value={race}
            onChange={(e) => setRace(e.target.value)}
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-[var(--color-gold)]"
          >
            {RACES.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>

        {/* Class */}
        <label className="block">
          <span className="text-sm text-gray-400">Class</span>
          <select
            value={charClass}
            onChange={(e) => setCharClass(e.target.value)}
            className="mt-1 w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-[var(--color-gold)]"
          >
            {CLASSES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>

        {/* Stats */}
        <div>
          <div className="flex justify-between items-center mb-3">
            <span className="text-sm text-gray-400">Ability Scores</span>
            <button
              type="button"
              onClick={handleRoll}
              disabled={rolling}
              className="px-4 py-1 text-sm bg-gray-800 border border-gray-700 rounded-lg hover:border-[var(--color-gold)] transition disabled:opacity-50"
            >
              {rolling ? "Rolling..." : stats ? "Re-roll" : "Roll 4d6 drop lowest"}
            </button>
          </div>

          {stats ? (
            <div className="grid grid-cols-3 gap-3">
              {STAT_NAMES.map((label, i) => (
                <div
                  key={label}
                  className="bg-gray-800 rounded-lg p-3 text-center border border-gray-700"
                >
                  <div className="text-xs text-gray-500 mb-1">{label}</div>
                  <div className="text-2xl font-bold text-[var(--color-gold)]">
                    {stats[i]}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">
                    {allRolls?.[i]?.join(", ")}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-600 text-sm text-center py-4">
              Click &quot;Roll&quot; to generate ability scores
            </p>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={creating || !stats || !name.trim()}
          className="w-full py-3 bg-[var(--color-gold)] text-gray-950 font-semibold rounded-lg hover:brightness-110 transition disabled:opacity-50"
        >
          {creating ? "Creating..." : "Begin Adventure"}
        </button>
      </form>
    </main>
  );
}
