from __future__ import annotations

from typing import Optional
from datetime import datetime, date, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, asc, func, select
from sqlalchemy.exc import IntegrityError

from app.auth import CurrentUser, get_current_user
from app.db import get_db
from app.db_models import Playthrough, Game, CollectionItem
from app.schemas import (
    PlaythroughListResponse,
    PlaythroughListItem,
    PlaythroughCreate,
    PlaythroughUpdate,
    PlaythroughComplete,
    PlaythroughDeleteResponse,
    PlaythroughBulkRequest,
    PlaythroughBulkResponse,
    BulkAction,
    BulkResultItem,
    BulkFailedItem,
    PlaythroughResponse,
    PlaythroughDetail,
    PlaythroughSortBy,
    PlaythroughStatus,
    CompletionType,
    GameSummary,
    GameDetail,
    CollectionSnippet,
    AcquisitionType,
    SortOrder,
    BacklogItem,
    BacklogResponse,
    PlayingItem,
    PlayingResponse,
    CompletedItem,
    CompletedResponse,
    PlaythroughStats,
)

import logging

router = APIRouter(prefix="/playthroughs", tags=["playthroughs"])

logger = logging.getLogger("app.router.playthroughs")


@router.get("", response_model=PlaythroughListResponse)
async def list_playthroughs(
    # Status filter
    status: Optional[list[PlaythroughStatus]] = Query(
        None, description="Filter by playthrough status"
    ),
    # Platform filter
    platform: Optional[list[str]] = Query(None, description="Filter by platforms"),
    # Rating filters
    rating_min: Optional[int] = Query(
        None, ge=1, le=10, description="Minimum rating (1-10)"
    ),
    rating_max: Optional[int] = Query(
        None, ge=1, le=10, description="Maximum rating (1-10)"
    ),
    # Play time filters
    play_time_min: Optional[float] = Query(
        None, ge=0, description="Minimum play time in hours"
    ),
    play_time_max: Optional[float] = Query(
        None, ge=0, description="Maximum play time in hours"
    ),
    # Difficulty and type filters
    difficulty: Optional[list[str]] = Query(
        None, description="Filter by difficulty settings"
    ),
    playthrough_type: Optional[list[str]] = Query(
        None, description="Filter by playthrough type"
    ),
    # Date filters
    started_after: Optional[date] = Query(
        None, description="Started after date (YYYY-MM-DD)"
    ),
    started_before: Optional[date] = Query(
        None, description="Started before date (YYYY-MM-DD)"
    ),
    completed_after: Optional[date] = Query(
        None, description="Completed after date (YYYY-MM-DD)"
    ),
    completed_before: Optional[date] = Query(
        None, description="Completed before date (YYYY-MM-DD)"
    ),
    # Search
    search: Optional[str] = Query(None, description="Search in game titles and notes"),
    # Sorting parameters
    sort_by: PlaythroughSortBy = Query(
        PlaythroughSortBy.UPDATED_AT, description="Sort field"
    ),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort direction"),
    # Pagination parameters
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    # Dependencies
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaythroughListResponse:
    """Get user's playthroughs with advanced filtering options."""

    # Validate rating range
    if rating_min is not None and rating_max is not None and rating_min > rating_max:
        raise HTTPException(
            status_code=422,
            detail="rating_min must be less than or equal to rating_max",
        )

    # Validate play time range
    if (
        play_time_min is not None
        and play_time_max is not None
        and play_time_min > play_time_max
    ):
        raise HTTPException(
            status_code=422,
            detail="play_time_min must be less than or equal to play_time_max",
        )

    logger.info(
        f"User {current_user.id} requested playthroughs list with filters: "
        f"status={status}, platform={platform}, rating_min={rating_min}, rating_max={rating_max}"
    )

    # Build base query - start with Playthrough joined with Game
    query = (
        select(Playthrough, Game, CollectionItem)
        .join(Game, Playthrough.game_id == Game.id)
        .outerjoin(CollectionItem, Playthrough.collection_id == CollectionItem.id)
        .where(Playthrough.user_id == current_user.id)
    )

    # Apply filters
    filters = []

    if status:
        # Convert enum values to strings for database query
        status_values = [s.value for s in status]
        filters.append(Playthrough.status.in_(status_values))

    if platform:
        filters.append(Playthrough.platform.in_(platform))

    if rating_min is not None:
        filters.append(Playthrough.rating >= rating_min)

    if rating_max is not None:
        filters.append(Playthrough.rating <= rating_max)

    if play_time_min is not None:
        filters.append(Playthrough.play_time_hours >= play_time_min)

    if play_time_max is not None:
        filters.append(Playthrough.play_time_hours <= play_time_max)

    if difficulty:
        filters.append(Playthrough.difficulty.in_(difficulty))

    if playthrough_type:
        filters.append(Playthrough.playthrough_type.in_(playthrough_type))

    if started_after:
        filters.append(
            Playthrough.started_at
            >= datetime.combine(started_after, datetime.min.time())
        )

    if started_before:
        filters.append(
            Playthrough.started_at
            <= datetime.combine(started_before, datetime.max.time())
        )

    if completed_after:
        filters.append(
            Playthrough.completed_at
            >= datetime.combine(completed_after, datetime.min.time())
        )

    if completed_before:
        filters.append(
            Playthrough.completed_at
            <= datetime.combine(completed_before, datetime.max.time())
        )

    if search:
        # Search in game title or playthrough notes
        search_term = f"%{search}%"
        filters.append(
            or_(Game.title.ilike(search_term), Playthrough.notes.ilike(search_term))
        )

    # Apply all filters
    if filters:
        query = query.where(and_(*filters))

    # Apply sorting
    # Map sort field to the correct table column
    if sort_by.value == "title":
        sort_column = Game.title  # Title comes from Game table
    elif sort_by.value == "play_time_hours":
        sort_column = Playthrough.play_time_hours
    else:
        sort_column = getattr(Playthrough, sort_by.value)

    if sort_order == SortOrder.DESC:
        # Handle NULL values in sorting - put them at the end for DESC
        query = query.order_by(sort_column.desc().nulls_last())
    else:
        # Handle NULL values in sorting - put them at the end for ASC
        query = query.order_by(sort_column.asc().nulls_last())

    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_count = db.scalar(count_query)

    # Apply pagination
    query = query.offset(offset).limit(limit)

    # Execute query - get Playthrough, Game, and optional CollectionItem
    results = db.execute(query).all()

    # Convert to response models
    items = []
    for playthrough, game, collection_item in results:
        # Create game summary
        game_summary = GameSummary(
            id=game.id,
            title=game.title,
            cover_image_id=game.cover_image_id,
            release_date=game.release_date,
            main_story=getattr(game, "main_story", None),
            main_extra=getattr(game, "main_extra", None),
            completionist=getattr(game, "completionist", None),
        )

        # Create collection snippet if available
        collection_snippet = None
        if collection_item:
            collection_snippet = CollectionSnippet(
                id=collection_item.id,
                platform=collection_item.platform,
                acquisition_type=AcquisitionType(collection_item.acquisition_type),
                acquired_at=collection_item.acquired_at,
                priority=collection_item.priority,
                is_active=collection_item.is_active,
            )

        # Create playthrough list item
        playthrough_item = PlaythroughListItem(
            id=playthrough.id,
            user_id=playthrough.user_id,
            status=PlaythroughStatus(playthrough.status),
            platform=playthrough.platform,
            started_at=playthrough.started_at,
            completed_at=playthrough.completed_at,
            play_time_hours=playthrough.play_time_hours,
            playthrough_type=playthrough.playthrough_type,
            difficulty=playthrough.difficulty,
            rating=playthrough.rating,
            notes=playthrough.notes,
            created_at=playthrough.created_at,
            updated_at=playthrough.updated_at,
            game=game_summary,
            collection=collection_snippet,
        )
        items.append(playthrough_item)

    return PlaythroughListResponse(
        items=items,
        total_count=total_count or 0,
        limit=limit,
        offset=offset,
        filters_applied={
            "status": [s.value for s in status] if status else None,
            "platform": platform,
            "rating_min": rating_min,
            "rating_max": rating_max,
            "play_time_min": play_time_min,
            "play_time_max": play_time_max,
            "difficulty": difficulty,
            "playthrough_type": playthrough_type,
            "started_after": started_after.isoformat() if started_after else None,
            "started_before": started_before.isoformat() if started_before else None,
            "completed_after": completed_after.isoformat() if completed_after else None,
            "completed_before": completed_before.isoformat()
            if completed_before
            else None,
            "search": search,
            "sort_by": sort_by.value,
            "sort_order": sort_order.value,
        },
    )


@router.post(
    "", response_model=PlaythroughResponse, status_code=status.HTTP_201_CREATED
)
async def create_playthrough(
    playthrough_data: PlaythroughCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaythroughResponse:
    """Create a new playthrough for the authenticated user."""

    logger.info(
        f"User {current_user.id} creating playthrough for game {playthrough_data.game_id}"
    )

    # Validate that the game exists
    game = db.query(Game).filter(Game.id == playthrough_data.game_id).first()
    if not game:
        logger.warning(
            f"Game {playthrough_data.game_id} not found for user {current_user.id}"
        )
        raise HTTPException(status_code=404, detail="Game not found")

    # Validate collection item if provided
    collection_item = None
    if playthrough_data.collection_id:
        collection_item = (
            db.query(CollectionItem)
            .filter(
                and_(
                    CollectionItem.id == playthrough_data.collection_id,
                    CollectionItem.user_id == current_user.id,
                )
            )
            .first()
        )

        if not collection_item:
            logger.warning(
                f"Collection item {playthrough_data.collection_id} not found for user {current_user.id}"
            )
            raise HTTPException(status_code=404, detail="Collection item not found")

        # Validate that collection item is for the same game
        if collection_item.game_id != playthrough_data.game_id:
            logger.warning(
                f"Collection item {playthrough_data.collection_id} is for game {collection_item.game_id}, "
                f"but playthrough is for game {playthrough_data.game_id}"
            )
            raise HTTPException(
                status_code=400, detail="Collection item is for a different game"
            )

    # Create the playthrough
    playthrough = Playthrough(
        id=str(uuid4()),
        user_id=current_user.id,
        game_id=playthrough_data.game_id,
        collection_id=playthrough_data.collection_id,
        status=playthrough_data.status.value,
        platform=playthrough_data.platform,
        started_at=playthrough_data.started_at,
        completed_at=playthrough_data.completed_at,
        play_time_hours=playthrough_data.play_time_hours,
        playthrough_type=playthrough_data.playthrough_type,
        difficulty=playthrough_data.difficulty,
        rating=playthrough_data.rating,
        notes=playthrough_data.notes,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    try:
        db.add(playthrough)
        db.commit()
        db.refresh(playthrough)

        logger.info(f"Created playthrough {playthrough.id} for user {current_user.id}")

        # Return the created playthrough
        return PlaythroughResponse(
            id=playthrough.id,
            user_id=playthrough.user_id,
            game_id=playthrough.game_id,
            collection_id=playthrough.collection_id,
            status=PlaythroughStatus(playthrough.status),
            platform=playthrough.platform,
            started_at=playthrough.started_at,
            completed_at=playthrough.completed_at,
            play_time_hours=playthrough.play_time_hours,
            playthrough_type=playthrough.playthrough_type,
            difficulty=playthrough.difficulty,
            rating=playthrough.rating,
            notes=playthrough.notes,
            created_at=playthrough.created_at,
            updated_at=playthrough.updated_at,
        )

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database error creating playthrough: {e}")
        raise HTTPException(status_code=500, detail="Failed to create playthrough")


# ===== Convenience Endpoints =====


@router.get("/backlog", response_model=BacklogResponse)
async def get_backlog(
    priority: Optional[int] = Query(
        None, ge=1, le=5, description="Filter by collection priority"
    ),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BacklogResponse:
    """Get user's backlog (planning status playthroughs)."""
    logger.info(f"Getting backlog for user {current_user.id}")

    # Build query for planning playthroughs
    query = (
        db.query(Playthrough)
        .filter(
            Playthrough.user_id == current_user.id,
            Playthrough.status == PlaythroughStatus.PLANNING,
        )
        .join(Game, Playthrough.game_id == Game.id)
        .outerjoin(CollectionItem, Playthrough.collection_id == CollectionItem.id)
    )

    # Apply priority filter if specified
    if priority is not None:
        query = query.filter(CollectionItem.priority == priority)

    # Order by created_at descending (most recent first)
    query = query.order_by(Playthrough.created_at.desc())

    try:
        # Execute query with proper joins
        results = query.all()

        # Convert to response format
        backlog_items = []
        for playthrough in results:
            # Get the game from the join
            game = db.query(Game).filter(Game.id == playthrough.game_id).first()
            if not game:
                continue

            # Get game details
            game_summary = GameSummary(
                id=game.id,
                title=game.title,
                cover_image_id=game.cover_image_id,
                release_date=game.release_date,
                main_story=None,  # Not available in current Game model
                main_extra=None,  # Not available in current Game model
                completionist=None,  # Not available in current Game model
            )

            # Get collection details if linked
            collection_snippet = None
            if playthrough.collection_id:
                collection = (
                    db.query(CollectionItem)
                    .filter(CollectionItem.id == playthrough.collection_id)
                    .first()
                )
                if collection:
                    collection_snippet = CollectionSnippet(
                        id=collection.id,
                        platform=collection.platform,
                        acquisition_type=collection.acquisition_type,
                        acquired_at=collection.acquired_at,
                        priority=collection.priority,
                        is_active=collection.is_active,
                    )

            backlog_item = BacklogItem(
                id=playthrough.id,
                game=game_summary,
                collection=collection_snippet,
                status="PLANNING",
                created_at=playthrough.created_at,
            )
            backlog_items.append(backlog_item)

        logger.info(
            f"Found {len(backlog_items)} backlog items for user {current_user.id}"
        )

        return BacklogResponse(
            items=backlog_items,
            total_count=len(backlog_items),
        )

    except Exception as e:
        logger.error(f"Error getting backlog for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve backlog")


@router.get("/playing", response_model=PlayingResponse)
async def get_playing(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlayingResponse:
    """Get user's currently playing games (playing status playthroughs)."""
    logger.info(f"Getting playing games for user {current_user.id}")

    # Build query for playing playthroughs
    query = (
        db.query(Playthrough)
        .filter(
            Playthrough.user_id == current_user.id,
            Playthrough.status == PlaythroughStatus.PLAYING,
        )
        .join(Game, Playthrough.game_id == Game.id)
    )

    # Apply platform filter if specified
    if platform is not None:
        query = query.filter(Playthrough.platform == platform)

    # Order by started_at descending (most recently started first)
    query = query.order_by(Playthrough.started_at.desc())

    try:
        # Execute query with proper joins
        results = query.all()

        # Convert to response format
        playing_items = []
        for playthrough in results:
            # Get the game from the join
            game = db.query(Game).filter(Game.id == playthrough.game_id).first()
            if not game:
                continue

            # Get game details
            game_summary = GameSummary(
                id=game.id,
                title=game.title,
                cover_image_id=game.cover_image_id,
                release_date=game.release_date,
                main_story=None,  # Not available in current Game model
                main_extra=None,  # Not available in current Game model
                completionist=None,  # Not available in current Game model
            )

            # Calculate last_played (use updated_at as a proxy for last activity)
            last_played = playthrough.updated_at

            playing_item = PlayingItem(
                id=playthrough.id,
                game=game_summary,
                status="PLAYING",
                platform=playthrough.platform,
                started_at=playthrough.started_at,
                play_time_hours=playthrough.play_time_hours,
                last_played=last_played,
            )
            playing_items.append(playing_item)

        logger.info(
            f"Found {len(playing_items)} playing items for user {current_user.id}"
        )

        return PlayingResponse(
            items=playing_items,
            total_count=len(playing_items),
        )

    except Exception as e:
        logger.error(f"Error getting playing games for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve playing games")


@router.get("/completed", response_model=CompletedResponse)
async def get_completed(
    year: Optional[int] = Query(None, description="Filter by completion year"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    min_rating: Optional[int] = Query(
        None, ge=1, le=10, description="Filter by minimum rating"
    ),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompletedResponse:
    """Get user's completed games (completed status playthroughs) with filters and statistics."""
    logger.info(f"Getting completed games for user {current_user.id}")

    # Build query for completed playthroughs
    query = (
        db.query(Playthrough)
        .filter(
            Playthrough.user_id == current_user.id,
            Playthrough.status == PlaythroughStatus.COMPLETED,
        )
        .join(Game, Playthrough.game_id == Game.id)
    )

    # Apply filters
    if year is not None:
        # Filter by completion year
        query = query.filter(func.extract("year", Playthrough.completed_at) == year)

    if platform is not None:
        query = query.filter(Playthrough.platform == platform)

    if min_rating is not None:
        query = query.filter(Playthrough.rating >= min_rating)

    # Order by completed_at descending (most recently completed first)
    query = query.order_by(Playthrough.completed_at.desc())

    try:
        # Execute query with proper joins
        results = query.all()

        # Convert to response format
        completed_items = []
        for playthrough in results:
            # Get the game from the join
            game = db.query(Game).filter(Game.id == playthrough.game_id).first()
            if not game:
                continue

            # Get game details
            game_summary = GameSummary(
                id=game.id,
                title=game.title,
                cover_image_id=game.cover_image_id,
                release_date=game.release_date,
                main_story=None,  # Not available in current Game model
                main_extra=None,  # Not available in current Game model
                completionist=None,  # Not available in current Game model
            )

            completed_item = CompletedItem(
                id=playthrough.id,
                game=game_summary,
                status="COMPLETED",
                platform=playthrough.platform,
                completed_at=playthrough.completed_at,
                play_time_hours=playthrough.play_time_hours,
                rating=playthrough.rating,
                playthrough_type=playthrough.playthrough_type,
            )
            completed_items.append(completed_item)

        # Calculate completion statistics
        completion_stats = {}
        if completed_items:
            completion_stats["total_completed"] = len(completed_items)

            # Calculate average rating (only for items with ratings)
            ratings = [
                item.rating for item in completed_items if item.rating is not None
            ]
            if ratings:
                completion_stats["average_rating"] = round(
                    sum(ratings) / len(ratings), 2
                )

            # Calculate total and average play time (only for items with play time)
            play_times = [
                item.play_time_hours
                for item in completed_items
                if item.play_time_hours is not None
            ]
            if play_times:
                total_time = sum(play_times)
                completion_stats["total_play_time"] = round(total_time, 2)
                completion_stats["average_play_time"] = round(
                    total_time / len(play_times), 2
                )
        else:
            completion_stats["total_completed"] = 0

        logger.info(
            f"Found {len(completed_items)} completed items for user {current_user.id}"
        )

        return CompletedResponse(
            items=completed_items,
            total_count=len(completed_items),
            completion_stats=completion_stats,
        )

    except Exception as e:
        logger.error(f"Error getting completed games for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve completed games"
        )


@router.get("/stats", response_model=PlaythroughStats)
async def get_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaythroughStats:
    """Get comprehensive playthrough statistics for the user."""
    logger.info(f"Getting playthrough stats for user {current_user.id}")

    try:
        # Get all user's playthroughs
        playthroughs = (
            db.query(Playthrough).filter(Playthrough.user_id == current_user.id).all()
        )

        total_playthroughs = len(playthroughs)

        # Calculate status breakdown
        by_status = {}
        for playthrough in playthroughs:
            status = (
                playthrough.status.value
                if hasattr(playthrough.status, "value")
                else playthrough.status
            )
            by_status[status] = by_status.get(status, 0) + 1

        # Calculate platform breakdown
        by_platform = {}
        for playthrough in playthroughs:
            platform = playthrough.platform
            by_platform[platform] = by_platform.get(platform, 0) + 1

        # Calculate completion statistics
        completed_playthroughs = [
            p
            for p in playthroughs
            if p.status in [PlaythroughStatus.COMPLETED, PlaythroughStatus.MASTERED]
        ]

        completion_stats = {}
        if total_playthroughs > 0:
            completion_rate = (len(completed_playthroughs) / total_playthroughs) * 100
            completion_stats["completion_rate"] = round(completion_rate, 2)
        else:
            completion_stats["completion_rate"] = 0.0

        # Calculate average rating for completed playthroughs with ratings
        completed_with_rating = [
            p for p in completed_playthroughs if p.rating is not None
        ]
        if completed_with_rating:
            avg_rating = sum(p.rating for p in completed_with_rating) / len(
                completed_with_rating
            )
            completion_stats["average_rating"] = round(avg_rating, 2)

        # Calculate total play time
        playthroughs_with_time = [
            p for p in playthroughs if p.play_time_hours is not None
        ]
        if playthroughs_with_time:
            total_time = sum(p.play_time_hours for p in playthroughs_with_time)
            completion_stats["total_play_time"] = round(total_time, 2)
            completion_stats["average_play_time"] = round(
                total_time / len(playthroughs_with_time), 2
            )

        # Calculate yearly stats (optional)
        yearly_stats = {}
        for playthrough in completed_playthroughs:
            if playthrough.completed_at:
                year = str(playthrough.completed_at.year)
                if year not in yearly_stats:
                    yearly_stats[year] = {"completed": 0, "total_time": 0.0}

                yearly_stats[year]["completed"] += 1
                if playthrough.play_time_hours:
                    yearly_stats[year]["total_time"] += playthrough.play_time_hours

        # Round yearly stats
        for year_data in yearly_stats.values():
            year_data["total_time"] = round(year_data["total_time"], 2)

        # Top genres placeholder (would require game genre data)
        # Since our current Game model doesn't have genre information,
        # we'll return None for now
        top_genres = None

        logger.info(
            f"Generated stats for user {current_user.id}: {total_playthroughs} playthroughs, "
            f"{len(completed_playthroughs)} completed"
        )

        return PlaythroughStats(
            total_playthroughs=total_playthroughs,
            by_status=by_status,
            by_platform=by_platform,
            completion_stats=completion_stats,
            yearly_stats=yearly_stats if yearly_stats else None,
            top_genres=top_genres,
        )

    except Exception as e:
        logger.error(f"Error getting playthrough stats for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve playthrough statistics"
        )


@router.get("/{playthrough_id}", response_model=PlaythroughDetail)
async def get_playthrough_by_id(
    playthrough_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaythroughDetail:
    """Get a playthrough by ID with full details including embedded game, collection, and milestones."""

    logger.info(f"User {current_user.id} requesting playthrough {playthrough_id}")

    # Query for the playthrough with joined game and collection data
    query = (
        select(Playthrough, Game, CollectionItem)
        .join(Game, Playthrough.game_id == Game.id)
        .outerjoin(CollectionItem, Playthrough.collection_id == CollectionItem.id)
        .where(
            and_(
                Playthrough.id == playthrough_id, Playthrough.user_id == current_user.id
            )
        )
    )

    result = db.execute(query).first()

    if not result:
        logger.warning(
            f"Playthrough {playthrough_id} not found for user {current_user.id}"
        )
        raise HTTPException(status_code=404, detail="Playthrough not found")

    playthrough, game, collection_item = result

    # Create game detail
    game_detail = GameDetail(
        id=game.id,
        title=game.title,
        cover_image_id=game.cover_image_id,
        release_date=game.release_date,
        main_story=getattr(game, "main_story", None),
        main_extra=getattr(game, "main_extra", None),
        completionist=getattr(game, "completionist", None),
        description=getattr(game, "description", None),
        igdb_id=getattr(game, "igdb_id", None),
        hltb_id=getattr(game, "hltb_id", None),
        steam_app_id=getattr(game, "steam_app_id", None),
    )

    # Create collection snippet if available
    collection_snippet = None
    if collection_item:
        collection_snippet = CollectionSnippet(
            id=collection_item.id,
            platform=collection_item.platform,
            acquisition_type=AcquisitionType(collection_item.acquisition_type),
            acquired_at=collection_item.acquired_at,
            priority=collection_item.priority,
            is_active=collection_item.is_active,
        )

    # For now, milestones are not implemented, so return empty list
    # TODO: Implement milestone retrieval when milestone system is added
    milestones = None

    # Create detailed playthrough response
    playthrough_detail = PlaythroughDetail(
        id=playthrough.id,
        user_id=playthrough.user_id,
        status=PlaythroughStatus(playthrough.status),
        platform=playthrough.platform,
        started_at=playthrough.started_at,
        completed_at=playthrough.completed_at,
        play_time_hours=playthrough.play_time_hours,
        playthrough_type=playthrough.playthrough_type,
        difficulty=playthrough.difficulty,
        rating=playthrough.rating,
        notes=playthrough.notes,
        created_at=playthrough.created_at,
        updated_at=playthrough.updated_at,
        game=game_detail,
        collection=collection_snippet,
        milestones=milestones,
    )

    logger.info(f"Retrieved playthrough {playthrough_id} for user {current_user.id}")
    return playthrough_detail


def _is_valid_status_transition(from_status: str, to_status: str) -> bool:
    """Check if the status transition is valid according to business rules."""
    # Define valid transitions
    valid_transitions = {
        "PLANNING": ["PLAYING", "DROPPED"],
        "PLAYING": ["COMPLETED", "DROPPED", "ON_HOLD", "MASTERED"],
        "ON_HOLD": ["PLAYING", "DROPPED", "COMPLETED", "MASTERED"],
        "COMPLETED": ["MASTERED"],  # Allow upgrade to mastered
        "DROPPED": ["PLANNING", "PLAYING"],  # Allow restart scenarios
        "MASTERED": [],  # Mastered is final state - no transitions allowed
    }

    # If same status, always allow (no-op)
    if from_status == to_status:
        return True

    return to_status in valid_transitions.get(from_status, [])


@router.put("/{playthrough_id}", response_model=PlaythroughResponse)
async def update_playthrough(
    playthrough_id: str,
    update_data: PlaythroughUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaythroughResponse:
    """Update a playthrough with business rules and valid status transitions."""

    logger.info(f"User {current_user.id} updating playthrough {playthrough_id}")

    # Find the existing playthrough
    existing_playthrough = (
        db.query(Playthrough)
        .filter(
            and_(
                Playthrough.id == playthrough_id, Playthrough.user_id == current_user.id
            )
        )
        .first()
    )

    if not existing_playthrough:
        logger.warning(
            f"Playthrough {playthrough_id} not found for user {current_user.id}"
        )
        raise HTTPException(status_code=404, detail="Playthrough not found")

    # Validate status transition if status is being changed
    if update_data.status and update_data.status.value != existing_playthrough.status:
        if not _is_valid_status_transition(
            existing_playthrough.status, update_data.status.value
        ):
            logger.warning(
                f"Invalid status transition from {existing_playthrough.status} to {update_data.status.value} "
                f"for playthrough {playthrough_id}"
            )
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status transition from {existing_playthrough.status} to {update_data.status.value}",
            )

    # Apply updates to the playthrough (only fields that were provided)
    update_dict = update_data.model_dump(exclude_unset=True, exclude_none=False)

    for field, value in update_dict.items():
        if field == "status" and value:
            setattr(existing_playthrough, field, value.value)
        elif value is not None:
            setattr(existing_playthrough, field, value)
        elif field in update_dict:  # Handle explicit None values for nullable fields
            setattr(existing_playthrough, field, None)

    # Apply timestamp business logic
    now = datetime.now(timezone.utc)

    # Set started_at when transitioning to PLAYING (if not already set)
    if (
        update_data.status
        and update_data.status.value == "PLAYING"
        and not existing_playthrough.started_at
    ):
        existing_playthrough.started_at = now
        logger.info(f"Set started_at for playthrough {playthrough_id}")

    # Set completed_at when transitioning to COMPLETED or MASTERED (if not already set)
    if (
        update_data.status
        and update_data.status.value in ["COMPLETED", "MASTERED"]
        and not existing_playthrough.completed_at
    ):
        existing_playthrough.completed_at = now
        logger.info(f"Set completed_at for playthrough {playthrough_id}")

    # Always update the updated_at timestamp
    existing_playthrough.updated_at = now

    try:
        db.commit()
        db.refresh(existing_playthrough)

        logger.info(f"Updated playthrough {playthrough_id} for user {current_user.id}")

        # Return the updated playthrough
        return PlaythroughResponse(
            id=existing_playthrough.id,
            user_id=existing_playthrough.user_id,
            game_id=existing_playthrough.game_id,
            collection_id=existing_playthrough.collection_id,
            status=PlaythroughStatus(existing_playthrough.status),
            platform=existing_playthrough.platform,
            started_at=existing_playthrough.started_at,
            completed_at=existing_playthrough.completed_at,
            play_time_hours=existing_playthrough.play_time_hours,
            playthrough_type=existing_playthrough.playthrough_type,
            difficulty=existing_playthrough.difficulty,
            rating=existing_playthrough.rating,
            notes=existing_playthrough.notes,
            created_at=existing_playthrough.created_at,
            updated_at=existing_playthrough.updated_at,
        )

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database error updating playthrough: {e}")
        raise HTTPException(status_code=500, detail="Failed to update playthrough")


@router.post("/{playthrough_id}/complete", response_model=PlaythroughResponse)
async def complete_playthrough(
    playthrough_id: str,
    completion_data: PlaythroughComplete,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaythroughResponse:
    """Mark playthrough as completed with final details."""

    logger.info(f"User {current_user.id} completing playthrough {playthrough_id}")

    # Find the existing playthrough
    existing_playthrough = (
        db.query(Playthrough)
        .filter(
            and_(
                Playthrough.id == playthrough_id, Playthrough.user_id == current_user.id
            )
        )
        .first()
    )

    if not existing_playthrough:
        logger.warning(
            f"Playthrough {playthrough_id} not found for user {current_user.id}"
        )
        raise HTTPException(status_code=404, detail="Playthrough not found")

    # Check if already completed
    if existing_playthrough.status in ["COMPLETED", "MASTERED", "DROPPED"]:
        logger.warning(
            f"Playthrough {playthrough_id} is already completed with status {existing_playthrough.status}"
        )
        raise HTTPException(
            status_code=409,
            detail=f"Playthrough is already completed with status {existing_playthrough.status}",
        )

    # Validate status transitions - completion is only allowed from PLAYING or ON_HOLD
    completion_status = completion_data.completion_type.value
    if not _is_valid_status_transition(existing_playthrough.status, completion_status):
        logger.warning(
            f"Invalid status transition from {existing_playthrough.status} to {completion_status} "
            f"for playthrough {playthrough_id}"
        )
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status transition from {existing_playthrough.status} to {completion_status}",
        )

    # Apply completion updates
    now = datetime.now(timezone.utc)

    # Update status
    existing_playthrough.status = completion_status

    # Set completed_at for COMPLETED/MASTERED/DROPPED (if provided or auto-set)
    if completion_status in ["COMPLETED", "MASTERED", "DROPPED"]:
        if completion_data.completed_at:
            existing_playthrough.completed_at = completion_data.completed_at
        elif not existing_playthrough.completed_at:
            existing_playthrough.completed_at = now
            logger.info(f"Auto-set completed_at for playthrough {playthrough_id}")

    # Update final play time if provided
    if completion_data.final_play_time_hours is not None:
        existing_playthrough.play_time_hours = completion_data.final_play_time_hours

    # Update rating if provided (but not for dropped playthroughs unless explicitly set)
    if completion_data.rating is not None:
        existing_playthrough.rating = completion_data.rating
    elif completion_status == "DROPPED" and completion_data.rating is None:
        # Don't require rating for dropped games
        pass

    # Update notes if provided
    if completion_data.final_notes is not None:
        existing_playthrough.notes = completion_data.final_notes

    # Always update the updated_at timestamp
    existing_playthrough.updated_at = now

    try:
        db.commit()
        db.refresh(existing_playthrough)

        logger.info(
            f"Completed playthrough {playthrough_id} with status {completion_status} for user {current_user.id}"
        )

        # Return the updated playthrough
        return PlaythroughResponse(
            id=existing_playthrough.id,
            user_id=existing_playthrough.user_id,
            game_id=existing_playthrough.game_id,
            collection_id=existing_playthrough.collection_id,
            status=PlaythroughStatus(existing_playthrough.status),
            platform=existing_playthrough.platform,
            started_at=existing_playthrough.started_at,
            completed_at=existing_playthrough.completed_at,
            play_time_hours=existing_playthrough.play_time_hours,
            playthrough_type=existing_playthrough.playthrough_type,
            difficulty=existing_playthrough.difficulty,
            rating=existing_playthrough.rating,
            notes=existing_playthrough.notes,
            created_at=existing_playthrough.created_at,
            updated_at=existing_playthrough.updated_at,
        )

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database error completing playthrough: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete playthrough")


@router.delete("/{playthrough_id}", response_model=PlaythroughDeleteResponse)
async def delete_playthrough(
    playthrough_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaythroughDeleteResponse:
    """Delete a playthrough record."""

    logger.info(f"User {current_user.id} deleting playthrough {playthrough_id}")

    # Find the existing playthrough
    existing_playthrough = (
        db.query(Playthrough)
        .filter(
            and_(
                Playthrough.id == playthrough_id, Playthrough.user_id == current_user.id
            )
        )
        .first()
    )

    if not existing_playthrough:
        logger.warning(
            f"Playthrough {playthrough_id} not found for user {current_user.id}"
        )
        raise HTTPException(status_code=404, detail="Playthrough not found")

    try:
        # Delete the playthrough from the database
        db.delete(existing_playthrough)
        db.commit()

        logger.info(f"Deleted playthrough {playthrough_id} for user {current_user.id}")

        return PlaythroughDeleteResponse(
            success=True, message="Playthrough deleted successfully"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Database error deleting playthrough: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete playthrough")


@router.post("/bulk", response_model=PlaythroughBulkResponse)
async def bulk_playthrough_operations(
    bulk_request: PlaythroughBulkRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PlaythroughBulkResponse:
    """Perform bulk operations on multiple playthroughs."""

    logger.info(
        f"User {current_user.id} performing bulk operation {bulk_request.action} "
        f"on {len(bulk_request.playthrough_ids)} playthroughs"
    )

    # Validate action-specific data
    if bulk_request.action == BulkAction.UPDATE_STATUS:
        if not bulk_request.data or "status" not in bulk_request.data:
            raise HTTPException(
                status_code=400, detail="Status is required for update_status action"
            )
    elif bulk_request.action == BulkAction.UPDATE_PLATFORM:
        if not bulk_request.data or "platform" not in bulk_request.data:
            raise HTTPException(
                status_code=400,
                detail="Platform is required for update_platform action",
            )
    elif bulk_request.action == BulkAction.ADD_TIME:
        if not bulk_request.data or "hours" not in bulk_request.data:
            raise HTTPException(
                status_code=400, detail="Hours is required for add_time action"
            )

    # Process each playthrough
    successful_items = []
    failed_items = []
    now = datetime.now(timezone.utc)

    for playthrough_id in bulk_request.playthrough_ids:
        try:
            # Find the playthrough
            existing_playthrough = (
                db.query(Playthrough)
                .filter(
                    and_(
                        Playthrough.id == playthrough_id,
                        Playthrough.user_id == current_user.id,
                    )
                )
                .first()
            )

            if not existing_playthrough:
                failed_items.append(
                    BulkFailedItem(id=playthrough_id, error="Playthrough not found")
                )
                continue

            # Perform the requested action
            if bulk_request.action == BulkAction.UPDATE_STATUS:
                new_status = bulk_request.data["status"]

                # Validate status transition
                if not _is_valid_status_transition(
                    existing_playthrough.status, new_status
                ):
                    failed_items.append(
                        BulkFailedItem(
                            id=playthrough_id,
                            error=f"Invalid status transition from {existing_playthrough.status} to {new_status}",
                        )
                    )
                    continue

                existing_playthrough.status = new_status

                # Apply timestamp logic like in update endpoint
                if new_status == "PLAYING" and not existing_playthrough.started_at:
                    existing_playthrough.started_at = now
                elif (
                    new_status in ["COMPLETED", "MASTERED"]
                    and not existing_playthrough.completed_at
                ):
                    existing_playthrough.completed_at = now

                successful_items.append(
                    BulkResultItem(id=playthrough_id, status=new_status)
                )

            elif bulk_request.action == BulkAction.UPDATE_PLATFORM:
                new_platform = bulk_request.data["platform"]
                existing_playthrough.platform = new_platform

                successful_items.append(
                    BulkResultItem(id=playthrough_id, platform=new_platform)
                )

            elif bulk_request.action == BulkAction.ADD_TIME:
                hours_to_add = bulk_request.data["hours"]
                current_time = existing_playthrough.play_time_hours or 0
                new_time = current_time + hours_to_add
                existing_playthrough.play_time_hours = new_time

                successful_items.append(
                    BulkResultItem(id=playthrough_id, play_time_hours=new_time)
                )

            elif bulk_request.action == BulkAction.DELETE:
                db.delete(existing_playthrough)

                successful_items.append(BulkResultItem(id=playthrough_id))

            # Update timestamp for all non-delete operations
            if bulk_request.action != BulkAction.DELETE:
                existing_playthrough.updated_at = now

        except Exception as e:
            logger.error(f"Error processing playthrough {playthrough_id}: {e}")
            failed_items.append(
                BulkFailedItem(id=playthrough_id, error=f"Processing error: {str(e)}")
            )

    # Commit all changes
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error in bulk operation: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete bulk operation")

    # Determine response status and format
    updated_count = len(successful_items)
    failed_count = len(failed_items)
    success = failed_count == 0

    logger.info(
        f"Bulk operation completed for user {current_user.id}: "
        f"{updated_count} successful, {failed_count} failed"
    )

    # Convert items to dicts for JSON serialization
    items_data = [item.model_dump() for item in successful_items]

    response_data = {
        "success": success,
        "updated_count": updated_count,
        "items": items_data,
    }

    if failed_count > 0:
        failed_items_data = [item.model_dump() for item in failed_items]
        response_data["failed_count"] = failed_count
        response_data["failed_items"] = failed_items_data

    # Return appropriate status code
    if success:
        return JSONResponse(content=response_data, status_code=200)
    else:
        return JSONResponse(
            content=response_data,
            status_code=207,  # Multi-Status
        )
