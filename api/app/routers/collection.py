from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException, Response, status

from app.auth import CurrentUser, get_current_user
from app.schemas import (
    CollectionListResponse,
    CollectionItemExpanded,
    CollectionItemCreate,
    CollectionItemUpdate,
    CollectionSortBy,
    AcquisitionType,
    BulkCollectionRequest,
    BulkCollectionResponse,
    BulkCollectionResult,
    BulkCollectionAction,
    CollectionStats,
)

import logging
from app.services.deps import get_collection_service
from app.services.collection_service import CollectionService
from app.services.errors import (
    NotFoundError,
    ConflictError,
    ValidationError,
    BadRequestError,
)

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
    service: CollectionService = Depends(get_collection_service),
) -> CollectionListResponse:
    """Get user's game collection with filtering, sorting, and pagination."""
    try:
        return service.list_collection(
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
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/stats", response_model=CollectionStats)
async def get_collection_stats(
    current_user: CurrentUser = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
) -> CollectionStats:
    """Get user's collection statistics and insights."""
    return service.get_collection_stats(current_user=current_user)


@router.post(
    "", response_model=CollectionItemExpanded, status_code=status.HTTP_201_CREATED
)
async def create_collection_item(
    item_data: CollectionItemCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
) -> CollectionItemExpanded:
    """Create a new collection item for the authenticated user."""
    try:
        return service.create_collection_item(
            current_user=current_user, item_data=item_data
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{collection_id}", response_model=CollectionItemExpanded)
async def get_collection_item(
    collection_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
) -> CollectionItemExpanded:
    """Get a collection item by ID for the authenticated user."""
    try:
        return service.get_collection_item(
            current_user=current_user, collection_id=collection_id
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{collection_id}", response_model=CollectionItemExpanded)
async def update_collection_item(
    collection_id: str,
    update_data: CollectionItemUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
) -> CollectionItemExpanded:
    """Update mutable fields of a collection item for the authenticated user."""
    try:
        return service.update_collection_item(
            current_user=current_user,
            collection_id=collection_id,
            update_data=update_data,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{collection_id}")
async def delete_collection_item(
    collection_id: str,
    hard_delete: bool = Query(False, description="Permanently delete the item"),
    current_user: CurrentUser = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
) -> dict:
    """Delete a collection item (soft delete by default, hard delete with safeguards)."""
    try:
        return service.delete_collection_item(
            current_user=current_user,
            collection_id=collection_id,
            hard_delete=hard_delete,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/bulk", response_model=BulkCollectionResponse)
async def bulk_collection_operations(
    request: BulkCollectionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    service: CollectionService = Depends(get_collection_service),
) -> BulkCollectionResponse:
    """Perform bulk operations on multiple collection items."""
    try:
        response = service.bulk_collection_operations(
            current_user=current_user, request=request
        )
    except BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not response.success:
        return Response(
            content=response.model_dump_json(),
            status_code=207,
            headers={"content-type": "application/json"},
        )
    return response
