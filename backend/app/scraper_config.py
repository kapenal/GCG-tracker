from dataclasses import dataclass


@dataclass(frozen=True)
class SetPage:
    slug: str
    url: str
    label: str


SET_PAGES: list[SetPage] = [
    SetPage("gd01", "https://yuyu-tei.jp/sell/gcg/s/gd01", "GD01"),
    SetPage("gd02", "https://yuyu-tei.jp/sell/gcg/s/gd02", "GD02"),
    SetPage("gd03", "https://yuyu-tei.jp/sell/gcg/s/gd03", "GD03"),
    SetPage("gd04", "https://yuyu-tei.jp/sell/gcg/s/gd04", "GD04"),
    SetPage("eb01", "https://yuyu-tei.jp/sell/gcg/s/eb01", "EB01"),
    SetPage("st01", "https://yuyu-tei.jp/sell/gcg/s/st01", "ST01"),
    SetPage("st02", "https://yuyu-tei.jp/sell/gcg/s/st02", "ST02"),
    SetPage("st03", "https://yuyu-tei.jp/sell/gcg/s/st03", "ST03"),
    SetPage("st04", "https://yuyu-tei.jp/sell/gcg/s/st04", "ST04"),
    SetPage("st05", "https://yuyu-tei.jp/sell/gcg/s/st05", "ST05"),
    SetPage("st06", "https://yuyu-tei.jp/sell/gcg/s/st06", "ST06"),
    SetPage("st07", "https://yuyu-tei.jp/sell/gcg/s/st07", "ST07"),
    SetPage("st08", "https://yuyu-tei.jp/sell/gcg/s/st08", "ST08"),
    SetPage("st09", "https://yuyu-tei.jp/sell/gcg/s/st09", "ST09"),
    SetPage("st10", "https://yuyu-tei.jp/sell/gcg/s/st10", "ST10"),
    SetPage("promo-gd10", "https://yuyu-tei.jp/sell/gcg/s/promo-gd10", "Promo GD"),
    SetPage("promo-st20", "https://yuyu-tei.jp/sell/gcg/s/promo-st20", "Promo ST"),
    SetPage("promo-t100", "https://yuyu-tei.jp/sell/gcg/s/promo-t100", "Promo T"),
    SetPage("promo-rp100", "https://yuyu-tei.jp/sell/gcg/s/rp-100", "Promo RP"),
    SetPage("promo-exbp100", "https://yuyu-tei.jp/sell/gcg/s/exbp-100", "Promo EXBP"),
    SetPage("promo-exrp100", "https://yuyu-tei.jp/sell/gcg/s/exrp-100", "Promo EXRP"),
    SetPage("reto", "https://yuyu-tei.jp/sell/gcg/s/reto", "Reto"),
]
