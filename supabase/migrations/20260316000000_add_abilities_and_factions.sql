-- Universal ability/knowledge store for character learning
CREATE TABLE IF NOT EXISTS character_abilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    category TEXT NOT NULL CHECK (category IN (
        'proficiency', 'language', 'recipe', 'technique',
        'lore', 'feat', 'spell', 'misc'
    )),
    name TEXT NOT NULL,
    name_ru TEXT NOT NULL,
    description_ru TEXT,
    source TEXT,
    data JSONB DEFAULT '{}',
    level INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(character_id, category, name)
);
CREATE INDEX IF NOT EXISTS idx_abilities_char ON character_abilities(character_id);

-- Faction reputation tracking
CREATE TABLE IF NOT EXISTS faction_reputation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    faction TEXT NOT NULL,
    reputation INT DEFAULT 0 CHECK (reputation BETWEEN -100 AND 100),
    UNIQUE(campaign_id, faction)
);

-- Merchant restock interval
ALTER TABLE npcs ADD COLUMN IF NOT EXISTS shop_restock_interval INT DEFAULT 50;
