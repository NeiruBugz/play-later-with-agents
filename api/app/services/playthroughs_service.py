from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional
from uuid import uuid4

import logging
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.db_models import CollectionItem, Game, Playthrough
from app.schemas import (
    AcquisitionType,
    BacklogItem,
    BacklogResponse,
    BulkAction,
    BulkFailedItem,
    BulkResultItem,
    CompletedItem,
    CompletedResponse,
    GameDetail,
    GameSummary,
    PlaythroughBulkRequest,
    PlaythroughBulkResponse,
    PlaythroughComplete,
    PlaythroughDetail,
    PlaythroughListItem,
    PlaythroughListResponse,
    PlaythroughResponse,
    PlaythroughSortBy,
    PlaythroughStats,
    PlaythroughStatus,
    PlayingItem,
    PlayingResponse,
    SortOrder,
    CollectionSnippet,
    PlaythroughUpdate,
    PlaythroughCreate,
)

logger = logging.getLogger("app.service.playthroughs")


def list_playthroughs(
    *,
    db: Session,
    current_user: CurrentUser,
    status_: Optional[list[PlaythroughStatus]],
    platform: Optional[list[str]],
    rating_min: Optional[int],
    rating_max: Optional[int],
    play_time_min: Optional[float],
    play_time_max: Optional[float],
    difficulty: Optional[list[str]],
    playthrough_type: Optional[list[str]],
    started_after: Optional[date],
    started_before: Optional[date],
    completed_after: Optional[date],
    completed_before: Optional[date],
    search: Optional[str],
    sort_by: PlaythroughSortBy,
    sort_order: SortOrder,
    limit: int,
    offset: int,
) -> PlaythroughListResponse:
    if rating_min is not None and rating_max is not None and rating_min > rating_max:
        raise HTTPException(status_code=422, detail="rating_min must be <= rating_max")

    if (
        play_time_min is not None
        and play_time_max is not None
        and play_time_min > play_time_max
    ):
        raise HTTPException(
            status_code=422, detail="play_time_min must be <= play_time_max"
        )

    logger.info(
        f"User {current_user.id} requested playthroughs list with filters: "
        f"status={status_}, platform={platform}, rating_min={rating_min}, rating_max={rating_max}"
    )

    query = (
        select(Playthrough, Game, CollectionItem)
        .join(Game, Playthrough.game_id == Game.id)
        .outerjoin(CollectionItem, Playthrough.collection_id == CollectionItem.id)
        .where(Playthrough.user_id == current_user.id)
    )

    filters = []

    if status_:
        status_values = [s.value for s in status_]
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
        search_term = f"%{search}%"
        filters.append(
            or_(Game.title.ilike(search_term), Playthrough.notes.ilike(search_term))
        )

    if filters:
        query = query.where(and_(*filters))

    if sort_by.value == "title":
        sort_column = Game.title
    elif sort_by.value == "play_time_hours":
        sort_column = Playthrough.play_time_hours
    else:
        sort_column = getattr(Playthrough, sort_by.value)

    if sort_order == SortOrder.DESC:
        query = query.order_by(sort_column.desc().nulls_last())
    else:
        query = query.order_by(sort_column.asc().nulls_last())

    count_query = select(func.count()).select_from(query.subquery())
    total_count = db.scalar(count_query)

    query = query.offset(offset).limit(limit)
    results = db.execute(query).all()

    items: list[PlaythroughListItem] = []
    for playthrough, game, collection_item in results:
        game_summary = GameSummary(
            id=game.id,
            title=game.title,
            cover_image_id=game.cover_image_id,
            release_date=game.release_date,
            main_story=getattr(game, "main_story", None),
            main_extra=getattr(game, "main_extra", None),
            completionist=getattr(game, "completionist", None),
        )

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

        items.append(
            PlaythroughListItem(
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
        )

    return PlaythroughListResponse(
        items=items,
        total_count=total_count or 0,
        limit=limit,
        offset=offset,
        filters_applied={
            "status": [s.value for s in status_] if status_ else None,
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


def create_playthrough(
    *, db: Session, current_user: CurrentUser, playthrough_data: PlaythroughCreate
) -> PlaythroughResponse:
    logger.info(
        f"User {current_user.id} creating playthrough for game {playthrough_data.game_id}"
    )

    game = db.query(Game).filter(Game.id == playthrough_data.game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

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
            raise HTTPException(status_code=404, detail="Collection item not found")
        if collection_item.game_id != playthrough_data.game_id:
            raise HTTPException(
                status_code=400, detail="Collection item is for a different game"
            )

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
    except IntegrityError as e:  # noqa: BLE001
        db.rollback()
        logger.error(f"Database error creating playthrough: {e}")
        raise HTTPException(status_code=500, detail="Failed to create playthrough")


def get_backlog(
    *, db: Session, current_user: CurrentUser, priority: Optional[int]
) -> BacklogResponse:
    logger.info(f"Getting backlog for user {current_user.id}")
    query = (
        db.query(Playthrough)
        .filter(
            Playthrough.user_id == current_user.id,
            Playthrough.status == PlaythroughStatus.PLANNING,
        )
        .join(Game, Playthrough.game_id == Game.id)
        .outerjoin(CollectionItem, Playthrough.collection_id == CollectionItem.id)
    )
    if priority is not None:
        query = query.filter(CollectionItem.priority == priority)
    query = query.order_by(Playthrough.created_at.desc())

    try:
        results = query.all()
        backlog_items: list[BacklogItem] = []
        for playthrough in results:
            game = db.query(Game).filter(Game.id == playthrough.game_id).first()
            if not game:
                continue
            game_summary = GameSummary(
                id=game.id,
                title=game.title,
                cover_image_id=game.cover_image_id,
                release_date=game.release_date,
                main_story=None,
                main_extra=None,
                completionist=None,
            )
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
            backlog_items.append(
                BacklogItem(
                    id=playthrough.id,
                    game=game_summary,
                    collection=collection_snippet,
                    status="PLANNING",
                    created_at=playthrough.created_at,
                )
            )
        return BacklogResponse(items=backlog_items, total_count=len(backlog_items))
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting backlog for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve backlog")


def get_playing(
    *, db: Session, current_user: CurrentUser, platform: Optional[str]
) -> PlayingResponse:
    logger.info(f"Getting playing games for user {current_user.id}")
    query = (
        db.query(Playthrough)
        .filter(
            Playthrough.user_id == current_user.id,
            Playthrough.status == PlaythroughStatus.PLAYING,
        )
        .join(Game, Playthrough.game_id == Game.id)
    )
    if platform is not None:
        query = query.filter(Playthrough.platform == platform)
    query = query.order_by(Playthrough.started_at.desc())

    try:
        results = query.all()
        playing_items: list[PlayingItem] = []
        for playthrough in results:
            game = db.query(Game).filter(Game.id == playthrough.game_id).first()
            if not game:
                continue
            game_summary = GameSummary(
                id=game.id,
                title=game.title,
                cover_image_id=game.cover_image_id,
                release_date=game.release_date,
                main_story=None,
                main_extra=None,
                completionist=None,
            )
            last_played = playthrough.updated_at
            playing_items.append(
                PlayingItem(
                    id=playthrough.id,
                    game=game_summary,
                    status="PLAYING",
                    platform=playthrough.platform,
                    started_at=playthrough.started_at,
                    play_time_hours=playthrough.play_time_hours,
                    last_played=last_played,
                )
            )
        return PlayingResponse(items=playing_items, total_count=len(playing_items))
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting playing games for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve playing games")


def get_completed(
    *,
    db: Session,
    current_user: CurrentUser,
    year: Optional[int],
    platform: Optional[str],
    min_rating: Optional[int],
) -> CompletedResponse:
    logger.info(f"Getting completed games for user {current_user.id}")
    query = (
        db.query(Playthrough)
        .filter(
            Playthrough.user_id == current_user.id,
            Playthrough.status == PlaythroughStatus.COMPLETED,
        )
        .join(Game, Playthrough.game_id == Game.id)
    )
    if year is not None:
        query = query.filter(func.extract("year", Playthrough.completed_at) == year)
    if platform is not None:
        query = query.filter(Playthrough.platform == platform)
    if min_rating is not None:
        query = query.filter(Playthrough.rating >= min_rating)
    query = query.order_by(Playthrough.completed_at.desc())

    try:
        results = query.all()
        completed_items: list[CompletedItem] = []
        for playthrough in results:
            game = db.query(Game).filter(Game.id == playthrough.game_id).first()
            if not game:
                continue
            game_summary = GameSummary(
                id=game.id,
                title=game.title,
                cover_image_id=game.cover_image_id,
                release_date=game.release_date,
                main_story=None,
                main_extra=None,
                completionist=None,
            )
            completed_items.append(
                CompletedItem(
                    id=playthrough.id,
                    game=game_summary,
                    status="COMPLETED",
                    platform=playthrough.platform,
                    completed_at=playthrough.completed_at,
                    play_time_hours=playthrough.play_time_hours,
                    rating=playthrough.rating,
                    playthrough_type=playthrough.playthrough_type,
                )
            )

        completion_stats: dict[str, float | int] = {}
        if completed_items:
            completion_stats["total_completed"] = len(completed_items)
            ratings = [
                item.rating for item in completed_items if item.rating is not None
            ]
            if ratings:
                completion_stats["average_rating"] = round(
                    sum(ratings) / len(ratings), 2
                )
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

        return CompletedResponse(
            items=completed_items,
            total_count=len(completed_items),
            completion_stats=completion_stats,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting completed games for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve completed games"
        )


def get_stats(*, db: Session, current_user: CurrentUser) -> PlaythroughStats:
    logger.info(f"Getting playthrough stats for user {current_user.id}")
    try:
        playthroughs = (
            db.query(Playthrough).filter(Playthrough.user_id == current_user.id).all()
        )
        total_playthroughs = len(playthroughs)

        by_status: dict[str, int] = {}
        for playthrough in playthroughs:
            status_val = (
                playthrough.status.value
                if hasattr(playthrough.status, "value")
                else playthrough.status
            )
            by_status[status_val] = by_status.get(status_val, 0) + 1

        by_platform: dict[str, int] = {}
        for playthrough in playthroughs:
            platform = playthrough.platform
            by_platform[platform] = by_platform.get(platform, 0) + 1

        completed_playthroughs = [
            p
            for p in playthroughs
            if p.status in [PlaythroughStatus.COMPLETED, PlaythroughStatus.MASTERED]
        ]

        completion_stats: dict[str, float] = {}
        if total_playthroughs > 0:
            completion_rate = (len(completed_playthroughs) / total_playthroughs) * 100
            completion_stats["completion_rate"] = round(completion_rate, 2)
        else:
            completion_stats["completion_rate"] = 0.0

        completed_with_rating = [
            p for p in completed_playthroughs if p.rating is not None
        ]
        if completed_with_rating:
            avg_rating = sum(p.rating for p in completed_with_rating) / len(
                completed_with_rating
            )  # type: ignore[arg-type]
            completion_stats["average_rating"] = round(avg_rating, 2)

        playthroughs_with_time = [
            p for p in playthroughs if p.play_time_hours is not None
        ]
        if playthroughs_with_time:
            total_time = sum(p.play_time_hours for p in playthroughs_with_time)  # type: ignore[arg-type]
            completion_stats["total_play_time"] = round(total_time, 2)
            completion_stats["average_play_time"] = round(
                total_time / len(playthroughs_with_time), 2
            )

        yearly_stats: dict[str, dict[str, float | int]] = {}
        for playthrough in completed_playthroughs:
            if playthrough.completed_at:
                year = str(playthrough.completed_at.year)
                if year not in yearly_stats:
                    yearly_stats[year] = {"completed": 0, "total_time": 0.0}
                yearly_stats[year]["completed"] += 1
                if playthrough.play_time_hours:
                    yearly_stats[year]["total_time"] += playthrough.play_time_hours
        for year_data in yearly_stats.values():
            year_data["total_time"] = round(year_data["total_time"], 2)

        top_genres = None

        return PlaythroughStats(
            total_playthroughs=total_playthroughs,
            by_status=by_status,
            by_platform=by_platform,
            completion_stats=completion_stats,
            yearly_stats=yearly_stats if yearly_stats else None,
            top_genres=top_genres,
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error getting playthrough stats for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve playthrough statistics"
        )


def get_playthrough_by_id(
    *, db: Session, current_user: CurrentUser, playthrough_id: str
) -> PlaythroughDetail:
    logger.info(f"User {current_user.id} requesting playthrough {playthrough_id}")
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
        raise HTTPException(status_code=404, detail="Playthrough not found")

    playthrough, game, collection_item = result

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

    milestones = None

    return PlaythroughDetail(
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


def _is_valid_status_transition(from_status: str, to_status: str) -> bool:
    valid_transitions = {
        "PLANNING": ["PLAYING", "DROPPED"],
        "PLAYING": ["COMPLETED", "DROPPED", "ON_HOLD", "MASTERED"],
        "ON_HOLD": ["PLAYING", "DROPPED", "COMPLETED", "MASTERED"],
        "COMPLETED": ["MASTERED"],
        "DROPPED": ["PLANNING", "PLAYING"],
        "MASTERED": [],
    }
    if from_status == to_status:
        return True
    return to_status in valid_transitions.get(from_status, [])


def update_playthrough(
    *,
    db: Session,
    current_user: CurrentUser,
    playthrough_id: str,
    update_data: PlaythroughUpdate,
) -> PlaythroughResponse:
    logger.info(f"User {current_user.id} updating playthrough {playthrough_id}")
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
        raise HTTPException(status_code=404, detail="Playthrough not found")

    if update_data.status and update_data.status.value != existing_playthrough.status:
        if not _is_valid_status_transition(
            existing_playthrough.status, update_data.status.value
        ):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status transition from {existing_playthrough.status} to {update_data.status.value}",
            )

    update_dict = update_data.model_dump(exclude_unset=True, exclude_none=False)
    for field, value in update_dict.items():
        if field == "status" and value:
            setattr(existing_playthrough, field, value.value)
        elif value is not None:
            setattr(existing_playthrough, field, value)
        elif field in update_dict:
            setattr(existing_playthrough, field, None)

    now = datetime.now(timezone.utc)
    if (
        update_data.status
        and update_data.status.value == "PLAYING"
        and not existing_playthrough.started_at
    ):
        existing_playthrough.started_at = now
    if (
        update_data.status
        and update_data.status.value in ["COMPLETED", "MASTERED"]
        and not existing_playthrough.completed_at
    ):
        existing_playthrough.completed_at = now
    existing_playthrough.updated_at = now

    try:
        db.commit()
        db.refresh(existing_playthrough)
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
    except IntegrityError as e:  # noqa: BLE001
        db.rollback()
        logger.error(f"Database error updating playthrough: {e}")
        raise HTTPException(status_code=500, detail="Failed to update playthrough")


def complete_playthrough(
    *,
    db: Session,
    current_user: CurrentUser,
    playthrough_id: str,
    completion_data: PlaythroughComplete,
) -> PlaythroughResponse:
    logger.info(f"User {current_user.id} completing playthrough {playthrough_id}")
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
        raise HTTPException(status_code=404, detail="Playthrough not found")

    if existing_playthrough.status in ["COMPLETED", "MASTERED", "DROPPED"]:
        raise HTTPException(
            status_code=409,
            detail=f"Playthrough is already completed with status {existing_playthrough.status}",
        )

    completion_status = completion_data.completion_type.value
    if not _is_valid_status_transition(existing_playthrough.status, completion_status):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status transition from {existing_playthrough.status} to {completion_status}",
        )

    now = datetime.now(timezone.utc)
    existing_playthrough.status = completion_status
    if completion_status in ["COMPLETED", "MASTERED", "DROPPED"]:
        if completion_data.completed_at:
            existing_playthrough.completed_at = completion_data.completed_at
        elif not existing_playthrough.completed_at:
            existing_playthrough.completed_at = now
    if completion_data.final_play_time_hours is not None:
        existing_playthrough.play_time_hours = completion_data.final_play_time_hours
    if completion_data.rating is not None:
        existing_playthrough.rating = completion_data.rating
    if completion_data.final_notes is not None:
        existing_playthrough.notes = completion_data.final_notes
    existing_playthrough.updated_at = now

    try:
        db.commit()
        db.refresh(existing_playthrough)
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
    except IntegrityError as e:  # noqa: BLE001
        db.rollback()
        logger.error(f"Database error completing playthrough: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete playthrough")


def delete_playthrough(*, db: Session, current_user: CurrentUser, playthrough_id: str):
    logger.info(f"User {current_user.id} deleting playthrough {playthrough_id}")
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
        raise HTTPException(status_code=404, detail="Playthrough not found")
    try:
        db.delete(existing_playthrough)
        db.commit()
        from app.schemas import (
            PlaythroughDeleteResponse,
        )  # import here to avoid circulars in type hints

        return PlaythroughDeleteResponse(
            success=True, message="Playthrough deleted successfully"
        )
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logger.error(f"Database error deleting playthrough: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete playthrough")


def bulk_playthrough_operations(
    *, db: Session, current_user: CurrentUser, bulk_request: PlaythroughBulkRequest
):
    logger.info(
        f"User {current_user.id} performing bulk operation {bulk_request.action} on {len(bulk_request.playthrough_ids)} playthroughs"
    )

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
    elif bulk_request.action == BulkAction.DELETE:
        # No payload required
        pass
    else:
        # Invalid/unsupported action
        raise HTTPException(status_code=422, detail="Invalid action")

    successful_items: list[BulkResultItem] = []
    failed_items: list[BulkFailedItem] = []
    now = datetime.now(timezone.utc)

    for playthrough_id in bulk_request.playthrough_ids:
        try:
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

            if bulk_request.action == BulkAction.UPDATE_STATUS:
                new_status = bulk_request.data["status"]  # type: ignore[index]
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
                if new_status == "PLAYING" and not existing_playthrough.started_at:
                    existing_playthrough.started_at = now
                elif (
                    new_status in ["COMPLETED", "MASTERED"]
                    and not existing_playthrough.completed_at
                ):
                    existing_playthrough.completed_at = now
                existing_playthrough.updated_at = now
                db.commit()
                db.refresh(existing_playthrough)
                successful_items.append(
                    BulkResultItem(
                        id=existing_playthrough.id,
                        status=existing_playthrough.status,
                    )
                )

            elif bulk_request.action == BulkAction.UPDATE_PLATFORM:
                platform_val = bulk_request.data["platform"]  # type: ignore[index]
                existing_playthrough.platform = platform_val
                existing_playthrough.updated_at = now
                db.commit()
                db.refresh(existing_playthrough)
                successful_items.append(
                    BulkResultItem(
                        id=existing_playthrough.id,
                        platform=existing_playthrough.platform,
                    )
                )

            elif bulk_request.action == BulkAction.ADD_TIME:
                hours = bulk_request.data["hours"]  # type: ignore[index]
                try:
                    hours_val = float(hours)
                except Exception:  # noqa: BLE001
                    failed_items.append(
                        BulkFailedItem(id=playthrough_id, error="Invalid hours value")
                    )
                    continue
                if hours_val <= 0:
                    failed_items.append(
                        BulkFailedItem(
                            id=playthrough_id, error="Hours must be positive"
                        )
                    )
                    continue
                existing_playthrough.play_time_hours = (
                    existing_playthrough.play_time_hours or 0
                ) + hours_val
                existing_playthrough.updated_at = now
                db.commit()
                db.refresh(existing_playthrough)
                successful_items.append(
                    BulkResultItem(
                        id=existing_playthrough.id,
                        play_time_hours=existing_playthrough.play_time_hours,
                    )
                )

            elif bulk_request.action == BulkAction.DELETE:
                db.delete(existing_playthrough)
                db.commit()
                successful_items.append(BulkResultItem(id=playthrough_id))
        except Exception as e:  # noqa: BLE001
            db.rollback()
            failed_items.append(BulkFailedItem(id=playthrough_id, error=str(e)))

    updated_count = len(successful_items)
    failed_count = len(failed_items)
    success = failed_count == 0

    items_data = [item.model_dump() for item in successful_items]
    response_data: dict[str, object] = {
        "success": success,
        "updated_count": updated_count,
        "items": items_data,
    }
    if failed_count > 0:
        failed_items_data = [item.model_dump() for item in failed_items]
        response_data["failed_count"] = failed_count
        response_data["failed_items"] = failed_items_data

    if success:
        return JSONResponse(content=response_data, status_code=200)
    else:
        return JSONResponse(content=response_data, status_code=207)
