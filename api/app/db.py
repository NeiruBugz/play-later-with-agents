from __future__ import annotations

from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase

from app.config import settings


def _make_engine_url() -> str:
    if settings.database_url:
        return settings.database_url
    # Default to local SQLite file for tests/dev without DB configured
    return "sqlite:///./test.db"


# Create engine and session factory
_engine = create_engine(
    _make_engine_url(),
    future=True,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False}
    if "sqlite" in (_make_engine_url())
    else {},
)

SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
