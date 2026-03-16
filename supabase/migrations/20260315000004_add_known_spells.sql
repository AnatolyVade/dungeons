-- Add known_spells column to characters table for spell system
ALTER TABLE characters ADD COLUMN known_spells JSONB DEFAULT '[]';
