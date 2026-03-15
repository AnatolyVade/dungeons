"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getCampaign,
  getCharacter,
  sendAction,
  rest,
  getNearbyNpcs,
  isLoggedIn,
  type Character,
  type CampaignFull,
  type NPC,
} from "@/lib/api";
import CharacterSidebar from "@/components/game/CharacterSidebar";
import NarrativeLog, { type LogEntry } from "@/components/game/NarrativeLog";
import ActionInput from "@/components/game/ActionInput";
import ShopModal from "@/components/game/ShopModal";

export default function PlayPage() {
  const { campaignId } = useParams<{ campaignId: string }>();
  const router = useRouter();

  const [campaign, setCampaign] = useState<CampaignFull | null>(null);
  const [character, setCharacter] = useState<Character | null>(null);
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState("");

  // NPCs & Shop
  const [nearbyNpcs, setNearbyNpcs] = useState<NPC[]>([]);
  const [shopNpc, setShopNpc] = useState<NPC | null>(null);

  const refreshNpcs = useCallback(async () => {
    try {
      const npcs = await getNearbyNpcs(campaignId);
      setNearbyNpcs(npcs);
    } catch {
      // silently fail
    }
  }, [campaignId]);

  const refreshCharacter = useCallback(async () => {
    const updatedChar = await getCharacter(campaignId);
    setCharacter(updatedChar);
  }, [campaignId]);

  // Load campaign and character
  useEffect(() => {
    if (!isLoggedIn()) {
      router.push("/auth/login");
      return;
    }

    async function load() {
      try {
        const c = await getCampaign(campaignId);
        setCampaign(c);

        if (!c.character) {
          router.push(`/campaigns/new?id=${campaignId}`);
          return;
        }

        const char = await getCharacter(campaignId);
        setCharacter(char);

        // Load nearby NPCs
        await refreshNpcs();

        // If first turn, show intro prompt
        if (c.turn_count === 0) {
          setSuggestions([
            "Осмотреться вокруг",
            "Поговорить с ближайшим NPC",
            "Отправиться исследовать окрестности",
          ]);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [campaignId, router, refreshNpcs]);

  const handleAction = useCallback(
    async (action: string) => {
      if (acting) return;
      setActing(true);
      setError("");

      // Add player entry
      setEntries((prev) => [...prev, { type: "player", text: action }]);

      try {
        const response = await sendAction(campaignId, action);

        // Add DM entry
        setEntries((prev) => [
          ...prev,
          {
            type: "dm",
            text: response.narrative,
            diceRolls: response.dice_rolls,
            imageUrl: response.scene_image_url,
          },
        ]);

        // Update suggestions
        setSuggestions(response.suggestions || []);

        // Refresh character state and nearby NPCs
        await refreshCharacter();
        await refreshNpcs();

        // Update campaign turn count locally
        setCampaign((prev) =>
          prev ? { ...prev, turn_count: prev.turn_count + 1 } : prev
        );
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Action failed");
        setEntries((prev) => prev.slice(0, -1));
      } finally {
        setActing(false);
      }
    },
    [campaignId, acting, refreshCharacter, refreshNpcs]
  );

  const handleRest = useCallback(
    async (type: "short" | "long") => {
      if (acting) return;
      setActing(true);
      try {
        const result = await rest(campaignId, type);
        setEntries((prev) => [
          ...prev,
          {
            type: "dm",
            text:
              type === "short"
                ? `Короткий отдых. Восстановлено ${(result as { hp_restored: number }).hp_restored} HP.`
                : `Долгий отдых. HP полностью восстановлено.`,
          },
        ]);
        await refreshCharacter();
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Rest failed");
      } finally {
        setActing(false);
      }
    },
    [campaignId, acting, refreshCharacter]
  );

  if (loading) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <p className="text-gray-500">Loading adventure...</p>
      </main>
    );
  }

  if (!character) return null;

  const merchants = nearbyNpcs.filter((n) => n.is_merchant);
  const nonMerchants = nearbyNpcs.filter((n) => !n.is_merchant);

  return (
    <main className="flex h-screen">
      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-gray-800 bg-gray-900">
          <div>
            <h1 className="font-bold" style={{ color: "#d4a843" }}>
              {campaign?.name}
            </h1>
            <p className="text-xs text-gray-500">Turn {campaign?.turn_count}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleRest("short")}
              disabled={acting}
              className="text-xs px-3 py-1 bg-gray-800 border border-gray-700 rounded hover:border-gray-600 disabled:opacity-50"
            >
              Short Rest
            </button>
            <button
              onClick={() => handleRest("long")}
              disabled={acting}
              className="text-xs px-3 py-1 bg-gray-800 border border-gray-700 rounded hover:border-gray-600 disabled:opacity-50"
            >
              Long Rest
            </button>
            <button
              onClick={() => router.push("/campaigns")}
              className="text-xs px-3 py-1 bg-gray-800 border border-gray-700 rounded hover:border-gray-600"
            >
              Back
            </button>
          </div>
        </header>

        {/* Nearby NPCs bar */}
        {nearbyNpcs.length > 0 && (
          <div className="flex items-center gap-2 px-6 py-2 border-b border-gray-800 bg-gray-900/50 flex-wrap">
            <span className="text-xs text-gray-500 mr-1">Nearby:</span>
            {merchants.map((m) => (
              <button
                key={m.id}
                onClick={() => setShopNpc(m)}
                className="text-xs px-3 py-1 rounded transition"
                style={{
                  background: "rgba(212, 168, 67, 0.15)",
                  border: "1px solid rgba(212, 168, 67, 0.4)",
                  color: "#d4a843",
                }}
              >
                🛒 {m.name_ru || m.name}
              </button>
            ))}
            {nonMerchants.map((n) => (
              <span
                key={n.id}
                className="text-xs px-3 py-1 bg-gray-800/50 border border-gray-700 text-gray-400 rounded"
              >
                {n.name_ru || n.name}
              </span>
            ))}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="px-6 py-2 bg-red-900/30 text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Narrative log */}
        <NarrativeLog entries={entries} />

        {/* Action input */}
        <ActionInput
          onSubmit={handleAction}
          suggestions={suggestions}
          disabled={acting || !character.is_alive}
        />
      </div>

      {/* Character sidebar */}
      <CharacterSidebar character={character} />

      {/* Shop modal */}
      {shopNpc && (
        <ShopModal
          campaignId={campaignId}
          npcId={shopNpc.id}
          npcName={shopNpc.name_ru || shopNpc.name}
          character={character}
          onClose={() => setShopNpc(null)}
          onUpdate={refreshCharacter}
        />
      )}
    </main>
  );
}
