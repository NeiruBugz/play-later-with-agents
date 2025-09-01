from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, String, func
from sqlalchemy.orm import Session, Mapped, mapped_column

from app.db import SessionLocal
from app.db import Base as _Base


class Base(_Base):
    __abstract__ = True
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid4().hex
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SessionRecord(Base):
    __tablename__ = "sessions"

    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


def create_session(
    db: Session, *, user_id: str, refresh_token: Optional[str] = None
) -> SessionRecord:
    rec = SessionRecord(user_id=user_id, refresh_token=refresh_token)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def get_session(db: Session, session_id: str) -> Optional[SessionRecord]:
    return db.get(SessionRecord, session_id)


def deactivate_session(db: Session, session_id: str) -> bool:
    rec = db.get(SessionRecord, session_id)
    if not rec:
        return False
    rec.active = False
    db.add(rec)
    db.commit()
    return True
