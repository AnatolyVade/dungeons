"use client";

import { useState, useRef, useEffect } from "react";

interface Props {
  onSubmit: (action: string) => void;
  suggestions: string[];
  disabled: boolean;
}

export default function ActionInput({ onSubmit, suggestions, disabled }: Props) {
  const [input, setInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!disabled) inputRef.current?.focus();
  }, [disabled]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSubmit(input.trim());
    setInput("");
  }

  return (
    <div className="border-t border-gray-800 bg-gray-900 px-4 py-3">
      {/* Suggestion buttons */}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSubmit(s)}
              disabled={disabled}
              className="text-xs px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-full hover:border-[var(--color-gold)] hover:text-[var(--color-gold)] transition disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={disabled}
          placeholder={disabled ? "Waiting for DM..." : "What do you do?"}
          className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:outline-none focus:border-[var(--color-gold)] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="px-6 py-2 bg-[var(--color-gold)] text-gray-950 font-semibold rounded-lg hover:brightness-110 transition disabled:opacity-50"
        >
          Act
        </button>
      </form>
    </div>
  );
}
