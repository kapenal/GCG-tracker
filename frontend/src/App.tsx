import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  api,
  raritySortKey,
  type Card,
  type PriceChange,
  type PricePoint,
} from './api';
import { CardGridSkeleton, ChangesSkeleton } from './components/CardGridSkeleton';
import './components/CardGridSkeleton.css';
import {
  queryKeys,
  STALE_CARDS,
  STALE_RARITIES,
  STALE_SETS,
} from './queryKeys';
import './App.css';

type Tab = 'cards' | 'changes';
type TrendFilter = 'all' | 'up' | 'down';

const INITIAL_LOAD_START = performance.now();

function formatYen(n: number) {
  return `${n.toLocaleString('ja-JP')}円`;
}

function rarityClass(rarity: string) {
  return `rarity-${rarity.replace(/\+/g, 'p').replace(/[^a-zA-Z0-9]/g, '')}`;
}

function CardTile({ c, onClick }: { c: Card; onClick: (card: Card) => void }) {
  const displayName = c.name_ko ?? c.name;
  const showChangeLabel =
    c.week_change_percent != null && c.week_change_direction && c.week_change_direction !== 'flat';
  const changeSign = (c.week_change_percent ?? 0) > 0 ? '+' : '';
  return (
    <article
      className="card clickable"
      onClick={() => onClick(c)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick(c);
        }
      }}
    >
      <div className="card-image-wrap">
        {c.image_url && <img src={c.image_url} alt={displayName} loading="lazy" />}
        {showChangeLabel && (
          <span
            className={`change-percent-badge ${
              c.week_change_direction === 'down' ? 'down' : 'up'
            }`}
          >
            {changeSign}
            {c.week_change_percent?.toFixed(2)}%
          </span>
        )}
      </div>
      <div className="card-body">
        <div className="card-top-row">
          <span className="card-number">{c.card_number ?? ''}</span>
          {c.rarity && (
            <span className={`rarity-badge ${rarityClass(c.rarity)}`}>{c.rarity}</span>
          )}
        </div>
        <span className="card-name">{displayName}</span>
        <span className="card-set">{c.set_label}</span>
        {c.price_yen != null && (
          <span className="card-price">{formatYen(c.price_yen)}</span>
        )}
        {c.stock && <span className="card-stock">在庫: {c.stock}</span>}
      </div>
    </article>
  );
}

