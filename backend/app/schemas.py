from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    label: str
    source_url: str
    card_count: int | None = None


class RarityOut(BaseModel):
    rarity: str
    card_count: int


class CardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    yuyu_card_id: str | None
    card_number: str | None
    rarity: str | None
    name: str
    name_ko: str | None
    image_url: str | None
    detail_url: str | None
    version: str
    set_slug: str
    set_label: str
    price_yen: int | None = None
    stock: str | None = None
    price_updated_at: datetime | None = None
    week_change_percent: float | None = None
    week_change_direction: str | None = None


class PricePointOut(BaseModel):
    recorded_at: datetime
    price_yen: int
    stock: str | None


class PriceChangeOut(BaseModel):
    card_id: int
    external_id: str
    card_number: str | None
    rarity: str | None
    name: str
    name_ko: str | None
    image_url: str | None
    set_slug: str
    previous_price: int | None
    current_price: int | None
    delta: int


class ChangesResponse(BaseModel):
    from_snapshot_at: datetime | None
    to_snapshot_at: datetime | None
    changes: list[PriceChangeOut]


class SnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fetched_at: datetime
    card_count: int


class SyncResult(BaseModel):
    snapshot_id: int
    fetched_at: datetime
    total_cards: int
    sets: list[dict]
