-- ================================================
-- Realms of Fate — Initial Schema
-- ================================================

-- Helper function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ========================
-- CAMPAIGNS
-- ========================
CREATE TABLE campaigns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  name TEXT NOT NULL,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned')),
  world_seed TEXT,
  world_state JSONB DEFAULT '{"story_summaries": [], "flags": {}, "visited_locations": []}',
  turn_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_campaigns_user ON campaigns(user_id, status);

CREATE TRIGGER campaigns_updated_at
  BEFORE UPDATE ON campaigns
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ========================
-- CHARACTERS
-- ========================
CREATE TABLE characters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  race TEXT NOT NULL,
  class TEXT NOT NULL,
  level INT DEFAULT 1,
  xp INT DEFAULT 0,
  hp INT NOT NULL,
  max_hp INT NOT NULL,
  ac INT NOT NULL,
  str INT NOT NULL,
  dex INT NOT NULL,
  con INT NOT NULL,
  int_ INT NOT NULL,
  wis INT NOT NULL,
  cha INT NOT NULL,
  gold INT DEFAULT 15,
  spell_slots JSONB DEFAULT '{}',
  max_spell_slots JSONB DEFAULT '{}',
  location TEXT DEFAULT 'Unknown',
  region TEXT DEFAULT 'Starting Region',
  conditions JSONB DEFAULT '[]',
  portrait_url TEXT,
  is_alive BOOLEAN DEFAULT true,
  total_kills INT DEFAULT 0,
  total_quests_completed INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_characters_campaign ON characters(campaign_id);

-- ========================
-- EQUIPMENT SLOTS
-- ========================
CREATE TABLE equipment_slots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  character_id UUID REFERENCES characters(id) ON DELETE CASCADE,
  slot TEXT NOT NULL CHECK (slot IN ('head', 'chest', 'legs', 'boots', 'weapon', 'offhand', 'ring_1', 'ring_2', 'amulet')),
  item_id UUID,
  UNIQUE(character_id, slot)
);
CREATE INDEX idx_equipment_character ON equipment_slots(character_id);

-- ========================
-- ITEM TEMPLATES
-- ========================
CREATE TABLE item_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  name_ru TEXT,
  description TEXT,
  description_ru TEXT,
  type TEXT NOT NULL CHECK (type IN ('weapon', 'armor', 'consumable', 'material', 'quest', 'scroll', 'misc')),
  slot TEXT CHECK (slot IN ('head', 'chest', 'legs', 'boots', 'weapon', 'offhand', 'ring_1', 'ring_2', 'amulet', NULL)),
  rarity TEXT DEFAULT 'common' CHECK (rarity IN ('common', 'uncommon', 'rare', 'epic', 'legendary')),
  damage_dice TEXT,
  ac_bonus INT DEFAULT 0,
  stat_bonuses JSONB DEFAULT '{}',
  effects JSONB DEFAULT '[]',
  weight FLOAT DEFAULT 0,
  value INT DEFAULT 0,
  stackable BOOLEAN DEFAULT false,
  max_stack INT DEFAULT 1,
  consumable_effect JSONB,
  image_url TEXT,
  image_prompt TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_items_type ON item_templates(type, rarity);

-- ========================
-- ITEM INSTANCES
-- ========================
CREATE TABLE item_instances (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id UUID REFERENCES item_templates(id),
  character_id UUID REFERENCES characters(id) ON DELETE CASCADE,
  quantity INT DEFAULT 1,
  is_identified BOOLEAN DEFAULT true,
  custom_name TEXT,
  custom_name_ru TEXT,
  enchantments JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_instances_character ON item_instances(character_id);

ALTER TABLE equipment_slots ADD CONSTRAINT fk_equipment_item
  FOREIGN KEY (item_id) REFERENCES item_instances(id) ON DELETE SET NULL;

-- ========================
-- NPCS
-- ========================
CREATE TABLE npcs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  name_ru TEXT,
  title TEXT,
  title_ru TEXT,
  race TEXT,
  location TEXT,
  region TEXT,
  personality TEXT NOT NULL,
  backstory TEXT,
  dialogue_style TEXT,
  reputation INT DEFAULT 0 CHECK (reputation BETWEEN -100 AND 100),
  disposition TEXT DEFAULT 'neutral' CHECK (disposition IN ('hostile', 'unfriendly', 'neutral', 'friendly', 'allied')),
  memories JSONB DEFAULT '[]',
  is_merchant BOOLEAN DEFAULT false,
  shop_inventory JSONB DEFAULT '[]',
  shop_restock_turn INT DEFAULT 0,
  portrait_url TEXT,
  portrait_prompt TEXT,
  is_alive BOOLEAN DEFAULT true,
  faction TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_npcs_campaign_location ON npcs(campaign_id, location);
CREATE INDEX idx_npcs_campaign_faction ON npcs(campaign_id, faction);

-- ========================
-- QUESTS
-- ========================
CREATE TABLE quests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  title_ru TEXT,
  description TEXT NOT NULL,
  description_ru TEXT,
  type TEXT DEFAULT 'side' CHECK (type IN ('main', 'side')),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'failed', 'abandoned')),
  giver_npc_id UUID REFERENCES npcs(id),
  objectives JSONB DEFAULT '[]',
  rewards JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);
