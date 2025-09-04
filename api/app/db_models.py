from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    String,
    Date,
    DateTime,
    Integer,
    Float,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False, index=True)
    cover_image_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    release_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    igdb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    hltb_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    steam_app_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Rely on column-level index=True for title; avoid duplicate explicit Index


class CollectionItem(Base):
    __tablename__ = "collection_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    game_id: Mapped[str] = mapped_column(
        String, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String, nullable=False, index=True)
    acquisition_type: Mapped[str] = mapped_column(String, nullable=False)
    acquired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    priority: Mapped[Optional[int]] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "game_id", "platform", name="uq_user_game_platform"
        ),
    )


class Playthrough(Base):
    __tablename__ = "playthroughs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    game_id: Mapped[str] = mapped_column(
        String, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    collection_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("collection_items.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String, nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    play_time_hours: Mapped[Optional[float]] = mapped_column(Float)
    playthrough_type: Mapped[Optional[str]] = mapped_column(String)
    difficulty: Mapped[Optional[str]] = mapped_column(String)
    rating: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
