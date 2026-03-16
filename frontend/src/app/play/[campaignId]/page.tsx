"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getCampaign,
  getCharacter,
  sendAction,
  rest,
  getNearbyNpcs,
  getChatHistory,
  getCombatStatus,
  isLoggedIn,
  type Character,
  type CampaignFull,
  type NPC,
  type CombatStatus,
  type CombatActionResponse,
} from "@/lib/api";
import CharacterSidebar from "@/components/game/CharacterSidebar";
import NarrativeLog, { type LogEntry } from "@/components/game/NarrativeLog";
import ActionInput from "@/components/game/ActionInput";
import ShopModal from "@/components/game/ShopModal";
import NpcModal from "@/components/game/NpcModal";
import InventoryModal from "@/components/game/InventoryModal";
import QuestJournal from "@/components/game/QuestJournal";
import CombatPanel from "@/components/game/CombatPanel";

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
  const [chatNpc, setChatNpc] = useState<NPC | null>(null);

  // Modals
  const [showInventory, setShowInventory] = useState(false);
  const [showQuests, setShowQuests] = useState(false);

  // Combat
  const [combat, setCombat] = useState<CombatStatus | null>(null);

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

  const checkCombat = useCallback(async () => {
    try {
      const status = await getCombatStatus(campaignId);
      setCombat(status);
    } catch {
      setCombat(null);
    }
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

        // Check for active combat
        await checkCombat();

        // Load chat history
        try {
          const history = await getChatHistory(campaignId);
          const restored: LogEntry[] = [];
          for (const msg of history) {
            if (msg.role === "user") {
              restored.push({ type: "player", text: msg.content });
            } else {
              restored.push({ type: "dm", text: msg.content });
            }
          }
          if (restored.length > 0) {
            setEntries(restored);
          }
        } catch {
          // silently fail — not critical
        }

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
  }, [campaignId, router, refreshNpcs, checkCombat]);

  const handleAction = useCallback(
    async (action: string) => {
      if (acting) return;
      setActing(true);
      setError("");

      // Add player entry
      setEntries((prev) => [...prev, { type: "player", text: action }]);

      try {
        const response = await sendAction(campaignId, action);

        // Check if combat started
        if (response.combat_status === "started" || response.combat_status === "ongoing") {
          await checkCombat();
        }

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
    [campaignId, acting, refreshCharacter, refreshNpcs, checkCombat]
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

  const handleCombatUpdate = useCallback(
    async (response: CombatActionResponse) => {
      setEntries((prev) => [
        ...prev,
        { type: "dm", text: response.narrative },
      ]);
      await refreshCharacter();
    },
    [refreshCharacter]
  );

  const handleCombatEnd = useCallback(
    async (status: string) => {
      setCombat(null);
      await refreshCharacter();
      await refreshNpcs();
      if (status === "victory") {
        setSuggestions([
          "Осмотреть тела врагов",
          "Осмотреться вокруг",
          "Отдохнуть",
        ]);
      } else if (status === "fled") {
        setSuggestions([
          "Бежать дальше",
          "Осмотреться вокруг",
          "Спрятаться",
        ]);
      }
    },
    [refreshCharacter, refreshNpcs]
  );

  if (loading) {
    return (
      <main className="flex items-center justify-center min-h-screen">
        <p className="text-gray-500">Loading adventure...</p>
      </main>
    );
  }

  if (!character) return null;

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
              onClick={() => setShowQuests(true)}
              className="text-xs px-3 py-1 bg-gray-800 border border-gray-700 rounded hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition disabled:opacity-50"
            >
              Quests
            </button>
            <button
              onClick={() => setShowInventory(true)}
              className="text-xs px-3 py-1 bg-gray-800 border border-gray-700 rounded hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition disabled:opacity-50"
            >
              Inventory
            </button>
            <button
              onClick={() => handleRest("short")}
              disabled={acting || !!combat}
              className="text-xs px-3 py-1 bg-gray-800 border border-gray-700 rounded hover:border-gray-600 disabled:opacity-50"
            >
              Short Rest
            </button>
            <button
              onClick={() => handleRest("long")}
              disabled={acting || !!combat}
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
            {nearbyNpcs.map((n) => (
              <button
                key={n.id}
                onClick={() => setChatNpc(n)}
                className="flex items-center gap-1.5 text-xs px-3 py-1 rounded transition hover:brightness-110"
                style={
                  n.is_merchant
                    ? {
                        background: "rgba(212, 168, 67, 0.15)",
                        border: "1px solid rgba(212, 168, 67, 0.4)",
                        color: "#d4a843",
                      }
                    : {
                        background: "rgba(55, 65, 81, 0.5)",
                        border: "1px solid rgba(75, 85, 99, 1)",
                        color: "#9ca3af",
                      }
                }
              >
                {n.portrait_url ? (
                  <img
                    src={n.portrait_url}
                    alt=""
                    className="w-5 h-5 rounded-full object-cover"
                  />
                ) : null}
                {n.is_merchant ? "🛒 " : ""}
                {n.name_ru || n.name}
              </button>
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

        {/* Combat panel or Action input */}
        {combat ? (
          <CombatPanel
            campaignId={campaignId}
            enemies={combat.enemies}
            round={combat.round}
            knownSpells={character.known_spells}
            spellSlots={character.spell_slots}
            onCombatUpdate={handleCombatUpdate}
            onCombatEnd={handleCombatEnd}
          />
        ) : (
          <ActionInput
            onSubmit={handleAction}
            suggestions={suggestions}
            disabled={acting || !character.is_alive}
          />
        )}
      </div>

      {/* Character sidebar */}
      <CharacterSidebar character={character} />

      {/* NPC conversation modal */}
      {chatNpc && (
        <NpcModal
          campaignId={campaignId}
          npc={chatNpc}
          onClose={() => setChatNpc(null)}
          onOpenShop={() => {
            setShopNpc(chatNpc);
            setChatNpc(null);
          }}
        />
      )}

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

      {/* Inventory modal */}
      {showInventory && (
        <InventoryModal
          campaignId={campaignId}
          character={character}
          onClose={() => setShowInventory(false)}
          onUpdate={refreshCharacter}
        />
      )}

      {/* Quest journal */}
      {showQuests && (
        <QuestJournal
          campaignId={campaignId}
          onClose={() => setShowQuests(false)}
        />
      )}
    </main>
  );
}
