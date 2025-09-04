from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.collection_service import CollectionService
from app.services.playthroughs_service import PlaythroughsService


def get_collection_service(db: Session = Depends(get_db)) -> CollectionService:
    return CollectionService(db)


def get_playthroughs_service(db: Session = Depends(get_db)) -> PlaythroughsService:
    return PlaythroughsService(db)