function PriceChart({ points }: { points: PricePoint[] }) {
  const [activeIdx, setActiveIdx] = useState<number | null>(
    points.length > 0 ? points.length - 1 : null
  );
  useEffect(() => {
    setActiveIdx(points.length > 0 ? points.length - 1 : null);
  }, [points]);

  if (points.length === 0) {
    return <p className="empty">최근 7일 수집 데이터가 없습니다.</p>;
  }
  if (points.length === 1) {
    return (
      <div className="single-point-box">
        <p>데이터 1건</p>
        <strong>{formatYen(points[0].price_yen)}</strong>
        <small>{new Date(points[0].recorded_at).toLocaleDateString('ko-KR')}</small>
      </div>
    );
  }

  const w = 620;
  const h = 240;
  const p = 34;
  const yAxisLabelX = 8;
  const prices = points.map((x) => x.price_yen);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const diff = Math.max(1, max - min);

  const toX = (i: number) => p + (i * (w - p * 2)) / (points.length - 1);
  const toY = (price: number) => h - p - ((price - min) / diff) * (h - p * 2);
  const nearestIndexFromX = (x: number) => {
    const clamped = Math.max(p, Math.min(w - p, x));
    const ratio = (clamped - p) / (w - p * 2);
    return Math.max(0, Math.min(points.length - 1, Math.round(ratio * (points.length - 1))));
  };
  const poly = points.map((pt, i) => `${toX(i)},${toY(pt.price_yen)}`).join(' ');
  const activePoint = activeIdx != null ? points[activeIdx] : null;
  const activeX = activeIdx != null ? toX(activeIdx) : 0;
  const activeY = activePoint ? toY(activePoint.price_yen) : 0;
  const tooltipDate = activePoint
    ? new Date(activePoint.recorded_at).toLocaleDateString('ko-KR')
    : '';
  const tooltipW = 150;
  const tooltipH = 40;
  const tooltipX = Math.min(w - tooltipW - 6, Math.max(6, activeX + 8));
  const tooltipY = Math.max(6, activeY - tooltipH - 4);

  return (
    <div className="chart-wrap">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        className="chart-svg"
        aria-label="최근 7일 가격 변동 그래프"
        onPointerDown={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const xInView = ((e.clientX - rect.left) / rect.width) * w;
          setActiveIdx(nearestIndexFromX(xInView));
        }}
        onPointerMove={(e) => {
          if (e.pointerType === 'mouse' || (e.buttons & 1) === 1) {
            const rect = e.currentTarget.getBoundingClientRect();
            const xInView = ((e.clientX - rect.left) / rect.width) * w;
            setActiveIdx(nearestIndexFromX(xInView));
          }
        }}
      >
        <line x1={p} y1={p} x2={p} y2={h - p} className="axis" />
        <line x1={p} y1={h - p} x2={w - p} y2={h - p} className="axis" />
        <text x={yAxisLabelX} y={toY(max) + 4} className="axis-label">
          {formatYen(max)}
        </text>
        <text x={yAxisLabelX} y={toY(min) + 4} className="axis-label">
          {formatYen(min)}
        </text>
        <polyline points={poly} className="line" />
        {activePoint && (
          <>
            <line x1={activeX} y1={p} x2={activeX} y2={h - p} className="focus-line" />
            <rect
              x={tooltipX}
              y={tooltipY}
              width={tooltipW}
              height={tooltipH}
              rx="6"
              className="tooltip-bg"
            />
            <text x={tooltipX + 8} y={tooltipY + 15} className="tooltip-subtext">
              {tooltipDate}
            </text>
            <text x={tooltipX + 8} y={tooltipY + 31} className="tooltip-text">
              {formatYen(activePoint.price_yen)}
            </text>
          </>
        )}
        {points.map((pt, i) => (
          <g key={`${pt.recorded_at}-${i}`}>
            <circle
              cx={toX(i)}
              cy={toY(pt.price_yen)}
              r={activeIdx === i ? 4.4 : 3}
              className={activeIdx === i ? 'dot active' : 'dot'}
              onMouseEnter={() => setActiveIdx(i)}
            />
            <circle
              cx={toX(i)}
              cy={toY(pt.price_yen)}
              r={14}
              className="dot-hit"
              onPointerDown={() => setActiveIdx(i)}
            />
          </g>
        ))}
      </svg>
      <div className="chart-legend">
        <span>최저: {formatYen(min)}</span>
        <span>최고: {formatYen(max)}</span>
      </div>
      <div className="chart-dates">
        <span>{new Date(points[0].recorded_at).toLocaleDateString('ko-KR')}</span>
        <span>
          {new Date(points[points.length - 1].recorded_at).toLocaleDateString('ko-KR')}
        </span>
      </div>
    </div>
  );
}

