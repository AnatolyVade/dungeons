# Realms of Fate — Full-Stack AI D&D Game
## Project Blueprint v2

---

## CLAUDE CODE SETUP INSTRUCTIONS

**This section is for Claude Code to follow when scaffolding the project.**

### Supabase Database Setup

Claude Code should set up the database using the Supabase CLI. Do NOT ask the developer to paste SQL manually.

**Step 1: Install and link Supabase CLI**
```bash
# If not installed
npm install -g supabase

# Login (developer needs to provide their access token)
supabase login

# Link to existing project (developer provides project ref + db password)
supabase link --project-ref <PROJECT_REF>
```

**Step 2: Create migration files**
Generate migration files in `supabase/migrations/` with timestamps:
```bash
supabase migration new create_initial_schema
```
Then write ALL the SQL from the "Database Schema" section below into that migration file.

**Step 3: Push to Supabase**
```bash
supabase db push
```
This applies all migrations to the remote Supabase database.

**Step 4: Generate types (for TypeScript frontend)**
```bash
supabase gen types typescript --linked > src/types/database.ts
```

**Alternative if Supabase CLI is not available:**
Use the Supabase Management API directly:
```python
import httpx

SUPABASE_URL = "https://<project_ref>.supabase.co"
SUPABASE_SERVICE_KEY = "<service_role_key>"  # from project settings

async def run_sql(sql: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/rpc/exec_sql",
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                "Content-Type": "application/json"
            },
            json={"query": sql}
        )
        return resp.json()
```

Or use `psycopg2` / `asyncpg` to connect directly to the Supabase PostgreSQL connection string (found in Project Settings > Database > Connection string).

**Claude Code: when you create the project, scaffold it in this order:**
1. Initialize Next.js app + FastAPI backend in a monorepo
2. Set up Supabase CLI and create + push all migrations
3. Generate TypeScript types from the schema
4. Set up environment variables (.env) for all API keys
5. Build Phase 1 features (auth, character creation, basic DM loop)
6. Then proceed phase by phase as listed in Implementation Phases

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND                  │
│  Character Creation │ Game UI │ Inventory │          │
│  Combat UI │ NPC Chat │ Quest Journal │ Shop         │
└────────────────────────┬────────────────────────────┘
                         │ REST + SSE (streaming)
┌────────────────────────▼────────────────────────────┐
│                   FASTAPI BACKEND                    │
│                                                      │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐            │
│  │ Game     │ │ AI       │ │ Combat    │            │
│  │ Engine   │ │ Manager  │ │ Engine    │            │
│  └──────────┘ └──────────┘ └───────────┘            │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐            │
│  │ Inventory│ │ NPC      │ │ Image     │            │
│  │ System   │ │ Memory   │ │ Generator │            │
│  └──────────┘ └──────────┘ └───────────┘            │
│  ┌──────────────────────────────────┐                │
│  │ Context Manager (Tiered Memory) │                │
│  └──────────────────────────────────┘                │
└───┬──────────────┬──────────────┬───────────────────┘
    │              │              │
