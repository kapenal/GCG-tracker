export const STALE_SETS = 10 * 60 * 1000;
export const STALE_RARITIES = 10 * 60 * 1000;
export const STALE_CARDS = 5 * 60 * 1000;

export const queryKeys = {
  sets: ['sets'] as const,
  rarities: (set?: string) => ['rarities', set ?? ''] as const,
  cards: (filters: { set?: string; rarity?: string; q?: string }) =>
    ['cards', filters.set ?? '', filters.rarity ?? '', filters.q ?? ''] as const,
  changes: ['changes'] as const,
  cardHistory: (cardId: number, days: number) =>
    ['cardHistory', cardId, days] as const,
};