CREATE INDEX idx_quests_campaign_status ON quests(campaign_id, status);

-- ========================
-- COMBAT SESSIONS
-- ========================
CREATE TABLE combat_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'victory', 'defeat', 'fled')),
  enemies JSONB NOT NULL,
  turn_order JSONB DEFAULT '[]',
  current_turn INT DEFAULT 0,
  round INT DEFAULT 1,
  log JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_combat_campaign ON combat_sessions(campaign_id, status);

-- ========================
-- COMPANIONS
-- ========================
CREATE TABLE companions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  name_ru TEXT,
  race TEXT,
  class TEXT,
  personality TEXT NOT NULL,
  level INT DEFAULT 1,
  hp INT NOT NULL,
  max_hp INT NOT NULL,
  ac INT NOT NULL,
  stats JSONB NOT NULL,
  equipment JSONB DEFAULT '[]',
  portrait_url TEXT,
  loyalty INT DEFAULT 50 CHECK (loyalty BETWEEN 0 AND 100),
  is_alive BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_companions_campaign ON companions(campaign_id);

-- ========================
-- CHAT HISTORY
-- ========================
CREATE TABLE chat_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
  context TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content TEXT NOT NULL,
  is_archived BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_chat_active ON chat_history(campaign_id, context, is_archived, created_at);

-- ========================
-- GENERATED IMAGES
-- ========================
CREATE TABLE generated_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_hash TEXT UNIQUE NOT NULL,
  prompt TEXT NOT NULL,
  image_url TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('scene', 'portrait', 'item', 'enemy', 'companion')),
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_images_hash ON generated_images(prompt_hash);

-- ========================
-- ROW LEVEL SECURITY
-- ========================
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE npcs ENABLE ROW LEVEL SECURITY;
ALTER TABLE quests ENABLE ROW LEVEL SECURITY;
ALTER TABLE combat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE companions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_images ENABLE ROW LEVEL SECURITY;

-- Users can only access their own campaigns
CREATE POLICY "Users own their campaigns" ON campaigns
  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users access own campaign characters" ON characters
  FOR ALL USING (campaign_id IN (SELECT id FROM campaigns WHERE user_id = auth.uid()));

CREATE POLICY "Users access own campaign npcs" ON npcs
  FOR ALL USING (campaign_id IN (SELECT id FROM campaigns WHERE user_id = auth.uid()));

CREATE POLICY "Users access own campaign quests" ON quests
  FOR ALL USING (campaign_id IN (SELECT id FROM campaigns WHERE user_id = auth.uid()));

CREATE POLICY "Users access own campaign combat" ON combat_sessions
  FOR ALL USING (campaign_id IN (SELECT id FROM campaigns WHERE user_id = auth.uid()));

CREATE POLICY "Users access own campaign companions" ON companions
  FOR ALL USING (campaign_id IN (SELECT id FROM campaigns WHERE user_id = auth.uid()));

CREATE POLICY "Users access own campaign chat" ON chat_history
  FOR ALL USING (campaign_id IN (SELECT id FROM campaigns WHERE user_id = auth.uid()));

CREATE POLICY "Users access own equipment" ON equipment_slots
  FOR ALL USING (character_id IN (
    SELECT c.id FROM characters c
    JOIN campaigns ca ON c.campaign_id = ca.id
    WHERE ca.user_id = auth.uid()
  ));

CREATE POLICY "Users access own items" ON item_instances
  FOR ALL USING (character_id IN (
    SELECT c.id FROM characters c
    JOIN campaigns ca ON c.campaign_id = ca.id
    WHERE ca.user_id = auth.uid()
  ));

-- Shared / read-only tables
CREATE POLICY "Item templates readable by all" ON item_templates
  FOR SELECT USING (true);

CREATE POLICY "Images readable by all" ON generated_images
  FOR SELECT USING (true);