┌───▼───┐    ┌────▼────┐   ┌────▼─────┐
│Supa-  │    │ Claude  │   │ DALL-E   │
│base   │    │ API     │   │ API      │
│(PgSQL)│    │         │   │          │
└───────┘    └─────────┘   └──────────┘
```

---

## Game Design: Open World, Endless

**There are NO floors, NO linear dungeon, NO win screen.** This is an open-world fantasy sandbox.

The player creates a character and enters a persistent world. The AI DM generates towns, dungeons, wilderness, NPCs, and quests organically. The player goes wherever they want, does whatever they want. Campaigns can last 10 turns or 10,000 turns.

Progression comes from:
- Leveling up (XP from combat, quests, roleplay)
- Better gear (loot drops, shops, crafting)
- Quest chains that emerge from NPC interactions
- Reputation across factions and regions
- Companions recruited along the way
- The unfolding narrative itself

There is no "game over" screen unless the character dies (permadeath optional). Players can run multiple campaigns with different characters.

---

## Tech Stack

| Layer      | Tech                    | Purpose                              |
|------------|-------------------------|--------------------------------------|
| Frontend   | Next.js 14+ (App Router)| SSR, client components, UI           |
| Backend    | FastAPI                 | Game logic, AI orchestration, combat |
| Database   | Supabase (PostgreSQL)   | Persistence, auth, real-time         |
| AI / DM    | Claude API (Sonnet)     | Narration, NPC dialogue, quests      |
| Image Gen  | DALL-E 3 API            | Scenes, portraits, items, enemies    |
| Cache      | Redis                   | Session state, rate limiting, images  |
| Storage    | Supabase Storage / S3   | Generated images, assets             |
| Auth       | Supabase Auth           | JWT, OAuth, session management       |

### Why NOT Mem0 / Vector DBs

This game does NOT need Mem0, Pinecone, or any vector database. Those solve semantic search across unstructured conversations (good for AI assistants like Sypher). This game has fully structured state — every piece of context is keyed to a campaign ID, stored in PostgreSQL, and loaded deterministically.

The database IS the memory. The tiered context manager (see below) handles what gets loaded into each AI prompt. No embeddings, no vector search, no extra dependencies.

---

## Tiered Memory / Context Management

The game can run for thousands of turns. Raw chat history would blow the context window and cost a fortune. This tiered system keeps context lean forever.

### Tier 1 — Always in Context (every AI call)
Loaded from DB every turn. ~1500 tokens.

- Character stats, HP, AC, level, conditions
- Equipped items + full inventory
- Active spell slots
- Current location name + description
- Active combat state (if any)
- Active companions + their stats/HP
- Last 6-8 chat exchanges (sliding window from chat_history table)

### Tier 2 — Loaded When Relevant
Only injected when the context calls for it. ~1000 tokens.

- **Nearby NPCs only** — NPCs in the player's current location get loaded with personality + memories. NPCs in other locations are NOT in context.
- **Active quest objectives** — just the objective text, not completed quests.
- **World state flags** — JSONB key-value pairs like `{"dragon_awakened": true, "bridge_destroyed": true}`. Compact and deterministic.
- **Location history** — one-liner: "Visited: Blackwood Village, The Sunken Mines, Fort Draven"

### Tier 3 — Background Summarization (the key piece)
Runs async every 20 turns. ~500 tokens in context.

Every 20 turns, a background task calls Claude to compress the last 20 turns of raw history into 2-3 sentences. These summaries accumulate as a "story so far" field. When they stack past 10 entries, the oldest 5 get mega-compressed into one paragraph.

This means the AI always has a coherent narrative of what happened, without the raw history bloating the context.

```python
# Context budget target per DM call: ~6000 tokens total
CONTEXT_BUDGET = {
    "dm_instructions":    700,   # rules, format, personality
    "character_sheet":    400,   # stats, equipment, conditions
    "active_quests":      300,   # 3-5 active quest objectives
    "companions":         300,   # 2 companions max
    "nearby_npcs":        400,   # NPCs in current location only
    "world_state_flags":  200,   # key flags only
    "story_summary":      500,   # rolling summary of past events
    "recent_history":    1200,   # last 6-8 exchanges
    # ────────────────────────
    # System prompt: ~4000 tokens
    # Recent chat:   ~2000 tokens
    # Total:         ~6000 tokens per call (stays flat forever)
}
```

### Summarizer Implementation

```python
async def maybe_summarize(campaign_id: str):
    """Called after every turn. Summarizes every 20 turns."""
    campaign = await get_campaign(campaign_id)
    if campaign.turn_count % 20 != 0 or campaign.turn_count == 0:
        return

    # Get last 20 exchanges
    recent = await get_chat_history(campaign_id, context="dm", limit=40)

    summary_text = await call_claude(
        system="Compress this D&D gameplay into 2-3 sentences. Focus on: key decisions, NPCs met, enemies defeated, items found, locations visited, quest progress. Be concise. Write in Russian.",
        messages=[{"role": "user", "content": format_history(recent)}]
    )

    # Append to rolling summaries in world_state
    summaries = campaign.world_state.get("story_summaries", [])
    summaries.append({
        "turns": f"{campaign.turn_count - 20}-{campaign.turn_count}",
        "text": summary_text
    })

    # If > 10 summaries, compress oldest 5 into 1
    if len(summaries) > 10:
        oldest_text = " ".join([s["text"] for s in summaries[:5]])
        mega = await call_claude(
            system="Compress this story recap into 2 sentences. Keep only the most important events. Russian.",
            messages=[{"role": "user", "content": oldest_text}]
        )
        summaries = [{"turns": summaries[0]["turns"] + "-" + summaries[4]["turns"], "text": mega}] + summaries[5:]

    campaign.world_state["story_summaries"] = summaries
    await update_campaign(campaign)

    # Archive old chat history (keep last 20 exchanges live, rest is archived)
    await archive_old_chat_history(campaign_id, keep_recent=40)
