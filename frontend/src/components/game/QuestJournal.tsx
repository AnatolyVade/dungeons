"use client";

import { useState, useEffect } from "react";
import { getQuests, type Quest } from "@/lib/api";

interface Props {
  campaignId: string;
  onClose: () => void;
}

export default function QuestJournal({ campaignId, onClose }: Props) {
  const [quests, setQuests] = useState<Quest[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"active" | "completed">("active");

  useEffect(() => {
    getQuests(campaignId)
      .then(setQuests)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [campaignId]);

  const activeQuests = quests.filter((q) => q.status === "active");
  const completedQuests = quests.filter((q) => q.status === "completed");
  const displayQuests = tab === "active" ? activeQuests : completedQuests;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
          <h2 className="text-lg font-bold text-[var(--color-gold)]">Quest Journal</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xl">&times;</button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-800">
          {(["active", "completed"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2 text-sm font-medium transition ${
                tab === t
                  ? "text-[var(--color-gold)] border-b-2 border-[var(--color-gold)]"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {t === "active" ? `Active (${activeQuests.length})` : `Completed (${completedQuests.length})`}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <p className="text-gray-500 text-center py-8">Loading...</p>
          ) : displayQuests.length === 0 ? (
            <p className="text-gray-600 text-sm text-center py-8">
              {tab === "active" ? "No active quests" : "No completed quests"}
            </p>
          ) : (
            <div className="space-y-4">
              {displayQuests.map((quest) => (
                <QuestCard key={quest.id} quest={quest} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function QuestCard({ quest }: { quest: Quest }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      {/* Title */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-bold text-[var(--color-gold)]">
          {quest.title_ru || quest.title}
        </h3>
        <span
          className={`text-xs px-2 py-0.5 rounded shrink-0 ${
            quest.type === "main"
              ? "bg-yellow-900/50 text-yellow-300"
              : "bg-gray-700 text-gray-400"
          }`}
        >
          {quest.type === "main" ? "Main" : "Side"}
        </span>
      </div>

      {/* Description */}
      {(quest.description_ru || quest.description) && (
        <p className="text-sm text-gray-400 mt-2">
          {quest.description_ru || quest.description}
        </p>
      )}

      {/* Objectives */}
      {quest.objectives && quest.objectives.length > 0 && (
        <div className="mt-3 space-y-1.5">
          {quest.objectives.map((obj, i) => (
            <div key={i} className="flex items-start gap-2 text-sm">
              <span className={`mt-0.5 ${obj.completed ? "text-green-400" : "text-gray-600"}`}>
                {obj.completed ? "✓" : "○"}
              </span>
              <span className={obj.completed ? "text-gray-500 line-through" : "text-gray-300"}>
                {obj.text}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Rewards */}
      {quest.rewards && (quest.rewards.xp || quest.rewards.gold) && (
        <div className="mt-3 flex items-center gap-3 text-xs">
          <span className="text-gray-500">Rewards:</span>
          {quest.rewards.xp && (
            <span className="text-purple-400">{quest.rewards.xp} XP</span>
          )}
          {quest.rewards.gold && (
            <span className="text-[var(--color-gold)]">{quest.rewards.gold} Gold</span>
          )}
        </div>
      )}

      {/* Completion date */}
      {quest.completed_at && (
        <p className="text-xs text-gray-600 mt-2">
          Completed: {new Date(quest.completed_at).toLocaleDateString()}
        </p>
      )}
    </div>
  );
}
