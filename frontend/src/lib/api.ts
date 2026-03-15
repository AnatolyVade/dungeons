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
  equipment?: unknown[];
  inventory?: unknown[];
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
}