```

### How It Feels to the AI

Recent events: vivid, detailed (raw chat history).
Older events: clear but compressed ("You saved Blackwood Village from bandits and befriended the blacksmith Goran").
Ancient events: just key facts ("Early in your journey you cleared the Sunken Mines and earned the trust of the Miners' Guild").

Like human memory. The AI never notices. The context never grows past ~6k tokens.

---

## Database Schema

**Claude Code: put ALL of the following SQL into a single migration file.**

### campaigns
```sql
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
```

### characters
```sql
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
```

### equipment_slots
```sql
CREATE TABLE equipment_slots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  character_id UUID REFERENCES characters(id) ON DELETE CASCADE,
  slot TEXT NOT NULL CHECK (slot IN ('head', 'chest', 'legs', 'boots', 'weapon', 'offhand', 'ring_1', 'ring_2', 'amulet')),
  item_id UUID,
  UNIQUE(character_id, slot)
);
CREATE INDEX idx_equipment_character ON equipment_slots(character_id);
```

### item_templates
```sql
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
```

### item_instances
```sql
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
ALTER TABLE equipment_slots ADD CONSTRAINT fk_equipment_item FOREIGN KEY (item_id) REFERENCES item_instances(id) ON DELETE SET NULL;
```

### npcs
```sql
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
```

### quests
```sql
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
```

### combat_sessions
```sql
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
```

### companions
```sql
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
```

### chat_history
```sql
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
```

### generated_images
```sql
CREATE TABLE generated_images (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  prompt_hash TEXT UNIQUE NOT NULL,
  prompt TEXT NOT NULL,
  image_url TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('scene', 'portrait', 'item', 'enemy', 'companion')),
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_images_hash ON generated_images(prompt_hash);
```

### RLS Policies
```sql
-- Enable RLS on all tables
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE characters ENABLE ROW LEVEL SECURITY;
ALTER TABLE equipment_slots ENABLE ROW LEVEL SECURITY;
ALTER TABLE item_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE npcs ENABLE ROW LEVEL SECURITY;
ALTER TABLE quests ENABLE ROW LEVEL SECURITY;
ALTER TABLE combat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE companions ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;

-- Users can only access their own campaigns and related data
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

-- item_templates and generated_images are shared / read-only for users
ALTER TABLE item_templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Item templates readable by all" ON item_templates FOR SELECT USING (true);

