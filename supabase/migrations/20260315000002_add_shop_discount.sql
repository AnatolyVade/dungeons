-- Add shop_discount column to NPCs for haggling system
ALTER TABLE npcs ADD COLUMN IF NOT EXISTS shop_discount INT DEFAULT 0;