export default function App() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<Tab>('cards');
  const [setFilter, setSetFilter] = useState('');
  const [rarityFilter, setRarityFilter] = useState('');
  const [groupByRarity, setGroupByRarity] = useState(true);
  const [search, setSearch] = useState('');
  const [trendFilter, setTrendFilter] = useState<TrendFilter>('all');
  const [selectedCard, setSelectedCard] = useState<Card | null>(null);
  const initialLoadLogged = useRef(false);
  const prevSyncAt = useRef<string | null>(null);
  const prevTodayExists = useRef<boolean | undefined>(undefined);

  const cardFilters = useMemo(
    () => ({
      set: setFilter || undefined,
      rarity: rarityFilter || undefined,
      q: search.trim() || undefined,
    }),
    [setFilter, rarityFilter, search]
  );

  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 3000;
      if (data.sync_in_progress || !data.today_snapshot_exists) return 3000;
      return false;
    },
    staleTime: 0,
  });

  const setsQuery = useQuery({
    queryKey: queryKeys.sets,
    queryFn: api.sets,
    staleTime: STALE_SETS,
    gcTime: STALE_SETS * 2,
  });

  const raritiesQuery = useQuery({
    queryKey: queryKeys.rarities(setFilter || undefined),
    queryFn: () => api.rarities(setFilter || undefined),
    staleTime: STALE_RARITIES,
    gcTime: STALE_RARITIES * 2,
  });

  const cardsQuery = useQuery({
    queryKey: queryKeys.cards(cardFilters),
    queryFn: () => api.cards(cardFilters),
    staleTime: STALE_CARDS,
    gcTime: STALE_CARDS * 2,
    placeholderData: (prev) => prev,
  });

  const changesQuery = useQuery({
    queryKey: queryKeys.changes,
    queryFn: api.changes,
    staleTime: STALE_CARDS,
    placeholderData: (prev) => prev,
  });

  const historyQuery = useQuery({
    queryKey: queryKeys.cardHistory(selectedCard?.id ?? 0, 7),
    queryFn: () => api.cardHistory(selectedCard!.id, 7),
    enabled: selectedCard != null,
    staleTime: STALE_CARDS,
  });

  const syncMutation = useMutation({
    mutationFn: api.sync,
    onSuccess: async () => {
      await queryClient.invalidateQueries();
    },
  });

  const sets = setsQuery.data ?? [];
  const rarities = raritiesQuery.data ?? [];
  const cards = cardsQuery.data ?? [];
  const changes = changesQuery.data?.changes ?? [];

  const cardsLoading = cardsQuery.isLoading && cards.length === 0;
  const cardsFetching = cardsQuery.isFetching && cards.length > 0;
  const changesLoading = changesQuery.isLoading && changes.length === 0;

  const queryError =
    setsQuery.error ?? raritiesQuery.error ?? cardsQuery.error ?? changesQuery.error;

  const meta = useMemo(() => {
    if (syncMutation.isSuccess && syncMutation.data) {
      return `동기화 완료 · ${syncMutation.data.total_cards}장 · ${new Date(
        syncMutation.data.fetched_at
      ).toLocaleString('ko-KR')}`;
    }

    const lastSync =
      healthQuery.data?.last_sync_at ??
      changesQuery.data?.to_snapshot_at ??
      cards.find((c) => c.price_updated_at)?.price_updated_at ??
      null;
    const dateLabel = lastSync
      ? new Date(lastSync).toLocaleString('ko-KR')
      : '스냅샷 없음';
    const syncing =
      healthQuery.data?.sync_in_progress ||
      syncMutation.isPending ||
      cardsFetching;

    return `${cards.length}장 · ${dateLabel}${syncing ? ' · 갱신 중…' : ''}`;
  }, [
    cards,
    cardsFetching,
    changesQuery.data?.to_snapshot_at,
    healthQuery.data?.last_sync_at,
    healthQuery.data?.sync_in_progress,
    syncMutation.data,
    syncMutation.isPending,
    syncMutation.isSuccess,
  ]);

  const filteredCards = useMemo(() => {
    if (trendFilter === 'all') return cards;
    return cards.filter((c) => c.week_change_direction === trendFilter);
  }, [cards, trendFilter]);

  const cardsByRarity = useMemo(() => {
    if (!groupByRarity || rarityFilter) {
      return null;
    }
    const map = new Map<string, Card[]>();
    for (const c of filteredCards) {
      const key = c.rarity ?? '미지정';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(c);
    }
    return [...map.entries()].sort(
      (a, b) =>
        raritySortKey(a[0] === '미지정' ? null : a[0]) -
        raritySortKey(b[0] === '미지정' ? null : b[0])
    );
  }, [filteredCards, groupByRarity, rarityFilter]);

  useEffect(() => {
    if (initialLoadLogged.current) return;
    if (!setsQuery.data || !raritiesQuery.data || !cardsQuery.data) return;

    const elapsed = performance.now() - INITIAL_LOAD_START;
    const fromCache =
      !setsQuery.isLoading && !raritiesQuery.isLoading && !cardsQuery.isLoading;
    console.info(
      `[perf] Initial load ready: ${elapsed.toFixed(0)}ms (display=${fromCache ? 'cached' : 'network'})`
    );
    initialLoadLogged.current = true;
  }, [setsQuery.data, raritiesQuery.data, cardsQuery.data, setsQuery.isLoading, raritiesQuery.isLoading, cardsQuery.isLoading]);

  useEffect(() => {
    const current = healthQuery.data?.last_sync_at ?? null;
    if (prevSyncAt.current && current && prevSyncAt.current !== current) {
      void queryClient.invalidateQueries();
    }
    prevSyncAt.current = current;
  }, [healthQuery.data?.last_sync_at, queryClient]);

  useEffect(() => {
    const todayExists = healthQuery.data?.today_snapshot_exists;
    if (prevTodayExists.current === false && todayExists === true) {
      void queryClient.invalidateQueries();
    }
    prevTodayExists.current = todayExists;
  }, [healthQuery.data?.today_snapshot_exists, queryClient]);

  function openCardDetail(card: Card) {
    setSelectedCard(card);
  }

  function openChangeDetail(ch: PriceChange) {
    setSelectedCard({
      id: ch.card_id,
      external_id: '',
      card_number: ch.card_number,
      rarity: ch.rarity,
      name: ch.name,
      name_ko: ch.name_ko,
      price_yen: ch.current_price,
      image_url: ch.image_url,
      detail_url: null,
      set_slug: ch.set_slug,
      set_label: ch.set_slug,
      stock: null,
      price_updated_at: changesQuery.data?.to_snapshot_at ?? null,
      week_change_percent: null,
      week_change_direction: ch.delta > 0 ? 'up' : 'down',
    });
  }

  const changeMeta = {
    from: changesQuery.data?.from_snapshot_at
      ? new Date(changesQuery.data.from_snapshot_at).toLocaleString('ko-KR')
      : '-',
    to: changesQuery.data?.to_snapshot_at
      ? new Date(changesQuery.data.to_snapshot_at).toLocaleString('ko-KR')
      : '-',
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>건담카드게임 GCG 시세</h1>
          <p className="meta">{meta}</p>
        </div>
        <button
          type="button"
          className="btn-sync"
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
        >
          {syncMutation.isPending ? '수집 중…' : '가격 수집'}
        </button>
      </header>

      {queryError && <p className="error">{String(queryError)}</p>}
      {syncMutation.error && <p className="error">{String(syncMutation.error)}</p>}

      <section className="toolbar">
        <input
          type="search"
          placeholder="카드명 / 번호 검색"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          value={setFilter}
          onChange={(e) => {
            setSetFilter(e.target.value);
            setRarityFilter('');
          }}
        >
          <option value="">전체 세트</option>
          {sets.map((s) => (
            <option key={s.slug} value={s.slug}>
              {s.label} ({s.card_count ?? 0})
            </option>
          ))}
        </select>
        <select
          value={rarityFilter}
          onChange={(e) => setRarityFilter(e.target.value)}
        >
          <option value="">전체 등급</option>
          {rarities.map((r) => (
            <option key={r.rarity} value={r.rarity}>
              {r.rarity} ({r.card_count})
            </option>
          ))}
        </select>
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={groupByRarity}
            onChange={(e) => setGroupByRarity(e.target.checked)}
            disabled={!!rarityFilter}
          />
          등급별 묶기
        </label>
        <button
          type="button"
          className={tab === 'cards' ? 'tab active' : 'tab'}
          onClick={() => setTab('cards')}
        >
          카드 목록
        </button>
        <button
          type="button"
          className={tab === 'changes' ? 'tab active' : 'tab'}
          onClick={() => setTab('changes')}
        >
          가격 변동
        </button>
      </section>

      {tab === 'cards' && (
        <section className="trend-tabs">
          <button
            type="button"
            className={trendFilter === 'all' ? 'tab active' : 'tab'}
            onClick={() => setTrendFilter('all')}
          >
            전체
          </button>
          <button
            type="button"
            className={trendFilter === 'up' ? 'tab active' : 'tab'}
            onClick={() => setTrendFilter('up')}
          >
            전일 대비 상승
          </button>
          <button
            type="button"
            className={trendFilter === 'down' ? 'tab active' : 'tab'}
            onClick={() => setTrendFilter('down')}
          >
            전일 대비 하락
          </button>
        </section>
      )}

      {tab === 'cards' ? (
        <main className="cards-panel">
          {cardsLoading ? (
            <CardGridSkeleton count={20} />
          ) : filteredCards.length === 0 ? (
            <p className="empty">
              {cards.length > 0 && trendFilter !== 'all'
                ? `전일 대비 ${trendFilter === 'up' ? '상승' : '하락'}한 카드가 없습니다.`
                : '데이터가 없습니다. 「가격 수집」을 실행하면 등급(LR++, LR+ …)이 함께 저장됩니다.'}
            </p>
          ) : cardsByRarity ? (
            cardsByRarity.map(([rarity, group]) => (
              <section key={rarity} className="rarity-section">
                <h2 className="rarity-heading">
                  <span
                    className={`rarity-badge ${rarity === '미지정' ? '' : rarityClass(rarity)}`}
                  >
                    {rarity}
                  </span>
                  <span className="rarity-count">{group.length}장</span>
                </h2>
                <div className="grid">
                  {group.map((c) => (
                    <CardTile key={c.id} c={c} onClick={openCardDetail} />
                  ))}
                </div>
              </section>
            ))
          ) : (
            <div className="grid">
              {filteredCards.map((c) => (
                <CardTile key={c.id} c={c} onClick={openCardDetail} />
              ))}
            </div>
          )}
        </main>
      ) : (
        <main className="changes">
          <p className="meta">
            {changeMeta.from} → {changeMeta.to} · {changes.length}건
          </p>
          {changesLoading ? (
            <ChangesSkeleton />
          ) : changes.length === 0 ? (
            <p className="empty">비교할 이전 스냅샷이 없습니다.</p>
          ) : (
            changes.map((ch: PriceChange) => (
              <div
                key={ch.card_id}
                className="change-row clickable"
                role="button"
                tabIndex={0}
                onClick={() => openChangeDetail(ch)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    openChangeDetail(ch);
                  }
                }}
              >
                <span>
                  {ch.image_url && (
                    <img src={ch.image_url} alt="" className="thumb" />
                  )}
                  <span>
                    {ch.rarity && (
                      <span className={`rarity-badge ${rarityClass(ch.rarity)}`}>
                        {ch.rarity}
                      </span>
                    )}{' '}
                    {ch.card_number} {ch.name_ko ?? ch.name}
                  </span>
                </span>
                <span>
                  {formatYen(ch.previous_price)} → {formatYen(ch.current_price)}
                </span>
                <span className={ch.delta > 0 ? 'delta up' : 'delta down'}>
                  {ch.delta > 0 ? '+' : ''}
                  {ch.delta.toLocaleString('ja-JP')}円
                </span>
              </div>
            ))
          )}
        </main>
      )}

      {selectedCard && (
        <div className="modal-backdrop" onClick={() => setSelectedCard(null)}>
          <section className="modal-card" onClick={(e) => e.stopPropagation()}>
            <header className="modal-header">
              <div>
                <h3>{selectedCard.name_ko ?? selectedCard.name}</h3>
                <p className="meta">
                  {selectedCard.card_number}{' '}
                  {selectedCard.rarity ? `· ${selectedCard.rarity}` : ''}
                </p>
              </div>
              <button className="modal-close" onClick={() => setSelectedCard(null)}>
                닫기
              </button>
            </header>
            {historyQuery.isLoading && !historyQuery.data ? (
              <div className="chart-skeleton">
                <div className="skeleton-block skeleton-chart" />
              </div>
            ) : historyQuery.error ? (
              <p className="error">{String(historyQuery.error)}</p>
            ) : (
              <PriceChart points={historyQuery.data ?? []} />
            )}
          </section>
        </div>
      )}
    </div>
  );
}