ALTER TABLE generated_images ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Images readable by all" ON generated_images FOR SELECT USING (true);
```

### Helper function for updated_at
```sql
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER campaigns_updated_at
  BEFORE UPDATE ON campaigns
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
```

---

## API Routes

### Auth
```
POST   /api/auth/register
POST   /api/auth/login
GET    /api/auth/me
```

### Campaigns
```
POST   /api/campaigns                    -- new campaign
GET    /api/campaigns                    -- list user campaigns
GET    /api/campaigns/:id                -- full campaign state
DELETE /api/campaigns/:id                -- abandon
```

### Character
```
POST   /api/campaigns/:id/character      -- create character
GET    /api/campaigns/:id/character      -- get character + stats + equipment
POST   /api/campaigns/:id/character/roll-stats  -- roll 4d6 drop lowest x6
```

### Game Actions (the core loop)
```
POST   /api/campaigns/:id/action         -- free text action -> DM response
  Body: { "action": "I sneak past the guards" }
  Response: {
    "narrative": "...",
    "dice_rolls": [...],
    "state_changes": {...},
    "suggestions": [...],
    "scene_image_url": "...",
    "combat": null | {...}
  }

POST   /api/campaigns/:id/action/use-item
  Body: { "item_id": "uuid", "target": "self" | "enemy" | "npc_name" }

POST   /api/campaigns/:id/action/rest
  Body: { "type": "short" | "long" }
```

### Combat
```
POST   /api/campaigns/:id/combat/action
  Body: { "action": "attack" | "spell" | "item" | "flee" | "custom", "details": "..." }
```

### NPCs
```
GET    /api/campaigns/:id/npcs
GET    /api/campaigns/:id/npcs/:npc_id
POST   /api/campaigns/:id/npcs/:npc_id/talk
  Body: { "message": "Do you know anything about the cave?" }
```

### Shop
```
GET    /api/campaigns/:id/npcs/:npc_id/shop
POST   /api/campaigns/:id/npcs/:npc_id/shop/buy
  Body: { "item_template_id": "uuid", "quantity": 1 }
POST   /api/campaigns/:id/npcs/:npc_id/shop/sell
  Body: { "item_instance_id": "uuid", "quantity": 1 }
POST   /api/campaigns/:id/npcs/:npc_id/shop/haggle
  Body: { "message": "Come on, that's too expensive..." }
```

### Inventory
```
GET    /api/campaigns/:id/inventory
POST   /api/campaigns/:id/inventory/equip
  Body: { "item_id": "uuid", "slot": "weapon" }
POST   /api/campaigns/:id/inventory/unequip
  Body: { "slot": "weapon" }
POST   /api/campaigns/:id/inventory/drop
  Body: { "item_id": "uuid" }
```

### Quests
```
GET    /api/campaigns/:id/quests
GET    /api/campaigns/:id/quests/:quest_id
```

### Companions
```
GET    /api/campaigns/:id/companions
POST   /api/campaigns/:id/companions/:id/command
  Body: { "command": "Protect me" | "Attack the goblin" | "Stay here" }
```

### Images
```
POST   /api/images/generate
  Body: { "prompt": "...", "type": "scene" | "portrait" | "item" | "enemy" }
  (checks generated_images cache by prompt_hash first)
