from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.db import SessionLocal


def test_alembic_upgrade_head_creates_tables() -> None:
    # Configure Alembic to use the project alembic.ini
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(cfg, "head")

    engine = SessionLocal.kw["bind"]  # type: ignore[index]
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    for t in ("games", "collection_items", "playthroughs", "sessions"):
        assert t in tables
