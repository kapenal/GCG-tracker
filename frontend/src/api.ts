const API_BASE = import.meta.env.VITE_API_URL ?? '';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type CardSet = {
  id: number;
  slug: string;
  label: string;
  source_url: string;
  card_count: number | null;
};

export type RarityStat = {
  rarity: string;
  card_count: number;
};

export type Card = {
  id: number;
  external_id: string;
  card_number: string | null;
  rarity: string | null;
  name: string;
  name_ko: string | null;
  price_yen: number | null;
  image_url: string | null;
  detail_url: string | null;
  set_slug: string;
  set_label: string;
  stock: string | null;
  price_updated_at: string | null;
  week_change_percent: number | null;
  week_change_direction: 'up' | 'down' | 'flat' | null;
};

export type PriceChange = {
  card_id: number;
  card_number: string | null;
  rarity: string | null;
  name: string;
  name_ko: string | null;
  image_url: string | null;
  set_slug: string;
  previous_price: number;
  current_price: number;
  delta: number;
};

export type PricePoint = {
  recorded_at: string;
  price_yen: number;
  stock: string | null;
};

export type ChangesResponse = {
  from_snapshot_at: string | null;
  to_snapshot_at: string | null;
  changes: PriceChange[];
};

export type SyncResult = {
  snapshot_id: number;
  fetched_at: string;
  total_cards: number;
  sets: { slug: string; label: string; count: number; error?: string }[];
};

export type HealthResponse = {
  status: string;
  last_sync_at: string | null;
  sync_in_progress: boolean;
  today_snapshot_exists: boolean;
};

export const RARITY_ORDER = [
  'LR++',
  'LR+',
  'LR',
  'R+',
  'R',
  'U+',
  'U',
  'C++',
  'C+',
  'C',
  'SP',
  'P',
] as const;

export function raritySortKey(rarity: string | null): number {
  if (!rarity) return RARITY_ORDER.length;
  const i = RARITY_ORDER.indexOf(rarity as (typeof RARITY_ORDER)[number]);
  return i >= 0 ? i : RARITY_ORDER.length;
}

export const api = {
  sets: () => request<CardSet[]>('/api/sets'),
  rarities: (set?: string) => {
    const qs = set ? `?set=${encodeURIComponent(set)}` : '';
    return request<RarityStat[]>(`/api/rarities${qs}`);
  },
  rarityOrder: () => request<string[]>('/api/rarities/order'),
  cards: (params?: { set?: string; rarity?: string; q?: string }) => {
    const qs = new URLSearchParams();
    if (params?.set) qs.set('set', params.set);
    if (params?.rarity) qs.set('rarity', params.rarity);
    if (params?.q) qs.set('q', params.q);
    const query = qs.toString();
    return request<Card[]>(`/api/cards${query ? `?${query}` : ''}`);
  },
  cardHistory: (cardId: number, days = 7) =>
    request<PricePoint[]>(`/api/cards/${cardId}/history?days=${days}`),
  changes: () => request<ChangesResponse>('/api/cards/changes'),
  health: () => request<HealthResponse>('/api/health'),
  sync: () => request<SyncResult>('/api/sync', { method: 'POST' }),
};