```

---

## AI Orchestration

### DM Context Builder

Every action builds the prompt from the tiered memory system:

```python
async def build_dm_context(campaign, character):
    # ── TIER 1: Always loaded ──
    char_block = format_character_sheet(character)    # stats, HP, equipment
    equipment = await get_equipped_items(character.id)
    inventory = await get_inventory(character.id)
    companions = await get_alive_companions(campaign.id)
    active_combat = await get_active_combat(campaign.id)

    # Recent chat (sliding window)
    recent_chat = await get_chat_history(
        campaign.id, context="dm", is_archived=False, limit=16  # last 8 exchanges
    )

    # ── TIER 2: Contextual ──
    nearby_npcs = await get_npcs_at_location(campaign.id, character.location)
    active_quests = await get_quests(campaign.id, status="active")
    flags = campaign.world_state.get("flags", {})
    visited = campaign.world_state.get("visited_locations", [])

    # ── TIER 3: Summaries ──
    story_summaries = campaign.world_state.get("story_summaries", [])
    story_so_far = "\n".join([s["text"] for s in story_summaries]) if story_summaries else "The adventure has just begun."

    context = f"""You are a D&D 5e Dungeon Master running an open-world fantasy campaign.
ALL narration, dialogue, item names, location names, NPC speech in Russian.
JSON keys stay in English. suggested_actions in Russian.

=== CHARACTER ===
{char_block}
Equipment: {format_equipment(equipment)}
Inventory: {format_inventory(inventory)}

=== COMPANIONS ===
{format_companions(companions)}

=== STORY SO FAR ===
{story_so_far}

=== ACTIVE QUESTS ===
{format_quests(active_quests)}

=== CURRENT LOCATION ===
{character.location} (Region: {character.region})
Nearby NPCs: {format_nearby_npcs(nearby_npcs)}

=== WORLD STATE ===
Flags: {json.dumps(flags)}
Visited: {", ".join(visited[-20:])}
Turn: {campaign.turn_count}

{"=== ACTIVE COMBAT ===" + format_combat(active_combat) if active_combat else ""}

=== RESPONSE FORMAT ===
Respond with valid JSON only. No markdown. No backticks.
{{
  "narrative": "2-5 vivid sentences in Russian",
  "dice_rolls": [{{"type": "d20", "value": <random 1-20>, "reason": "reason"}}],
  "hp_change": 0,
  "xp_gain": 0,
  "gold_change": 0,
  "items_gained": [],
  "items_lost": [],
  "location": "Current Location",
  "region": "Current Region",
  "new_npcs": [],
  "combat_status": "none|started|ongoing|victory|defeat",
  "enemies": "",
  "suggestions": ["Action 1", "Action 2", "Action 3"]
}}

=== DM RULES ===
- Open world. No linear path. Player goes wherever they want.
- Generate towns, dungeons, wilderness, NPCs organically.
- Dice rolls determine success. Use character stat modifiers.
- Combat is dangerous. Enemies attack back. Track HP.
- HP 0 = death. Make it dramatic.
- Reward XP (25-100 for encounters, 10-25 for roleplay).
- Drop loot from enemies. Vary rarity.
- NPCs have distinct personalities. Let player converse freely.
- Consequences matter. The world remembers.
- Create quest hooks from NPC interactions naturally.
- Vary encounters: combat, puzzles, traps, social, exploration.
- Reference the story so far for continuity.
"""
    return context, recent_chat
```

### NPC Context Builder
```python
async def build_npc_context(npc, character, campaign):
    return f"""You are {npc.name}, {npc.title or ""}.
Race: {npc.race} | Location: {npc.location}
Personality: {npc.personality}
Backstory: {npc.backstory}
Dialogue style: {npc.dialogue_style}
Disposition: {npc.disposition} (reputation: {npc.reputation})

Memories of this player:
{json.dumps(npc.memories[-10:])}

Speaking with: {character.name}, Level {character.level} {character.race} {character.class}

Respond in Russian. Stay in character. 2-4 sentences.
{"You are a merchant. Discuss prices when asked. Your inventory: " + json.dumps(npc.shop_inventory) if npc.is_merchant else ""}
{"Be hostile and unhelpful." if npc.reputation < -30 else ""}
{"Be generous. Share secrets and tips." if npc.reputation > 50 else ""}

Respond as JSON:
{{"dialogue": "...", "reputation_change": 0, "new_memory": null or "short description",
  "quest_offered": null or {{"title": "...", "description": "...", "objectives": [...], "rewards": {{...}}}},
  "shop_discount": 0}}"""
```

### Image Prompt Builder
```python
STYLE_PREFIX = "Dark fantasy oil painting, dramatic lighting, D&D art style, detailed, atmospheric"

def build_scene_prompt(location, description, mood="dark"):
    return f"{STYLE_PREFIX}, {description}, {location}, {mood} mood, no text, no words"

def build_portrait_prompt(name, race, char_class, appearance):
    return f"{STYLE_PREFIX}, portrait of a {race} {char_class}, {appearance}, bust shot, no text"

def build_enemy_prompt(enemy_name, description):
    return f"{STYLE_PREFIX}, {enemy_name}, {description}, menacing, battle-ready, no text"

