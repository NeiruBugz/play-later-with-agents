from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import logging
from fastapi import HTTPException, Response, status
from sqlalchemy import and_, or_, desc, asc, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.db_models import CollectionItem, Game, Playthrough
from app.schemas import (
    AcquisitionType,
    BulkCollectionAction,
    BulkCollectionRequest,
    BulkCollectionResponse,
    BulkCollectionResult,
    CollectionItemCreate,
    CollectionItemExpanded,
    CollectionItemUpdate,
    CollectionListResponse,
    CollectionSortBy,
    CollectionStats,
    GameDetail,
)

logger = logging.getLogger("app.service.collection")


def list_collection(
    *,
    db: Session,
    current_user: CurrentUser,
    platform: Optional[str],
    acquisition_type: Optional[AcquisitionType],
    priority: Optional[int],
    is_active: Optional[bool],
    search: Optional[str],
    sort_by: CollectionSortBy,
    sort_order: str,
    limit: int,
    offset: int,
) -> CollectionListResponse:
    logger.info(
        f"User {current_user.id} requested collection list with filters: {{'platform': '{platform}', 'acquisition_type': '{acquisition_type}', 'priority': {priority}, 'is_active': {is_active}, 'search': '{search}'}}"
    )

    query = (
        select(CollectionItem, Game)
        .join(Game, CollectionItem.game_id == Game.id)
        .where(CollectionItem.user_id == current_user.id)
    )

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
        search_term = f"%{search}%"
        filters.append(
            or_(Game.title.ilike(search_term), CollectionItem.notes.ilike(search_term))
        )

    if filters:
        query = query.where(and_(*filters))

    if sort_by.value == "title":
        sort_column = Game.title
    else:
        sort_column = getattr(CollectionItem, sort_by.value)

    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    count_query = select(func.count()).select_from(query.subquery())
    total_count = db.scalar(count_query)

    query = query.offset(offset).limit(limit)
    results = db.execute(query).all()

    items: list[CollectionItemExpanded] = []
    for collection_item, game in results:
        playthroughs_query = select(Playthrough).where(
            Playthrough.collection_id == collection_item.id
        )
        playthroughs = db.scalars(playthroughs_query).all()

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

        items.append(
            CollectionItemExpanded(
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
        )

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


def get_collection_stats(*, db: Session, current_user: CurrentUser) -> CollectionStats:
    base_query = (
        select(CollectionItem, Game)
        .join(Game, CollectionItem.game_id == Game.id)
        .where(CollectionItem.user_id == current_user.id)
    )

    results = db.execute(base_query).all()
    collection_items = [item for item, _ in results]

    if not collection_items:
        return CollectionStats(
            total_games=0,
            by_platform={},
            by_acquisition_type={},
            by_priority={},
            value_estimate=None,
            recent_additions=[],
        )

    total_games = len(collection_items)

    by_platform: dict[str, int] = {}
    for item in collection_items:
        platform = item.platform
        by_platform[platform] = by_platform.get(platform, 0) + 1

    by_acquisition_type: dict[str, int] = {}
    for item in collection_items:
        acq_type = item.acquisition_type
        by_acquisition_type[acq_type] = by_acquisition_type.get(acq_type, 0) + 1

    by_priority: dict[str, int] = {}
    for item in collection_items:
        priority = str(item.priority) if item.priority is not None else "null"
        by_priority[priority] = by_priority.get(priority, 0) + 1

    digital_items = sum(
        1 for item in collection_items if item.acquisition_type == "DIGITAL"
    )
    physical_items = sum(
        1 for item in collection_items if item.acquisition_type == "PHYSICAL"
    )

    value_estimate = {
        "digital": round(digital_items * 45.99, 2),
        "physical": round(physical_items * 59.99, 2),
        "currency": "USD",
    }

    recent_additions = []
    items_with_acquired_at = [
        (item, game) for item, game in results if item.acquired_at is not None
    ]
    items_with_acquired_at.sort(key=lambda x: x[0].acquired_at, reverse=True)

    for item, game in items_with_acquired_at[:5]:
        recent_additions.append(
            {
                "game": {"title": game.title, "cover_image_id": game.cover_image_id},
                "platform": item.platform,
                "acquired_at": item.acquired_at.isoformat(),
            }
        )

    return CollectionStats(
        total_games=total_games,
        by_platform=by_platform,
        by_acquisition_type=by_acquisition_type,
        by_priority=by_priority,
        value_estimate=value_estimate,
        recent_additions=recent_additions,
    )


def create_collection_item(
    *, db: Session, current_user: CurrentUser, item_data: CollectionItemCreate
) -> CollectionItemExpanded:
    game_query = select(Game).where(Game.id == item_data.game_id)
    game = db.scalar(game_query)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )

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

    playthroughs_query = select(Playthrough).where(
        Playthrough.collection_id == collection_item.id
    )
    playthroughs = db.scalars(playthroughs_query).all()

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


