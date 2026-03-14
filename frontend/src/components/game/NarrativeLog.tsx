"use client";

import { useEffect, useRef } from "react";
import type { DMResponse } from "@/lib/api";

interface LogEntry {
  type: "player" | "dm";
  text: string;
  diceRolls?: DMResponse["dice_rolls"];
  imageUrl?: string | null;
}

export default function NarrativeLog({ entries }: { entries: LogEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
      {entries.length === 0 && (
        <p className="text-gray-600 text-center py-12">
          Your adventure awaits. Type an action to begin...
        </p>
      )}

      {entries.map((entry, i) => (
        <div
          key={i}
          className={`narrative-fade-in ${
            entry.type === "player"
              ? "ml-12 bg-gray-800/50 rounded-lg p-3 border-l-2 border-blue-500"
              : "mr-4"
          }`}
        >
          {entry.type === "player" ? (
            <p className="text-blue-300 text-sm">{entry.text}</p>
          ) : (
            <>
              {entry.imageUrl && (
                <img
                  src={entry.imageUrl}
                  alt="Scene"
                  className="w-full max-w-md rounded-lg mb-3 border border-gray-700"
                />
              )}
              <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">
                {entry.text}
              </p>
              {entry.diceRolls && entry.diceRolls.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {entry.diceRolls.map((roll, j) => (
                    <span
                      key={j}
                      className={`text-xs px-2 py-1 rounded ${
                        roll.value === 20
                          ? "bg-green-900/50 text-green-300"
                          : roll.value === 1
                            ? "bg-red-900/50 text-red-300"
                            : "bg-gray-800 text-gray-400"
                      }`}
                    >
                      {roll.type}: {roll.value} ({roll.reason})
                    </span>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

export type { LogEntry };
