import re
from dataclasses import dataclass

_IMG = re.compile(
    r'<img[^>]+src="([^"]+)"[^>]*class="card img-fluid"',
    re.IGNORECASE,
)
_ALT_RARITY = re.compile(
    r'alt="[^"]*?\s((?:LR\+\+|LR\+|LR|R\+|R|U\+|U|C\+\+|C\+|C|SP|P))\s',
    re.IGNORECASE,
)
_NUMBER = re.compile(
    r'<span[^>]*class="d-block border border-dark[^"]*"[^>]*>([^<]+)</span>',
    re.IGNORECASE,
)
_NAME = re.compile(r'<h4 class="text-primary fw-bold">([^<]+)</h4>')
_PRICE = re.compile(
    r'<strong[^>]*class="d-block text-end[^"]*"[^>]*>\s*([^<]+?)\s*</strong>',
    re.IGNORECASE,
)
_DETAIL = re.compile(r'href="(https://yuyu-tei\.jp/sell/gcg/card/[^"]+)"')
_STOCK = re.compile(r"在庫\s*:\s*([^<\n]+)")
_HIDDEN = re.compile(
    r'<input[^>]*class="(?P<class>[^"]+)"[^>]*value="(?P<val>[^"]*)"|'
    r'<input[^>]*value="(?P<val2>[^"]*)"[^>]*class="(?P<class2>[^"]+)"',
    re.IGNORECASE,
)
_SECTION = re.compile(
    r'<span[^>]*fw-bold[^>]*>([^<]+)</span>\s*Card List</h3>(.*?)(?=<h3\s|<!--\s*FOOTER|$)',
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class ScrapedCard:
    external_id: str
    yuyu_card_id: str | None
    card_number: str | None
    name: str
    rarity: str | None
    price_yen: int
    image_url: str | None
    detail_url: str | None
    version: str
    set_slug: str
    stock: str | None
    source_url: str


def _read_hidden(block: str, class_name: str) -> str | None:
    for m in _HIDDEN.finditer(block):
        if m.group("class") == class_name or m.group("class2") == class_name:
            return m.group("val") or m.group("val2")
    return None


def _parse_yen(raw: str | None) -> int | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    return int(digits) if digits else None


def _rarity_from_alt(block: str) -> str | None:
    m = _ALT_RARITY.search(block)
    if not m:
        return None
    return m.group(1).strip()


def _parse_card_block(
    block: str,
    meta_set_slug: str,
    source_url: str,
    section_rarity: str | None,
) -> ScrapedCard | None:
    img = _IMG.search(block)
    number = _NUMBER.search(block)
    name_m = _NAME.search(block)
    price_m = _PRICE.search(block)
    detail = _DETAIL.search(block)
    stock_m = _STOCK.search(block)

    name = name_m.group(1).strip() if name_m else None
    price_yen = _parse_yen(price_m.group(1) if price_m else None)
    if not name or price_yen is None:
        return None

    yuyu_card_id = _read_hidden(block, "cart_cid")
    version = _read_hidden(block, "cart_ver") or meta_set_slug
    card_number = number.group(1).strip() if number else None
    external_id = f"{version}:{yuyu_card_id or card_number or name}"
    rarity = (section_rarity or _rarity_from_alt(block) or "").strip() or None

    return ScrapedCard(
        external_id=external_id,
        yuyu_card_id=yuyu_card_id,
        card_number=card_number,
        name=name,
        rarity=rarity,
        price_yen=price_yen,
        image_url=img.group(1) if img else None,
        detail_url=detail.group(1) if detail else None,
        version=version,
        set_slug=meta_set_slug,
        stock=stock_m.group(1).strip() if stock_m else None,
        source_url=source_url,
    )


def _parse_section(section_html: str, rarity: str, set_slug: str, source_url: str) -> list[ScrapedCard]:
    cards: list[ScrapedCard] = []
    rarity_clean = rarity.strip()
    blocks = section_html.split('class="card-product')
    blocks.pop(0)
    for block in blocks:
        card = _parse_card_block(block, set_slug, source_url, rarity_clean)
        if card:
            cards.append(card)
    return cards


def parse_sell_page(html: str, set_slug: str, source_url: str) -> list[ScrapedCard]:
    cards: list[ScrapedCard] = []
    sections = list(_SECTION.finditer(html))

    if sections:
        for m in sections:
            cards.extend(
                _parse_section(m.group(2), m.group(1), set_slug, source_url)
            )
        return cards

    # Fallback: no section headers (index pages) — alt text on images
    blocks = html.split('class="card-product')
    blocks.pop(0)
    for block in blocks:
        card = _parse_card_block(block, set_slug, source_url, None)
        if card:
            cards.append(card)
    return cards
