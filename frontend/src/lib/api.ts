const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8019";

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