def build_item_prompt(item_name, description, rarity):
    glow = "magical glow, enchanted" if rarity in ("rare", "epic", "legendary") else ""
    return f"{STYLE_PREFIX}, {item_name}, {description}, {glow}, item art, dark background, no text"
```

### Image Caching
```python
import hashlib

async def get_or_generate_image(prompt: str, img_type: str) -> str:
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

    # Check DB cache
    cached = await db.generated_images.select().eq("prompt_hash", prompt_hash).maybe_single()
    if cached:
        return cached["image_url"]

    # Generate via DALL-E
    response = await openai_client.images.generate(
        model="dall-e-3", prompt=prompt,
        size="1024x1024", quality="standard", n=1
    )

    # Upload to Supabase Storage
    image_data = await download_image(response.data[0].url)
    path = f"{img_type}/{prompt_hash}.png"
    await supabase.storage.from_("game-images").upload(path, image_data)
    image_url = supabase.storage.from_("game-images").get_public_url(path)

    # Cache in DB
    await db.generated_images.insert({
        "prompt_hash": prompt_hash, "prompt": prompt,
        "image_url": image_url, "type": img_type
    })
    return image_url
```

---

## Combat Engine (Server-Side)

All dice rolls happen server-side. No client-side cheating.

```python
import random
import re

def roll_dice(dice_str: str) -> tuple[int, list[int]]:
    """Parse '2d6+3' -> (total, individual_rolls)"""
    match = re.match(r"(\d+)d(\d+)([+-]\d+)?", dice_str)
    if not match:
        return 0, []
    count, sides, bonus = int(match[1]), int(match[2]), int(match[3] or 0)
    rolls = [random.randint(1, sides) for _ in range(count)]
    return sum(rolls) + bonus, rolls

def calc_mod(stat: int) -> int:
    return (stat - 10) // 2

def attack_roll(attacker_stat: int, target_ac: int) -> dict:
    d20 = random.randint(1, 20)
    mod = calc_mod(attacker_stat)
    total = d20 + mod
    return {
        "hit": d20 == 20 or (d20 != 1 and total >= target_ac),
        "roll": d20, "total": total, "modifier": mod,
        "is_crit": d20 == 20, "is_fumble": d20 == 1,
    }

def saving_throw(stat_value: int, dc: int) -> dict:
    d20 = random.randint(1, 20)
    total = d20 + calc_mod(stat_value)
    return {"success": total >= dc, "roll": d20, "total": total}

class CombatManager:
    async def player_attack(self, character, target_enemy, weapon):
        stat = character.str if weapon["type"] == "melee" else character.dex
        result = attack_roll(stat, target_enemy["ac"])
        damage = 0
        if result["is_fumble"]:
            hint = "fumble"
        elif result["hit"]:
            dmg, rolls = roll_dice(weapon["damage_dice"])
            if result["is_crit"]:
                crit_dmg, _ = roll_dice(weapon["damage_dice"])
                dmg += crit_dmg
                hint = "critical_hit"
            else:
                hint = "hit"
            damage = max(1, dmg + calc_mod(stat))
        else:
            hint = "miss"
        target_enemy["hp"] = max(0, target_enemy["hp"] - damage)
        return {"result": result, "damage": damage, "hint": hint,
                "enemy_hp": target_enemy["hp"], "enemy_dead": target_enemy["hp"] <= 0}

    async def enemy_turn(self, enemy, character):
        result = attack_roll(enemy.get("attack_stat", 14), character.ac)
        damage = 0
        if result["hit"]:
            dmg, _ = roll_dice(enemy["attack_dice"])
            damage = dmg
            character.hp = max(0, character.hp - damage)
        return {"result": result, "damage": damage,
                "player_hp": character.hp, "player_dead": character.hp <= 0}
