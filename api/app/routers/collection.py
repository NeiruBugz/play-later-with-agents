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

    # Find the collection item
    query = select(CollectionItem).where(
        and_(
            CollectionItem.id == collection_id,
            CollectionItem.user_id == current_user.id,
        )
    )

    collection_item = db.scalar(query)
    if not collection_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Collection item not found"
        )

    if hard_delete:
        # Check for associated playthroughs before hard delete
        playthroughs_query = select(func.count(Playthrough.id)).where(
            Playthrough.collection_id == collection_item.id
        )
        playthrough_count = db.scalar(playthroughs_query)

        if playthrough_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot hard delete: collection item has associated playthroughs",
            )

        # Perform hard delete
        db.delete(collection_item)
        db.commit()

        return {"message": "Collection item permanently deleted", "id": collection_id}
    else:
        # Perform soft delete
        collection_item.is_active = False
        collection_item.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(collection_item)

        return {
            "message": "Collection item soft deleted",
            "id": collection_id,
            "is_active": collection_item.is_active,
        }


@router.post("/bulk", response_model=BulkCollectionResponse)
async def bulk_collection_operations(
    request: BulkCollectionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BulkCollectionResponse:
    """Perform bulk operations on multiple collection items."""

    # Validate required data for each action
    if request.action == BulkCollectionAction.UPDATE_PRIORITY:
        if not request.data or "priority" not in request.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Priority data is required for update_priority action",
            )
    elif request.action == BulkCollectionAction.UPDATE_PLATFORM:
        if not request.data or "platform" not in request.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Platform data is required for update_platform action",
            )
    # HIDE and ACTIVATE actions don't require data

    results = []
    updated_count = 0

    for collection_id in request.collection_ids:
        try:
            # Find the collection item belonging to the current user
            query = select(CollectionItem).where(
                and_(
                    CollectionItem.id == collection_id,
                    CollectionItem.user_id == current_user.id,
                )
            )
            collection_item = db.scalar(query)

            if not collection_item:
                results.append(
                    BulkCollectionResult(
                        id=collection_id,
                        success=False,
                        error="Collection item not found or not owned by user",
                    )
                )
                continue

            # Perform the requested action
            updated_data = {}

            if request.action == BulkCollectionAction.UPDATE_PRIORITY:
                priority = request.data["priority"]
                # Validate priority range
                if not isinstance(priority, int) or priority < 1 or priority > 5:
                    results.append(
                        BulkCollectionResult(
                            id=collection_id,
                            success=False,
                            error="Priority must be between 1 and 5",
                        )
                    )
                    continue

                collection_item.priority = priority
                updated_data["priority"] = priority

            elif request.action == BulkCollectionAction.UPDATE_PLATFORM:
                platform = request.data["platform"]
                if not platform or not isinstance(platform, str):
                    results.append(
                        BulkCollectionResult(
                            id=collection_id,
                            success=False,
                            error="Platform must be a non-empty string",
                        )
                    )
                    continue

                collection_item.platform = platform
                updated_data["platform"] = platform

            elif request.action == BulkCollectionAction.HIDE:
                collection_item.is_active = False
                updated_data["is_active"] = False

            elif request.action == BulkCollectionAction.ACTIVATE:
                collection_item.is_active = True
                updated_data["is_active"] = True

            # Update timestamp
            collection_item.updated_at = datetime.now(timezone.utc)
            updated_data["updated_at"] = collection_item.updated_at.isoformat()

            # Commit the changes for this item
            db.commit()
            db.refresh(collection_item)

            results.append(
                BulkCollectionResult(
                    id=collection_id,
                    success=True,
                    error=None,
                    updated_data=updated_data,
                )
            )
            updated_count += 1

        except Exception as e:
            db.rollback()
            results.append(
                BulkCollectionResult(id=collection_id, success=False, error=str(e))
            )

    # Determine response status
    total_count = len(request.collection_ids)
    all_successful = updated_count == total_count

    response = BulkCollectionResponse(
        success=all_successful,
        updated_count=updated_count,
        total_count=total_count,
        results=results,
    )

    # Return appropriate status code
    if all_successful:
        return response  # 200 OK
    else:
        # Return 207 Multi-Status for partial success
        # We need to manually set the status code to 207
        # FastAPI doesn't have a direct way to return 207, so we'll use a custom response
        content = response.model_dump_json()
        return Response(
            content=content,
            status_code=207,
            headers={"content-type": "application/json"},
        )
