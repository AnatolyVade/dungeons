"use client";

import { useState, useCallback } from "react";
import {
  equipItem,
  unequipItem,
  dropItem,
  type Character,
  type EquipmentSlot,
  type InventoryItem,
} from "@/lib/api";

const RARITY_COLORS: Record<string, string> = {
  common: "text-gray-400",
  uncommon: "text-green-400",
  rare: "text-blue-400",
  epic: "text-purple-400",
  legendary: "text-yellow-400",
};

const SLOT_LABELS: Record<string, string> = {
  head: "Head",
  chest: "Chest",
  legs: "Legs",
  boots: "Boots",
  weapon: "Weapon",
  offhand: "Off-hand",
  ring_1: "Ring 1",
  ring_2: "Ring 2",
  amulet: "Amulet",
};

const SLOT_ORDER = ["weapon", "offhand", "head", "chest", "legs", "boots", "ring_1", "ring_2", "amulet"];

interface Props {
  campaignId: string;
  character: Character;
  onClose: () => void;
  onUpdate: () => void;
}

export default function InventoryModal({ campaignId, character, onClose, onUpdate }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const equipment = (character.equipment || []) as EquipmentSlot[];
  const inventory = (character.inventory || []) as InventoryItem[];

  // Get equipped item IDs to filter them out of bag
  const equippedIds = new Set(
    equipment.filter((e) => e.item_instances?.id).map((e) => e.item_instances!.id)
  );
  const bagItems = inventory.filter((i) => !equippedIds.has(i.id));

  // Sort equipment by slot order
  const sortedEquipment = [...equipment].sort(
    (a, b) => SLOT_ORDER.indexOf(a.slot) - SLOT_ORDER.indexOf(b.slot)
  );

  const handleEquip = useCallback(
    async (itemInstanceId: string, slot: string) => {
      setLoading(true);
      setError("");
      setSuccess("");
      try {
        const result = await equipItem(campaignId, itemInstanceId, slot);
        setSuccess(`Equipped ${result.item_name}`);
        onUpdate();
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Equip failed");
      } finally {
        setLoading(false);
      }
    },
    [campaignId, onUpdate]
  );

  const handleUnequip = useCallback(
    async (slot: string) => {
      setLoading(true);
      setError("");
      setSuccess("");
      try {
        await unequipItem(campaignId, slot);
        setSuccess("Unequipped");
        onUpdate();
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Unequip failed");
      } finally {
        setLoading(false);
      }
    },
    [campaignId, onUpdate]
  );

  const handleDrop = useCallback(
    async (itemInstanceId: string) => {
      setLoading(true);
      setError("");
      setSuccess("");
      try {
        await dropItem(campaignId, itemInstanceId);
        setSuccess("Dropped");
        onUpdate();
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Drop failed");
      } finally {
        setLoading(false);
      }
    },
    [campaignId, onUpdate]
  );

  // Determine which slot an inventory item can go in
  function getItemSlot(item: InventoryItem): string | null {
    const tmpl = item.item_templates;
    if (!tmpl) return null;
    if (tmpl.type === "weapon") return "weapon";
    if (tmpl.type === "armor") {
      // Try to infer from name or just default to chest
      return "chest";
    }
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-gray-800">
          <h2 className="text-lg font-bold text-[var(--color-gold)]">Inventory</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-xl">&times;</button>
        </div>

        {/* Messages */}
        {error && <p className="px-5 py-2 text-red-400 text-sm">{error}</p>}
        {success && <p className="px-5 py-2 text-green-400 text-sm">{success}</p>}

        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Equipment Slots */}
          <div>
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Equipment</h3>
            <div className="grid grid-cols-1 gap-2">
              {sortedEquipment.map((slot) => {
                const inst = slot.item_instances;
                const tmpl = inst?.item_templates;
                const hasItem = !!inst && !!tmpl;

                return (
                  <div
                    key={slot.slot}
                    className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2.5"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <span className="text-xs text-gray-500 w-16 shrink-0">
                        {SLOT_LABELS[slot.slot] || slot.slot}
                      </span>
                      {hasItem ? (
                        <div className="min-w-0">
                          <span className="font-medium text-sm">
                            {inst!.custom_name || tmpl!.name_ru || tmpl!.name}
                          </span>
                          <span className={`text-xs ml-2 ${RARITY_COLORS[tmpl!.rarity] || "text-gray-400"}`}>
                            [{tmpl!.rarity}]
                          </span>
                          {tmpl!.damage_dice && (
                            <span className="text-xs text-gray-500 ml-2">{tmpl!.damage_dice}</span>
                          )}
                          {tmpl!.ac_bonus > 0 && (
                            <span className="text-xs text-gray-500 ml-2">+{tmpl!.ac_bonus} AC</span>
                          )}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-600 italic">Empty</span>
                      )}
                    </div>
                    {hasItem && (
                      <button
                        onClick={() => handleUnequip(slot.slot)}
                        disabled={loading}
                        className="text-xs px-2 py-1 bg-gray-700 text-gray-300 rounded hover:bg-gray-600 transition disabled:opacity-40 shrink-0"
                      >
                        Unequip
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Bag */}
          <div>
            <h3 className="text-sm font-semibold text-gray-400 mb-3">Bag</h3>
            {bagItems.length === 0 ? (
              <p className="text-gray-600 text-sm text-center py-4">Empty</p>
            ) : (
              <div className="space-y-2">
                {bagItems.map((item) => {
                  const tmpl = item.item_templates;
                  if (!tmpl) return null;
                  const equipSlot = getItemSlot(item);

                  return (
                    <div
                      key={item.id}
                      className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2.5"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">
                            {item.custom_name_ru || item.custom_name || tmpl.name_ru || tmpl.name}
                          </span>
                          <span className={`text-xs ${RARITY_COLORS[tmpl.rarity] || "text-gray-400"}`}>
                            [{tmpl.rarity}]
                          </span>
                        </div>
                        <div className="text-xs text-gray-500">
                          {tmpl.type} &middot; x{item.quantity}
                          {tmpl.value > 0 && <span className="ml-2 text-[var(--color-gold)]">{tmpl.value}g</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {equipSlot && (
                          <button
                            onClick={() => handleEquip(item.id, equipSlot)}
                            disabled={loading}
                            className="text-xs px-2 py-1 bg-[var(--color-gold)] text-gray-950 font-semibold rounded hover:brightness-110 transition disabled:opacity-40"
                          >
                            Equip
                          </button>
                        )}
                        <button
                          onClick={() => handleDrop(item.id)}
                          disabled={loading}
                          className="text-xs px-2 py-1 bg-red-900/50 text-red-300 rounded hover:bg-red-900/70 transition disabled:opacity-40"
                        >
                          Drop
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
