import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import Base as DBBase, SessionLocal
from app.db_models import Game, CollectionItem, Playthrough


def _mk_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def test_create_tables_and_crud():
    # Ensure tables exist
    DBBase.metadata.create_all(bind=SessionLocal.kw["bind"])  # type: ignore[index]

    with Session(SessionLocal.kw["bind"]) as db:  # type: ignore[index]
        # Create a game
        gid = _mk_id("game")
        game = Game(id=gid, title="Test Game")
        db.add(game)
        db.commit()

        # Create collection item
        cid = _mk_id("col")
        col = CollectionItem(
            id=cid,
            user_id="user-1",
            game_id=gid,
            platform="PS5",
            acquisition_type="DIGITAL",
            priority=2,
        )
        db.add(col)
        db.commit()

        # Unique constraint on (user_id, game_id, platform)
        dup = CollectionItem(
            id=_mk_id("col"),
            user_id="user-1",
            game_id=gid,
            platform="PS5",
            acquisition_type="DIGITAL",
        )
        db.add(dup)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # Create playthrough referencing game and collection
        pid = _mk_id("play")
        pt = Playthrough(
            id=pid,
            user_id="user-1",
            game_id=gid,
            collection_id=cid,
            status="PLANNING",
            platform="PS5",
        )
        db.add(pt)
        db.commit()

        # Basic queries
        assert db.get(Game, gid) is not None
        assert db.get(CollectionItem, cid) is not None
        assert db.get(Playthrough, pid) is not None
