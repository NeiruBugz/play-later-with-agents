from __future__ import annotations

from typing import Optional
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, HTTPException, status
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
    CollectionSortBy,
    AcquisitionType,
    GameDetail,
    CollectionSnippet,
)

router = APIRouter(prefix="/collection", tags=["collection"])


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

    # Build base query - start with CollectionItem joined with Game
    query = (
        select(CollectionItem, Game)
        .join(Game, CollectionItem.game_id == Game.id)
        .where(CollectionItem.user_id == current_user.id)
    )

    # Apply filters
    filters = []

    if platform:
        filters.append(CollectionItem.platform == platform)

    if acquisition_type:
        filters.append(CollectionItem.acquisition_type == acquisition_type.value)

    if priority is not None:
        filters.append(CollectionItem.priority == priority)

    if is_active is not None:
        filters.append(CollectionItem.is_active == is_active)

    if search:
        # Search in game title or collection notes (Game is already joined)
        search_term = f"%{search}%"
        filters.append(
            or_(Game.title.ilike(search_term), CollectionItem.notes.ilike(search_term))
        )

    # Apply all filters
    if filters:
        query = query.where(and_(*filters))

    # Apply sorting
    # Map sort field to the correct table column
    if sort_by.value == "title":
        sort_column = Game.title  # Title comes from Game table
    else:
        sort_column = getattr(CollectionItem, sort_by.value)

    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_count = db.scalar(count_query)

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Execute query - get both CollectionItem and Game
    results = db.execute(query).all()

    # Convert to response models
    items = []
    for collection_item, game in results:
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

        expanded_item = CollectionItemExpanded(
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
        items.append(expanded_item)

    return CollectionListResponse(
        items=items,
        total_count=total_count or 0,
        limit=limit,
        offset=offset,
        filters_applied={
            "platform": platform,
            "acquisition_type": acquisition_type.value if acquisition_type else None,
            "priority": priority,
            "is_active": is_active,
            "search": search,
            "sort_by": sort_by.value,
            "sort_order": sort_order,
        },
    )


@router.post(
    "", response_model=CollectionItemExpanded, status_code=status.HTTP_201_CREATED
)
async def create_collection_item(
    item_data: CollectionItemCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionItemExpanded:
    """Create a new collection item for the authenticated user."""

    # Check if the game exists
    game_query = select(Game).where(Game.id == item_data.game_id)
    game = db.scalar(game_query)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

    # Create the collection item
    collection_item = CollectionItem(
        id=str(uuid4()),
        user_id=current_user.id,
        game_id=item_data.game_id,
        platform=item_data.platform,
        acquisition_type=item_data.acquisition_type.value,
        acquired_at=item_data.acquired_at,
        priority=item_data.priority,
        is_active=True,
        notes=item_data.notes,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    try:
        db.add(collection_item)
        db.commit()
        db.refresh(collection_item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Collection item already exists for this user, game, and platform",
        )

    # Get playthroughs for this collection item (will be empty for new items)
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

    # Convert playthroughs to dict format (will be empty list)
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


@router.get("/{collection_id}", response_model=CollectionItemExpanded)
async def get_collection_item(
    collection_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionItemExpanded:
    """Get a collection item by ID for the authenticated user."""

    # Query for the collection item with joined game data
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
