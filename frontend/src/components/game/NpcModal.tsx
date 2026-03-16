"use client";

import { useState, useEffect, useCallback } from "react";
import {
  chatWithNpc,
  getNpcPortrait,
  type NPC,
} from "@/lib/api";

const DISPOSITION_COLORS: Record<string, string> = {
  friendly: "text-green-400",
  neutral: "text-gray-400",
  unfriendly: "text-orange-400",
  hostile: "text-red-400",
};

const DISPOSITION_LABELS: Record<string, string> = {
  friendly: "Дружелюбный",
  neutral: "Нейтральный",
  unfriendly: "Недружелюбный",
  hostile: "Враждебный",
};

interface Props {
  campaignId: string;
  npc: NPC;
  onClose: () => void;
  onOpenShop: () => void;
}

export default function NpcModal({
  campaignId,
  npc,
  onClose,
  onOpenShop,
}: Props) {
  const [portraitUrl, setPortraitUrl] = useState<string | null>(npc.portrait_url);
  const [chatLog, setChatLog] = useState<{ role: string; text: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reputation, setReputation] = useState(npc.reputation || 0);
  const [disposition, setDisposition] = useState(npc.disposition);

  // Load portrait if not available
  useEffect(() => {
    if (!portraitUrl) {
      getNpcPortrait(campaignId, npc.id)
        .then((r) => setPortraitUrl(r.portrait_url))
        .catch(() => {});
    }
  }, [campaignId, npc.id, portraitUrl]);

  const handleSend = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!input.trim() || loading) return;
      const msg = input.trim();
      setInput("");
      setLoading(true);
      setError("");

      setChatLog((prev) => [...prev, { role: "player", text: msg }]);

      try {
        const result = await chatWithNpc(campaignId, npc.id, msg);
        setChatLog((prev) => [
          ...prev,
          { role: "npc", text: result.dialogue },
        ]);
        // Show quest notification if offered
        if (result.quest_offered && typeof result.quest_offered === "object") {
          const q = result.quest_offered as { title_ru?: string; title?: string };
          setChatLog((prev) => [
            ...prev,
            { role: "system", text: `📜 Новый квест: ${q.title_ru || q.title || "Unknown"}` },
          ]);
        }
        // Show ability learned notification
        if (result.taught && typeof result.taught === "object") {
          const t = result.taught as { name_ru?: string; name?: string; gold_cost?: number };
          const costText = t.gold_cost ? ` (-${t.gold_cost} золота)` : "";
          setChatLog((prev) => [
            ...prev,
            { role: "system", text: `✨ Изучено: ${t.name_ru || t.name || "Новый навык"}${costText}` },
          ]);
        }
        setReputation(result.new_reputation);
        // Update disposition based on reputation
        if (result.new_reputation > 50) setDisposition("friendly");
        else if (result.new_reputation > -30) setDisposition("neutral");
        else if (result.new_reputation > -60) setDisposition("unfriendly");
        else setDisposition("hostile");
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed");
      } finally {
        setLoading(false);
      }
    },
    [campaignId, npc.id, input, loading]
  );

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        {/* Header with portrait */}
        <div className="flex items-start gap-4 px-5 py-4 border-b border-gray-800">
          {/* Portrait */}
          <div className="shrink-0 w-20 h-20 rounded-lg overflow-hidden bg-gray-800 border border-gray-700">
            {portraitUrl ? (
              <img
                src={portraitUrl}
                alt={npc.name_ru || npc.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-3xl text-gray-600">
                👤
              </div>
            )}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold" style={{ color: "#d4a843" }}>
              {npc.name_ru || npc.name}
            </h2>
            <div className="flex items-center gap-3 mt-1 text-xs">
              <span className="text-gray-500">{npc.race || "Unknown"}</span>
              <span className={DISPOSITION_COLORS[disposition] || "text-gray-400"}>
                {DISPOSITION_LABELS[disposition] || disposition}
              </span>
              <span className="text-gray-600">
                Rep: {reputation}
              </span>
              {npc.is_merchant && (
                <button
                  onClick={() => {
                    onClose();
                    onOpenShop();
                  }}
                  className="px-2 py-0.5 rounded text-xs"
                  style={{
                    background: "rgba(212, 168, 67, 0.15)",
                    border: "1px solid rgba(212, 168, 67, 0.4)",
                    color: "#d4a843",
                  }}
                >
                  🛒 Shop
                </button>
              )}
            </div>
            {npc.personality && (
              <p className="text-xs text-gray-600 mt-1 truncate">
                {npc.personality}
              </p>
            )}
          </div>

          {/* Close */}
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-xl shrink-0"
          >
            &times;
          </button>
        </div>

        {/* Error */}
        {error && (
          <p className="px-5 py-2 text-red-400 text-sm">{error}</p>
        )}

        {/* Chat log */}
        <div className="flex-1 overflow-y-auto p-5 space-y-3">
          {chatLog.length === 0 && (
            <p className="text-gray-600 text-sm text-center py-8">
              Start a conversation...
            </p>
          )}
          {chatLog.map((entry, i) => (
            <div
              key={i}
              className={
                entry.role === "player"
                  ? "ml-8 bg-gray-800/50 rounded-lg p-3 border-l-2 border-blue-500"
                  : entry.role === "system"
                  ? "mx-4 bg-yellow-900/20 rounded-lg p-3 border-l-2 border-yellow-600 text-center"
                  : "mr-8 bg-gray-800 rounded-lg p-3 border-l-2"
              }
              style={
                entry.role === "npc"
                  ? { borderLeftColor: "#d4a843" }
                  : undefined
              }
            >
              <p className={`text-sm ${entry.role === "system" ? "text-yellow-300 font-medium" : ""}`}>{entry.text}</p>
            </div>
          ))}
        </div>

        {/* Input */}
        <form onSubmit={handleSend} className="flex gap-2 px-5 py-3 border-t border-gray-800">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Say something..."
            className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-amber-700 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2 font-semibold rounded-lg text-sm transition disabled:opacity-50 cursor-pointer"
            style={{
              background: "linear-gradient(135deg, #d4a843 0%, #b8912e 100%)",
              color: "#0a0a0f",
            }}
          >
            {loading ? "..." : "Say"}
          </button>
        </form>
      </div>
    </div>
  );
}
