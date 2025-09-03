from __future__ import annotations

from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, HTTPException, Response, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, asc, func, select
from sqlalchemy.exc import IntegrityError

from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.db_models import CollectionItem, Game, Playthrough
from app.schemas import (
    CollectionListResponse,
    CollectionItemExpanded,
    CollectionItemCreate,
    CollectionItemUpdate,
    CollectionSortBy,
    AcquisitionType,
    GameDetail,
    CollectionSnippet,
    BulkCollectionRequest,
    BulkCollectionResponse,
    BulkCollectionResult,
    BulkCollectionAction,
    CollectionStats,
)

import logging
from app.services import collection_service

router = APIRouter(prefix="/collection", tags=["collection"])

logger = logging.getLogger("app.router.collection")


@router.get("", response_model=CollectionListResponse)
async def list_collection(
    # Filtering parameters
    platform: Optional[str] = Query(None, description="Filter by platform"),
    acquisition_type: Optional[AcquisitionType] = Query(
        None, description="Filter by acquisition type"
    ),
    priority: Optional[int] = Query(
        None, ge=1, le=5, description="Filter by priority (1-5)"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in game title or notes"),
    # Sorting parameters
    sort_by: CollectionSortBy = Query(
        CollectionSortBy.UPDATED_AT, description="Sort field"
    ),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    # Pagination parameters
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    # Dependencies
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionListResponse:
    """Get user's game collection with filtering, sorting, and pagination."""
    return collection_service.list_collection(
        db=db,
        current_user=current_user,
        platform=platform,
        acquisition_type=acquisition_type,
        priority=priority,
        is_active=is_active,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=CollectionStats)
async def get_collection_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionStats:
    """Get user's collection statistics and insights."""
    return collection_service.get_collection_stats(db=db, current_user=current_user)


@router.post(
    "", response_model=CollectionItemExpanded, status_code=status.HTTP_201_CREATED
)
async def create_collection_item(
    item_data: CollectionItemCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionItemExpanded:
    """Create a new collection item for the authenticated user."""
    return collection_service.create_collection_item(
        db=db, current_user=current_user, item_data=item_data
    )


@router.get("/{collection_id}", response_model=CollectionItemExpanded)
async def get_collection_item(
    collection_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionItemExpanded:
    """Get a collection item by ID for the authenticated user."""
    return collection_service.get_collection_item(
        db=db, current_user=current_user, collection_id=collection_id
    )


@router.put("/{collection_id}", response_model=CollectionItemExpanded)
async def update_collection_item(
    collection_id: str,
    update_data: CollectionItemUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionItemExpanded:
    """Update mutable fields of a collection item for the authenticated user."""

    # First, get the existing collection item with game data
    query = (
        select(CollectionItem, Game)
        .join(Game, CollectionItem.game_id == Game.id)
        .where(
            and_(
                CollectionItem.id == collection_id,
                CollectionItem.user_id == current_user.id,
            )
        )
    )

    result = db.execute(query).first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collection item not found"
        )

    collection_item, game = result

    # Update only the fields that are provided (not None)
    update_values = {}
    if update_data.acquisition_type is not None:
        update_values["acquisition_type"] = update_data.acquisition_type.value
    if update_data.acquired_at is not None:
        update_values["acquired_at"] = update_data.acquired_at
    if update_data.priority is not None:
        update_values["priority"] = update_data.priority
    if update_data.is_active is not None:
        update_values["is_active"] = update_data.is_active
    if update_data.notes is not None:
        update_values["notes"] = update_data.notes

    # If there are no updates, just return the current item
    if not update_values:
        # Still need to get playthroughs and build response
        pass
    else:
        # Update the timestamp
        update_values["updated_at"] = datetime.now(timezone.utc)

        # Apply the updates
        for field, value in update_values.items():
            setattr(collection_item, field, value)

        db.commit()
        db.refresh(collection_item)

    # Get playthroughs for this collection item
    playthroughs_query = select(Playthrough).where(
        Playthrough.collection_id == collection_item.id
    )
    playthroughs = db.scalars(playthroughs_query).all()

    # Convert to response model
    game_detail = GameDetail(
        id=game.id,
        title=game.title,
        cover_image_id=game.cover_image_id,
        release_date=game.release_date,
        description=game.description,
        igdb_id=game.igdb_id,
        hltb_id=game.hltb_id,
        steam_app_id=game.steam_app_id,
    )

    # Convert playthroughs to dict format
    playthrough_dicts = []
    for pt in playthroughs:
        playthrough_dicts.append(
            {
                "id": pt.id,
                "status": pt.status,
                "platform": pt.platform,
                "started_at": pt.started_at.isoformat() if pt.started_at else None,
                "completed_at": pt.completed_at.isoformat()
                if pt.completed_at
                else None,
                "play_time_hours": pt.play_time_hours,
                "rating": pt.rating,
            }
        )

    return CollectionItemExpanded(
        id=collection_item.id,
        user_id=collection_item.user_id,
        game=game_detail,
        platform=collection_item.platform,
        acquisition_type=AcquisitionType(collection_item.acquisition_type),
        acquired_at=collection_item.acquired_at,
        priority=collection_item.priority,
        is_active=collection_item.is_active,
        notes=collection_item.notes,
        playthroughs=playthrough_dicts,
        created_at=collection_item.created_at,
        updated_at=collection_item.updated_at,
    )


@router.delete("/{collection_id}")
async def delete_collection_item(
    collection_id: str,
    hard_delete: bool = Query(False, description="Permanently delete the item"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a collection item (soft delete by default, hard delete with safeguards)."""
    return collection_service.delete_collection_item(
        db=db,
        current_user=current_user,
        collection_id=collection_id,
        hard_delete=hard_delete,
    )


@router.post("/bulk", response_model=BulkCollectionResponse)
async def bulk_collection_operations(
    request: BulkCollectionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BulkCollectionResponse:
    """Perform bulk operations on multiple collection items."""
    return collection_service.bulk_collection_operations(
        db=db, current_user=current_user, request=request
    )
