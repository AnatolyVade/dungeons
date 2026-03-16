const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

async function getToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }

  return res.json();
}

// ── Auth ──
export async function register(email: string, password: string) {
  const data = await apiFetch<{ access_token: string; user_id: string }>(
    "/api/auth/register",
    { method: "POST", body: JSON.stringify({ email, password }) }
  );
  localStorage.setItem("access_token", data.access_token);
  return data;
}

export async function login(email: string, password: string) {
  const data = await apiFetch<{ access_token: string; user_id: string }>(
    "/api/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) }
  );
  localStorage.setItem("access_token", data.access_token);
  return data;
}

export function logout() {
  localStorage.removeItem("access_token");
}

export function isLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}

// ── Campaigns ──
export async function getCampaigns() {
  return apiFetch<Campaign[]>("/api/campaigns");
}

export async function createCampaign(name: string) {
  return apiFetch<Campaign>("/api/campaigns", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function getCampaign(id: string) {
  return apiFetch<CampaignFull>(`/api/campaigns/${id}`);
}

// ── Character ──
export async function rollStats(campaignId: string) {
  return apiFetch<{ rolls: number[][]; totals: number[] }>(
    `/api/campaigns/${campaignId}/character/roll-stats`,
    { method: "POST" }
  );
}

export async function createCharacter(
  campaignId: string,
  data: CharacterCreateData
) {
  return apiFetch(`/api/campaigns/${campaignId}/character`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getCharacter(campaignId: string) {
  return apiFetch<Character>(`/api/campaigns/${campaignId}/character`);
}

// ── Game Actions ──
export async function sendAction(campaignId: string, action: string) {
  return apiFetch<DMResponse>(`/api/campaigns/${campaignId}/action`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

export async function rest(campaignId: string, type: "short" | "long") {
  return apiFetch(`/api/campaigns/${campaignId}/action/rest`, {
    method: "POST",
    body: JSON.stringify({ type }),
  });
}

// ── Chat History ──
export async function getChatHistory(campaignId: string) {
  return apiFetch<{ role: string; content: string; created_at: string }[]>(
    `/api/campaigns/${campaignId}/chat-history`
  );
}

// ── Shop ──
export async function getShop(campaignId: string, npcId: string) {
  return apiFetch<ShopResponse>(`/api/campaigns/${campaignId}/npcs/${npcId}/shop`);
}

export async function buyItem(
  campaignId: string,
  npcId: string,
  itemTemplateId: string,
  quantity = 1,
  haggleDiscount = 0
) {
  return apiFetch<BuyResponse>(
    `/api/campaigns/${campaignId}/npcs/${npcId}/shop/buy`,
    {
      method: "POST",
      body: JSON.stringify({
        item_template_id: itemTemplateId,
        quantity,
        haggle_discount: haggleDiscount,
      }),
    }
  );
}

export async function sellItem(
  campaignId: string,
  npcId: string,
  itemInstanceId: string,
  quantity = 1
) {
  return apiFetch<SellResponse>(
    `/api/campaigns/${campaignId}/npcs/${npcId}/shop/sell`,
    {
      method: "POST",
      body: JSON.stringify({ item_instance_id: itemInstanceId, quantity }),
    }
  );
}

export async function haggle(campaignId: string, npcId: string, message: string) {
  return apiFetch<HaggleResponse>(
    `/api/campaigns/${campaignId}/npcs/${npcId}/shop/haggle`,
    { method: "POST", body: JSON.stringify({ message }) }
  );
}

// ── NPCs ──
export async function getNearbyNpcs(campaignId: string) {
  return apiFetch<NPC[]>(`/api/campaigns/${campaignId}/npcs`);
}

export async function chatWithNpc(campaignId: string, npcId: string, message: string) {
  return apiFetch<NpcChatResponse>(
    `/api/campaigns/${campaignId}/npcs/${npcId}/chat`,
    { method: "POST", body: JSON.stringify({ message }) }
  );
}

export async function getNpcPortrait(campaignId: string, npcId: string) {
  return apiFetch<{ portrait_url: string | null }>(
    `/api/campaigns/${campaignId}/npcs/${npcId}/portrait`
  );
}

// ── Inventory ──
export async function equipItem(campaignId: string, itemInstanceId: string, slot: string) {
  return apiFetch<{ success: boolean; slot: string; item_name: string }>(
    `/api/campaigns/${campaignId}/inventory/equip`,
    { method: "POST", body: JSON.stringify({ item_instance_id: itemInstanceId, slot }) }
  );
}

export async function unequipItem(campaignId: string, slot: string) {
  return apiFetch<{ success: boolean; slot: string }>(
    `/api/campaigns/${campaignId}/inventory/unequip`,
    { method: "POST", body: JSON.stringify({ slot }) }
  );
}

export async function dropItem(campaignId: string, itemInstanceId: string) {
  return apiFetch<{ success: boolean }>(
    `/api/campaigns/${campaignId}/inventory/drop`,
    { method: "POST", body: JSON.stringify({ item_instance_id: itemInstanceId }) }
  );
}

// ── Combat ──
export async function getCombatStatus(campaignId: string) {
  return apiFetch<CombatStatus | null>(`/api/campaigns/${campaignId}/combat/status`);
}

export async function combatAction(campaignId: string, action: string, details = "") {
  return apiFetch<CombatActionResponse>(
    `/api/campaigns/${campaignId}/combat/action`,
    { method: "POST", body: JSON.stringify({ action, details }) }
  );
}

// ── Quests ──
export async function getQuests(campaignId: string) {
  return apiFetch<Quest[]>(`/api/campaigns/${campaignId}/quests`);
}

// ── Types ──
export interface Campaign {
  id: string;
  name: string;
  status: string;
  turn_count: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignFull extends Campaign {
  character: Character | null;
  world_state: Record<string, unknown>;
}

export interface ItemTemplate {
  name: string;
  name_ru: string | null;
  type: string;
  rarity: string;
  value?: number;
  damage_dice: string | null;
  ac_bonus: number;
  stat_bonuses?: Record<string, number>;
  description_ru?: string | null;
  slot?: string | null;
}

export interface EquipmentSlot {
  slot: string;
  item_id: string | null;
  item_instances: {
    id: string;
    quantity: number;
    custom_name: string | null;
    item_templates: ItemTemplate;
  } | null;
}

export interface InventoryItem {
  id: string;
  quantity: number;
  custom_name: string | null;
  custom_name_ru: string | null;
  is_identified: boolean;
  item_templates: {
    name: string;
    name_ru: string | null;
    type: string;
    rarity: string;
    value: number;
    description_ru: string | null;
  };
}

export interface Character {
  id: string;
  name: string;
  race: string;
  class: string;
  level: number;
  xp: number;
  hp: number;
  max_hp: number;
  ac: number;
  str: number;
  dex: number;
  con: number;
  int_: number;
  wis: number;
  cha: number;
  gold: number;
  location: string;
  region: string;
  conditions: string[];
  portrait_url: string | null;
  is_alive: boolean;
  spell_slots?: Record<string, number>;
  max_spell_slots?: Record<string, number>;
  known_spells?: string[];
  equipment?: EquipmentSlot[];
  inventory?: InventoryItem[];
}

export interface CharacterCreateData {
  name: string;
  race: string;
  class: string;
  stats: {
    str: number;
    dex: number;
    con: number;
    int: number;
    wis: number;
    cha: number;
  };
}

export interface DiceRoll {
  type: string;
  value: number;
  reason: string;
}

export interface DMResponse {
  narrative: string;
  dice_rolls: DiceRoll[];
  hp_change: number;
  xp_gain: number;
  gold_change: number;
  items_gained: Record<string, unknown>[];
  items_lost: string[];
  location: string | null;
  region: string | null;
  new_npcs: Record<string, unknown>[];
  combat_status: string;
  enemies: unknown;
  suggestions: string[];
  scene_image_url: string | null;
  conditions_gained?: string[];
  conditions_lost?: string[];
  quest_update?: { title: string; objective_completed: string } | null;
}

export interface ShopItem {
  item_template_id: string;
  name: string;
  name_ru: string | null;
  type: string;
  rarity: string;
  description_ru: string | null;
  base_price: number;
  effective_price: number;
  quantity: number;
  damage_dice: string | null;
  ac_bonus: number;
}

export interface ShopResponse {
  items: ShopItem[];
  merchant_name: string;
  merchant_name_ru: string | null;
  discount: number;
  sell_multiplier: number;
}

export interface BuyResponse {
  success: boolean;
  gold_spent: number;
  new_gold: number;
  item_name: string;
}

export interface SellResponse {
  success: boolean;
  gold_earned: number;
  new_gold: number;
}

export interface HaggleResponse {
  dialogue: string;
  discount: number;
  reputation_change: number;
  new_reputation: number;
}

export interface NPC {
  id: string;
  name: string;
  name_ru: string | null;
  disposition: string;
  is_merchant: boolean;
  location: string;
  portrait_url: string | null;
  personality: string | null;
  race: string | null;
  reputation: number;
}

export interface NpcChatResponse {
  dialogue: string;
  reputation_change: number;
  new_reputation: number;
  quest_offered: QuestOffered | null;
}

export interface QuestOffered {
  title: string;
  title_ru?: string;
  description?: string;
  description_ru?: string;
  objectives?: { text: string; completed: boolean }[];
  rewards?: { xp?: number; gold?: number };
}

export interface CombatStatus {
  id: string;
  enemies: CombatEnemy[];
  round: number;
  log: unknown[];
  status: string;
}

export interface CombatEnemy {
  name: string;
  hp: number;
  max_hp: number;
  ac: number;
  attack_dice?: string;
  attack_stat?: number;
  xp_value?: number;
}

export interface CombatActionResponse {
  narrative: string;
  combat_status: string;
  player_action: Record<string, unknown> | null;
  enemy_actions: Record<string, unknown>[];
  enemies: CombatEnemy[];
  round: number;
  character_hp: number;
  xp_gain: number;
  gold_change: number;
  items_gained: Record<string, unknown>[];
}

export interface Quest {
  id: string;
  title: string;
  title_ru: string | null;
  description: string | null;
  description_ru: string | null;
  type: string;
  status: string;
  objectives: { text: string; completed: boolean }[];
  rewards: { xp?: number; gold?: number };
  giver_npc_id: string | null;
  created_at: string;
  completed_at: string | null;
}