```

---

## Frontend Pages

```
/                         -- Landing page
/auth/login              -- Login
/auth/register           -- Register
/campaigns               -- Campaign list (continue / new)
/campaigns/new           -- Character creation wizard
/play/:campaign_id       -- Main game screen
  ├── Narrative panel (scrollable, DALL-E images inline)
  ├── Sidebar: character sheet, HP/XP bars, stats
  ├── Inventory panel (equipment slots + bag)
  ├── Quest journal panel
  ├── NPC chat modal (per-NPC conversation)
  ├── Shop modal (buy/sell/haggle)
  ├── Combat overlay (initiative tracker, enemy HP bars)
  └── Input bar + AI suggestion buttons
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Monorepo: Next.js frontend + FastAPI backend
- [ ] Supabase: CLI setup, migrations, push schema
- [ ] Auth flow (register, login, JWT via Supabase Auth)
- [ ] Character creation (race, class, server-side stat rolling)
- [ ] Basic DM loop: action -> build context -> Claude -> parse JSON -> update state
- [ ] Tiered context manager (Tier 1 + basic Tier 3 summarizer)
- [ ] Basic UI: narrative log, input bar, character sidebar, suggestion buttons

### Phase 2: Core Mechanics (Week 3-4)
- [ ] Inventory system (item templates, instances, equip/unequip)
- [ ] Equipment slots UI (click-to-equip, stat changes visible)
- [ ] Combat engine (server-side dice, turn order, enemy AI via Claude)
- [ ] Combat UI (initiative bar, enemy cards, HP bars, attack buttons)
- [ ] HP/XP/Gold mutations from AI responses
- [ ] DALL-E integration (scene image on new location, portrait on character create)

### Phase 3: Living World (Week 5-6)
- [ ] NPC system (creation from DM responses, personality, memory)
- [ ] NPC conversation (separate Claude context per NPC, Tier 2 loading)
- [ ] Reputation system (disposition changes behavior)
- [ ] Shop system (buy/sell/haggle via NPC chat)
- [ ] Quest journal (AI-generated from NPC interactions)
- [ ] DALL-E portraits for NPCs and enemies (with caching)
- [ ] Full Tier 3 summarizer with mega-compression

### Phase 4: Companions & Polish (Week 7-8)
- [ ] AI companion system (recruit through roleplay, stats, personality)
- [ ] Companion commands (protect, attack, stay)
- [ ] Companion autonomous combat (Claude picks their actions)
- [ ] Companion loyalty (affected by player decisions)
- [ ] Rest system (short/long rest, random encounter chance)
- [ ] Death handling (permadeath + optional resurrection mechanic)
- [ ] Image caching optimization
- [ ] Mobile responsive UI

### Phase 5: Launch (Week 9-10)
- [ ] Rate limiting (AI calls per user per hour)
- [ ] Error handling, retries, graceful degradation
- [ ] SSE streaming for narration
- [ ] Campaign save/resume reliability testing
- [ ] Landing page + onboarding tutorial
- [ ] Deploy to GCP
- [ ] Beta test

---

## Cost Estimation (per active user)

| Resource           | Cost/call     | Per session (~50 turns) |
|--------------------|--------------|------------------------|
| Claude Sonnet (DM) | ~$0.003      | ~$0.15                 |
| Claude Sonnet (NPC)| ~$0.003      | ~$0.06 (20 chats)     |
| Claude (summarizer)| ~$0.002      | ~$0.005 (2-3 per session)|
| DALL-E 3 Standard  | ~$0.04       | ~$0.40 (10 images)    |
| Supabase (free)    | $0           | $0                     |
| **Total/session**  |              | **~$0.62**             |

Image caching reduces DALL-E costs significantly over time. Returning to a previously visited location = free image.

---

## Key Decisions

1. **DALL-E 3** ($0.04/img) — much better quality than DALL-E 2
2. **Companion limit**: 2 max — keeps context lean
3. **Image triggers**: new locations only + character creation + boss enemies
4. **Russian narration**: all AI output in Russian, UI labels in English
5. **Monetization**: TBD — free tier (text only) + premium (with images)?
6. **Domain**: TBD
