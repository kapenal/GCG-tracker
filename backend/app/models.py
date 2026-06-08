from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CardSet(Base):
    __tablename__ = "card_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(128))
    source_url: Mapped[str] = mapped_column(Text)

    cards: Mapped[list["Card"]] = relationship(back_populates="card_set")


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    yuyu_card_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    card_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    rarity: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(512), index=True)
    name_ko: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(64))
    set_id: Mapped[int] = mapped_column(ForeignKey("card_sets.id"), index=True)

    card_set: Mapped["CardSet"] = relationship(back_populates="cards")
    prices: Mapped[list["PriceRecord"]] = relationship(back_populates="card")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    card_count: Mapped[int] = mapped_column(Integer, default=0)

    records: Mapped[list["PriceRecord"]] = relationship(
        back_populates="snapshot",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class PriceRecord(Base):
    __tablename__ = "price_records"
    __table_args__ = (
        Index("ix_price_records_card_snapshot", "card_id", "snapshot_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(
        ForeignKey("price_snapshots.id", ondelete="CASCADE"), index=True
    )
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), index=True
    )
    price_yen: Mapped[int] = mapped_column(Integer)
    stock: Mapped[str | None] = mapped_column(String(64), nullable=True)

    snapshot: Mapped["PriceSnapshot"] = relationship(back_populates="records")
    card: Mapped["Card"] = relationship(back_populates="prices")
