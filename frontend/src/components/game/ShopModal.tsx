"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getShop,
  buyItem,
  sellItem,
  haggle,
  getCharacter,
  type ShopItem,
  type ShopResponse,
  type Character,
} from "@/lib/api";

type Tab = "buy" | "sell" | "haggle";

const RARITY_COLORS: Record<string, string> = {
  common: "text-gray-400",
  uncommon: "text-green-400",
  rare: "text-blue-400",
  epic: "text-purple-400",
  legendary: "text-yellow-400",
};

interface Props {
  campaignId: string;
  npcId: string;
  npcName: string;
  character: Character;
  onClose: () => void;
  onUpdate: () => void;
}

export default function ShopModal({
  campaignId,
  npcId,
  npcName,
  character,
  onClose,
  onUpdate,
}: Props) {
  const [tab, setTab] = useState<Tab>("buy");
  const [shop, setShop] = useState<ShopResponse | null>(null);
  const [inventory, setInventory] = useState<Character | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Haggle state
  const [haggleInput, setHaggleInput] = useState("");
  const [haggleLog, setHaggleLog] = useState<{ role: string; text: string }[]>(
    []
  );

  const loadShop = useCallback(async () => {
    try {
      const [shopData, charData] = await Promise.all([
        getShop(campaignId, npcId),
        getCharacter(campaignId),
      ]);
      setShop(shopData);
      setInventory(charData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load shop");
    } finally {
      setLoading(false);
    }
  }, [campaignId, npcId]);

  useEffect(() => {
    loadShop();
  }, [loadShop]);

  async function handleBuy(item: ShopItem) {
    setActionLoading(true);
    setError("");
    setSuccess("");
    try {
      const result = await buyItem(
        campaignId,
        npcId,
        item.item_template_id,
        1,
        shop?.discount || 0
      );
      setSuccess(
        `Bought ${result.item_name} for ${result.gold_spent}g`
      );
      await loadShop();
      onUpdate();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Purchase failed");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSell(itemInstanceId: string) {
    setActionLoading(true);
    setError("");
    setSuccess("");
    try {
      const result = await sellItem(campaignId, npcId, itemInstanceId);
      setSuccess(`Sold for ${result.gold_earned}g`);
      await loadShop();
      onUpdate();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sale failed");
    } finally {
      setActionLoading(false);
    }
  }

  async function handleHaggle(e: React.FormEvent) {
    e.preventDefault();
    if (!haggleInput.trim() || actionLoading) return;
    const msg = haggleInput.trim();
    setHaggleInput("");
    setActionLoading(true);
    setError("");

    setHaggleLog((prev) => [...prev, { role: "player", text: msg }]);

    try {
      const result = await haggle(campaignId, npcId, msg);
      setHaggleLog((prev) => [
        ...prev,
        { role: "npc", text: result.dialogue },
      ]);
      if (result.discount > 0) {
        setSuccess(`Discount: ${result.discount}%!`);
        // Refresh shop to show new prices
        const shopData = await getShop(campaignId, npcId);
        setShop(shopData);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Haggle failed");
    } finally {
      setActionLoading(false);
    }
  }

  const gold = inventory?.gold ?? character.gold;

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
          <div>
            <h2 className="text-lg font-bold text-[var(--color-gold)]">
              {npcName}
            </h2>
            <p className="text-xs text-gray-500">
              Gold: <span className="text-[var(--color-gold)]">{gold}</span>
              {shop && shop.discount > 0 && (
                <span className="ml-2 text-green-400">
                  -{shop.discount}% discount
                </span>
              )}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 text-xl"
          >
            &times;
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-800">
          {(["buy", "sell", "haggle"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => {
                setTab(t);
                setError("");
                setSuccess("");
              }}
              className={`flex-1 py-2 text-sm font-medium transition ${
                tab === t
                  ? "text-[var(--color-gold)] border-b-2 border-[var(--color-gold)]"
                  : "text-gray-500 hover:text-gray-300"
              }`}
            >
              {t === "buy" ? "Buy" : t === "sell" ? "Sell" : "Haggle"}
            </button>
          ))}
        </div>

        {/* Messages */}
        {error && (
          <p className="px-5 py-2 text-red-400 text-sm">{error}</p>
        )}
        {success && (
          <p className="px-5 py-2 text-green-400 text-sm">{success}</p>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <p className="text-gray-500 text-center py-8">Loading...</p>
          ) : tab === "buy" ? (
            <BuyTab
              items={shop?.items || []}
              gold={gold}
              onBuy={handleBuy}
              disabled={actionLoading}
            />
          ) : tab === "sell" ? (
            <SellTab
              inventory={inventory?.inventory || []}
              sellMultiplier={shop?.sell_multiplier || 0.5}
              onSell={handleSell}
              disabled={actionLoading}
            />
          ) : (
            <HaggleTab
              log={haggleLog}
              input={haggleInput}
              onInputChange={setHaggleInput}
              onSubmit={handleHaggle}
              disabled={actionLoading}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ── Buy Tab ──
function BuyTab({
  items,
  gold,
  onBuy,
  disabled,
}: {
  items: ShopItem[];
  gold: number;
  onBuy: (item: ShopItem) => void;
  disabled: boolean;
}) {
  if (items.length === 0) {
    return <p className="text-gray-500 text-center py-8">Shop is empty</p>;
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div
          key={item.item_template_id}
          className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3"
        >
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-medium">
                {item.name_ru || item.name}
              </span>
              <span
                className={`text-xs ${RARITY_COLORS[item.rarity] || "text-gray-400"}`}
              >
                [{item.rarity}]
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-0.5">
              {item.type}
              {item.damage_dice && ` | ${item.damage_dice}`}
              {item.ac_bonus > 0 && ` | +${item.ac_bonus} AC`}
              {item.description_ru && ` | ${item.description_ru}`}
            </div>
          </div>
          <div className="flex items-center gap-3 ml-4">
            <span className="text-xs text-gray-500">x{item.quantity}</span>
            <div className="text-right">
              {item.effective_price < item.base_price ? (
                <>
                  <span className="text-xs text-gray-600 line-through">
                    {item.base_price}g
                  </span>{" "}
                  <span className="text-[var(--color-gold)] font-medium">
                    {item.effective_price}g
                  </span>
                </>
              ) : (
                <span className="text-[var(--color-gold)] font-medium">
                  {item.effective_price}g
                </span>
              )}
            </div>
            <button
              onClick={() => onBuy(item)}
              disabled={disabled || gold < item.effective_price}
              className="px-3 py-1 text-xs bg-[var(--color-gold)] text-gray-950 font-semibold rounded hover:brightness-110 transition disabled:opacity-40"
            >
              Buy
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Sell Tab ──
function SellTab({
  inventory,
  sellMultiplier,
  onSell,
  disabled,
}: {
  inventory: unknown[];
  sellMultiplier: number;
  onSell: (id: string) => void;
  disabled: boolean;
}) {
  const items = inventory as {
    id: string;
    quantity: number;
    custom_name: string | null;
    custom_name_ru: string | null;
    item_templates: {
      name: string;
      name_ru: string | null;
      type: string;
      rarity: string;
      value: number;
      description_ru: string | null;
    };
  }[];

  if (!items || items.length === 0) {
    return (
      <p className="text-gray-500 text-center py-8">
        No items to sell
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item) => {
        const tmpl = item.item_templates;
        if (!tmpl) return null;
        const sellPrice = Math.max(1, Math.floor(tmpl.value * sellMultiplier));
        return (
          <div
            key={item.id}
            className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium">
                  {item.custom_name_ru || tmpl.name_ru || tmpl.name}
                </span>
                <span
                  className={`text-xs ${RARITY_COLORS[tmpl.rarity] || "text-gray-400"}`}
                >
                  [{tmpl.rarity}]
                </span>
              </div>
              <div className="text-xs text-gray-500">
                {tmpl.type} &middot; x{item.quantity}
              </div>
            </div>
            <div className="flex items-center gap-3 ml-4">
              <span className="text-[var(--color-gold)]">{sellPrice}g</span>
              <button
                onClick={() => onSell(item.id)}
                disabled={disabled}
                className="px-3 py-1 text-xs bg-gray-700 text-gray-200 font-semibold rounded hover:bg-gray-600 transition disabled:opacity-40"
              >
                Sell
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Haggle Tab ──
function HaggleTab({
  log,
  input,
  onInputChange,
  onSubmit,
  disabled,
}: {
  log: { role: string; text: string }[];
  input: string;
  onInputChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex flex-col h-full min-h-[300px]">
      <div className="flex-1 overflow-y-auto space-y-3 mb-4">
        {log.length === 0 && (
          <p className="text-gray-600 text-sm text-center py-8">
            Try to convince the merchant to lower prices...
          </p>
        )}
        {log.map((entry, i) => (
          <div
            key={i}
            className={
              entry.role === "player"
                ? "ml-8 bg-gray-800/50 rounded-lg p-3 border-l-2 border-blue-500"
                : "mr-8 bg-gray-800 rounded-lg p-3 border-l-2 border-[var(--color-gold)]"
            }
          >
            <p className="text-sm">{entry.text}</p>
          </div>
        ))}
      </div>
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => onInputChange(e.target.value)}
          disabled={disabled}
          placeholder="Try persuading..."
          className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-[var(--color-gold)] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="px-4 py-2 bg-[var(--color-gold)] text-gray-950 font-semibold rounded-lg text-sm hover:brightness-110 transition disabled:opacity-50"
        >
          Say
        </button>
      </form>
    </div>
  );
}