def get_collection_item(
    *, db: Session, current_user: CurrentUser, collection_id: str
) -> CollectionItemExpanded:
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

    playthroughs_query = select(Playthrough).where(
        Playthrough.collection_id == collection_item.id
    )
    playthroughs = db.scalars(playthroughs_query).all()

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


def update_collection_item(
    *,
    db: Session,
    current_user: CurrentUser,
    collection_id: str,
    update_data: CollectionItemUpdate,
) -> CollectionItemExpanded:
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

    update_values: dict[str, object] = {}
    if update_data.platform is not None:
        update_values["platform"] = update_data.platform
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

    if update_values:
        update_values["updated_at"] = datetime.now(timezone.utc)
        for field, value in update_values.items():
            setattr(collection_item, field, value)
        db.commit()
        db.refresh(collection_item)

    playthroughs_query = select(Playthrough).where(
        Playthrough.collection_id == collection_item.id
    )
    playthroughs = db.scalars(playthroughs_query).all()

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


def delete_collection_item(
    *, db: Session, current_user: CurrentUser, collection_id: str, hard_delete: bool
) -> dict:
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
        playthroughs_query = select(func.count(Playthrough.id)).where(
            Playthrough.collection_id == collection_item.id
        )
        playthrough_count = db.scalar(playthroughs_query)
        if playthrough_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot hard delete: collection item has associated playthroughs",
            )
        db.delete(collection_item)
        db.commit()
        return {"message": "Collection item permanently deleted", "id": collection_id}

    collection_item.is_active = False
    collection_item.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(collection_item)
    return {
        "message": "Collection item soft deleted",
        "id": collection_id,
        "is_active": collection_item.is_active,
    }


def bulk_collection_operations(
    *, db: Session, current_user: CurrentUser, request: BulkCollectionRequest
) -> BulkCollectionResponse | Response:
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

    results: list[BulkCollectionResult] = []
    updated_count = 0

    for collection_id in request.collection_ids:
        try:
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

            updated_data: dict[str, object] = {}

            if request.action == BulkCollectionAction.UPDATE_PRIORITY:
                priority = request.data["priority"]  # type: ignore[index]
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
                platform = request.data["platform"]  # type: ignore[index]
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

            collection_item.updated_at = datetime.now(timezone.utc)
            updated_data["updated_at"] = collection_item.updated_at.isoformat()

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

        except Exception as e:  # noqa: BLE001
            db.rollback()
            results.append(
                BulkCollectionResult(id=collection_id, success=False, error=str(e))
            )

    total_count = len(request.collection_ids)
    all_successful = updated_count == total_count

    response = BulkCollectionResponse(
        success=all_successful,
        updated_count=updated_count,
        total_count=total_count,
        results=results,
    )

    if all_successful:
        return response

    content = response.model_dump_json()
    return Response(
        content=content, status_code=207, headers={"content-type": "application/json"}
    )
