// One-off: 19개 세트를 등급(rarity) 포함하여 다시 수집해 data/latest.json 재생성.
// Docker/Python 없이 latest.json을 갱신할 때 사용. (Node 18+ 내장 fetch)
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');

const USER_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const FETCH_DELAY_MS = 2000;

const SET_PAGES = [
  { slug: 'gd01', url: 'https://yuyu-tei.jp/sell/gcg/s/gd01', label: 'GD01' },
  { slug: 'gd02', url: 'https://yuyu-tei.jp/sell/gcg/s/gd02', label: 'GD02' },
  { slug: 'gd03', url: 'https://yuyu-tei.jp/sell/gcg/s/gd03', label: 'GD03' },
  { slug: 'gd04', url: 'https://yuyu-tei.jp/sell/gcg/s/gd04', label: 'GD04' },
  { slug: 'gd05', url: 'https://yuyu-tei.jp/sell/gcg/s/gd05', label: 'GD05' },
  { slug: 'eb01', url: 'https://yuyu-tei.jp/sell/gcg/s/eb01', label: 'EB01' },
  { slug: 'st01', url: 'https://yuyu-tei.jp/sell/gcg/s/st01', label: 'ST01' },
  { slug: 'st02', url: 'https://yuyu-tei.jp/sell/gcg/s/st02', label: 'ST02' },
  { slug: 'st03', url: 'https://yuyu-tei.jp/sell/gcg/s/st03', label: 'ST03' },
  { slug: 'st04', url: 'https://yuyu-tei.jp/sell/gcg/s/st04', label: 'ST04' },
  { slug: 'st05', url: 'https://yuyu-tei.jp/sell/gcg/s/st05', label: 'ST05' },
  { slug: 'st06', url: 'https://yuyu-tei.jp/sell/gcg/s/st06', label: 'ST06' },
  { slug: 'st07', url: 'https://yuyu-tei.jp/sell/gcg/s/st07', label: 'ST07' },
  { slug: 'st08', url: 'https://yuyu-tei.jp/sell/gcg/s/st08', label: 'ST08' },
  { slug: 'st09', url: 'https://yuyu-tei.jp/sell/gcg/s/st09', label: 'ST09' },
  { slug: 'st10', url: 'https://yuyu-tei.jp/sell/gcg/s/st10', label: 'ST10' },
  { slug: 'promo-gd10', url: 'https://yuyu-tei.jp/sell/gcg/s/promo-gd10', label: 'Promo GD' },
  { slug: 'promo-st20', url: 'https://yuyu-tei.jp/sell/gcg/s/promo-st20', label: 'Promo ST' },
  { slug: 'promo-t100', url: 'https://yuyu-tei.jp/sell/gcg/s/promo-t100', label: 'Promo T' },
  { slug: 'promo-rp100', url: 'https://yuyu-tei.jp/sell/gcg/s/rp-100', label: 'Promo RP' },
  { slug: 'promo-exbp100', url: 'https://yuyu-tei.jp/sell/gcg/s/exbp-100', label: 'Promo EXBP' },
  { slug: 'promo-exrp100', url: 'https://yuyu-tei.jp/sell/gcg/s/exrp-100', label: 'Promo EXRP' },
  { slug: 'reto', url: 'https://yuyu-tei.jp/sell/gcg/s/reto', label: 'Reto' },
];

const SECTION =
  /<span[^>]*fw-bold[^>]*>([^<]+)<\/span>\s*Card List<\/h3>(.*?)(?=<h3\s|$)/gis;
const ALT_RARITY = /alt="[^"]*?\s(LR\+\+|LR\+|LR|R\+|R|U\+|U|C\+\+|C\+|C|SP|P)\s/i;

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function parseYen(raw) {
  if (!raw) return null;
  const digits = String(raw).replace(/\D/g, '');
  return digits ? Number.parseInt(digits, 10) : null;
}

function readHidden(block, className) {
  const re = new RegExp(
    `<input[^>]*class="${className}"[^>]*value="([^"]*)"|` +
      `<input[^>]*value="([^"]*)"[^>]*class="${className}"`,
    'i'
  );
  const m = block.match(re);
  return m ? m[1] ?? m[2] ?? null : null;
}

