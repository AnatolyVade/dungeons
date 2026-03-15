-- Locations table: stores discovered locations with images and metadata
CREATE TABLE IF NOT EXISTS locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    region TEXT DEFAULT 'Unknown',
    description TEXT,
    description_ru TEXT,
    image_url TEXT,
    image_prompt TEXT,
    location_type TEXT DEFAULT 'general', -- town, tavern, dungeon, wilderness, shop, etc.
    discovered_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(campaign_id, name)
);

CREATE INDEX IF NOT EXISTS idx_locations_campaign ON locations(campaign_id);
CREATE INDEX IF NOT EXISTS idx_locations_name ON locations(campaign_id, name);

ALTER TABLE locations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own campaign locations" ON locations
    FOR ALL USING (
        campaign_id IN (SELECT id FROM campaigns WHERE user_id = auth.uid())
    );
