from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.auth import CurrentUser, get_current_user
from app.schemas import (
    BacklogResponse,
    CompletedResponse,
    PlaythroughBulkRequest,
    PlaythroughBulkResponse,
    PlaythroughComplete,
    PlaythroughDetail,
    PlaythroughListResponse,
    PlaythroughResponse,
    PlaythroughSortBy,
    PlaythroughStats,
    PlaythroughStatus,
    PlaythroughUpdate,
    PlaythroughCreate,
    PlayingResponse,
    SortOrder,
    PlaythroughDeleteResponse,
)
from app.services.deps import get_playthroughs_service
from app.services.errors import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    OperationError,
    ServiceValidationError,
)
from app.services.playthroughs_service import PlaythroughsService

router = APIRouter(prefix="/playthroughs", tags=["playthroughs"])


@router.get("", response_model=PlaythroughListResponse)
def list_playthroughs(
    playthrough_status: Optional[list[PlaythroughStatus]] = Query(
        None, alias="status", description="Filter by playthrough status"
    ),
    platform: Optional[list[str]] = Query(None, description="Filter by platforms"),
    rating_min: Optional[int] = Query(None, ge=1, le=10, description="Minimum rating (1-10)"),
    rating_max: Optional[int] = Query(None, ge=1, le=10, description="Maximum rating (1-10)"),
    play_time_min: Optional[float] = Query(None, ge=0, description="Minimum play time in hours"),
    play_time_max: Optional[float] = Query(None, ge=0, description="Maximum play time in hours"),
    difficulty: Optional[list[str]] = Query(None, description="Filter by difficulty settings"),
    playthrough_type: Optional[list[str]] = Query(None, description="Filter by playthrough type"),
    started_after: Optional[date] = Query(None, description="Started after date (YYYY-MM-DD)"),
    started_before: Optional[date] = Query(None, description="Started before date (YYYY-MM-DD)"),
    completed_after: Optional[date] = Query(None, description="Completed after date (YYYY-MM-DD)"),
    completed_before: Optional[date] = Query(None, description="Completed before date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search in game titles and notes"),
    sort_by: PlaythroughSortBy = Query(PlaythroughSortBy.UPDATED_AT, description="Sort field"),
    sort_order: SortOrder = Query(SortOrder.DESC, description="Sort direction"),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> PlaythroughListResponse:
    try:
        return service.list_playthroughs(
            current_user=current_user,
            status_=playthrough_status,
            platform=platform,
            rating_min=rating_min,
            rating_max=rating_max,
            play_time_min=play_time_min,
            play_time_max=play_time_max,
            difficulty=difficulty,
            playthrough_type=playthrough_type,
            started_after=started_after,
            started_before=started_before,
            completed_after=completed_after,
            completed_before=completed_before,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
        )
    except ServiceValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("", response_model=PlaythroughResponse, status_code=status.HTTP_201_CREATED)
def create_playthrough(
    playthrough_data: PlaythroughCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> PlaythroughResponse:
    try:
        return service.create_playthrough(current_user=current_user, playthrough_data=playthrough_data)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ServiceValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OperationError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/backlog", response_model=BacklogResponse)
def get_backlog(
    priority: Optional[int] = Query(None, ge=1, le=5, description="Filter by collection priority"),
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> BacklogResponse:
    return service.get_backlog(current_user=current_user, priority=priority)


@router.get("/playing", response_model=PlayingResponse)
def get_playing(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> PlayingResponse:
    return service.get_playing(current_user=current_user, platform=platform)


@router.get("/completed", response_model=CompletedResponse)
def get_completed(
    year: Optional[int] = Query(None, description="Filter by completion year"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    min_rating: Optional[int] = Query(None, ge=1, le=10, description="Filter by minimum rating"),
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> CompletedResponse:
    return service.get_completed(current_user=current_user, year=year, platform=platform, min_rating=min_rating)


@router.get("/stats", response_model=PlaythroughStats)
def get_stats(
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> PlaythroughStats:
    return service.get_stats(current_user=current_user)


@router.get("/{playthrough_id}", response_model=PlaythroughDetail)
def get_playthrough_by_id(
    playthrough_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> PlaythroughDetail:
    try:
        return service.get_playthrough_by_id(current_user=current_user, playthrough_id=playthrough_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.put("/{playthrough_id}", response_model=PlaythroughResponse)
def update_playthrough(
    playthrough_id: str,
    update_data: PlaythroughUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> PlaythroughResponse:
    try:
        return service.update_playthrough(
            current_user=current_user,
            playthrough_id=playthrough_id,
            update_data=update_data,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ServiceValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OperationError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{playthrough_id}/complete", response_model=PlaythroughResponse)
def complete_playthrough(
    playthrough_id: str,
    completion_data: PlaythroughComplete,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> PlaythroughResponse:
    try:
        return service.complete_playthrough(
            current_user=current_user,
            playthrough_id=playthrough_id,
            completion_data=completion_data,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except ServiceValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except OperationError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{playthrough_id}", response_model=PlaythroughDeleteResponse)
def delete_playthrough(
    playthrough_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> PlaythroughDeleteResponse:
    try:
        return service.delete_playthrough(current_user=current_user, playthrough_id=playthrough_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except OperationError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/bulk", response_model=PlaythroughBulkResponse)
def bulk_playthrough_operations(
    bulk_request: PlaythroughBulkRequest,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    service: PlaythroughsService = Depends(get_playthroughs_service),
) -> PlaythroughBulkResponse:
    try:
        data = service.bulk_playthrough_operations(current_user=current_user, bulk_request=bulk_request)
    except ServiceValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if data.get("success"):
        response.status_code = 200
    else:
        response.status_code = 207
    return data