function parseCardBlock(block, setSlug, sourceUrl, sectionRarity) {
  const img = block.match(/<img[^>]+src="([^"]+)"[^>]*class="card img-fluid"/i);
  const number = block.match(
    /<span[^>]*class="d-block border border-dark[^"]*"[^>]*>([^<]+)<\/span>/i
  );
  const nameM = block.match(/<h4 class="text-primary fw-bold">([^<]+)<\/h4>/);
  const priceM = block.match(
    /<strong[^>]*class="d-block text-end[^"]*"[^>]*>\s*([^<]+?)\s*<\/strong>/i
  );
  const detail = block.match(/href="(https:\/\/yuyu-tei\.jp\/sell\/gcg\/card\/[^"]+)"/);
  const stockM = block.match(/在庫\s*:\s*([^<\n]+)/);

  const name = nameM ? nameM[1].trim() : null;
  const priceYen = parseYen(priceM ? priceM[1] : null);
  if (!name || priceYen == null) return null;

  const cardId = readHidden(block, 'cart_cid');
  const version = readHidden(block, 'cart_ver') || setSlug;
  const cardNumber = number ? number[1].trim() : null;
  const altR = block.match(ALT_RARITY);
  const rarity = (sectionRarity || (altR ? altR[1] : null) || '').trim() || null;

  return {
    id: `${version}:${cardId ?? cardNumber ?? name}`,
    cardId,
    cardNumber,
    rarity,
    name,
    priceYen,
    imageUrl: img ? img[1] : null,
    detailUrl: detail ? detail[1] : null,
    setSlug,
    version,
    stock: stockM ? stockM[1].trim() : null,
    sourceUrl,
  };
}

function parseSellPage(html, setSlug, sourceUrl) {
  const cards = [];
  const sections = [...html.matchAll(SECTION)];

  if (sections.length > 0) {
    for (const m of sections) {
      const rarity = m[1].trim();
      const blocks = m[2].split('class="card-product');
      blocks.shift();
      for (const b of blocks) {
        const c = parseCardBlock(b, setSlug, sourceUrl, rarity);
        if (c) cards.push(c);
      }
    }
    return cards;
  }

  const blocks = html.split('class="card-product');
  blocks.shift();
  for (const b of blocks) {
    const c = parseCardBlock(b, setSlug, sourceUrl, null);
    if (c) cards.push(c);
  }
  return cards;
}

function todayLocal() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate()
  ).padStart(2, '0')}`;
}

async function main() {
  await fs.mkdir(path.join(DATA_DIR, 'history'), { recursive: true });
  const allCards = [];
  const sets = [];

  for (let i = 0; i < SET_PAGES.length; i++) {
    const page = SET_PAGES[i];
    try {
      const res = await fetch(page.url, {
        headers: { 'User-Agent': USER_AGENT, 'Accept-Language': 'ja' },
        signal: AbortSignal.timeout(60_000),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const html = await res.text();
      const cards = parseSellPage(html, page.slug, page.url);
      allCards.push(...cards);
      const withR = cards.filter((c) => c.rarity).length;
      sets.push({ slug: page.slug, url: page.url, count: cards.length });
      console.log(`[ok] ${page.label}: ${cards.length} cards (rarity: ${withR})`);
    } catch (err) {
      sets.push({ slug: page.slug, url: page.url, count: 0, error: String(err) });
      console.error(`[fail] ${page.label}: ${err}`);
    }
    if (i < SET_PAGES.length - 1) await sleep(FETCH_DELAY_MS);
  }

  const snapshot = {
    fetchedAt: new Date().toISOString(),
    date: todayLocal(),
    cards: allCards,
    sets,
  };

  await fs.writeFile(
    path.join(DATA_DIR, 'latest.json'),
    JSON.stringify(snapshot, null, 2),
    'utf8'
  );
  await fs.writeFile(
    path.join(DATA_DIR, 'history', `${snapshot.date}.json`),
    JSON.stringify(snapshot, null, 2),
    'utf8'
  );

  const total = allCards.length;
  const withRarity = allCards.filter((c) => c.rarity).length;
  console.log(`\nSaved ${total} cards (rarity filled: ${withRarity})`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
