"""Yu-Yu Tei GCG rarity (レアリティ) display order."""

RARITY_ORDER: tuple[str, ...] = (
    "LR++",
    "LR+",
    "LR",
    "R+",
    "R",
    "U+",
    "U",
    "C++",
    "C+",
    "C",
    "SP",
    "P",
)

_ORDER_INDEX = {r: i for i, r in enumerate(RARITY_ORDER)}


def rarity_sort_key(rarity: str | None) -> tuple[int, str]:
    if not rarity:
        return (len(RARITY_ORDER), "")
    return (_ORDER_INDEX.get(rarity, len(RARITY_ORDER)), rarity)
