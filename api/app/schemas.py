from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ===== Enums =====


class AcquisitionType(str, Enum):
    PHYSICAL = "PHYSICAL"
    DIGITAL = "DIGITAL"
    SUBSCRIPTION = "SUBSCRIPTION"
    BORROWED = "BORROWED"
    RENTAL = "RENTAL"


class CollectionSortBy(str, Enum):
    TITLE = "title"
    ACQUIRED_AT = "acquired_at"
    PRIORITY = "priority"
    PLATFORM = "platform"
    UPDATED_AT = "updated_at"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class PlaythroughStatus(str, Enum):
    PLANNING = "PLANNING"
    PLAYING = "PLAYING"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"
    ON_HOLD = "ON_HOLD"
    MASTERED = "MASTERED"


class PlaythroughSortBy(str, Enum):
    TITLE = "title"
    STATUS = "status"
    STARTED_AT = "started_at"
    COMPLETED_AT = "completed_at"
    UPDATED_AT = "updated_at"
    RATING = "rating"
    PLAY_TIME = "play_time_hours"
    PLATFORM = "platform"


# ===== Core DTOs =====


class GameSummary(BaseModel):
    id: str
    title: str
    cover_image_id: Optional[str] = None
    release_date: Optional[date] = None
    main_story: Optional[int] = None
    main_extra: Optional[int] = None
    completionist: Optional[int] = None


class GameDetail(GameSummary):
    description: Optional[str] = None
    igdb_id: Optional[int] = None
    hltb_id: Optional[int] = None
    steam_app_id: Optional[int] = None


class CollectionSnippet(BaseModel):
    id: str
    platform: str
    acquisition_type: AcquisitionType
    acquired_at: Optional[datetime] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    is_active: bool = True


class CollectionItemCreate(BaseModel):
    game_id: str = Field(..., description="Game ID to add to collection")
    platform: str = Field(..., description="Gaming platform")
    acquisition_type: AcquisitionType = Field(
        ..., description="How the game was acquired"
    )
    acquired_at: Optional[datetime] = Field(
        None, description="When the game was acquired"
    )
    priority: Optional[int] = Field(
        default=None, ge=1, le=5, description="Priority level (1-5)"
    )
    notes: Optional[str] = Field(None, description="Personal notes about the game")


class CollectionItemUpdate(BaseModel):
    acquisition_type: Optional[AcquisitionType] = Field(
        None, description="How the game was acquired"
    )
    acquired_at: Optional[datetime] = Field(
        None, description="When the game was acquired"
    )
    priority: Optional[int] = Field(
        None, ge=1, le=5, description="Priority level (1-5)"
    )
    is_active: Optional[bool] = Field(None, description="Whether the item is active")
    notes: Optional[str] = Field(None, description="Personal notes about the game")


class CollectionItem(BaseModel):
    id: str
    user_id: str
    game_id: str
    platform: str
    acquisition_type: AcquisitionType
    acquired_at: Optional[datetime] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    is_active: bool = True
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CollectionItemExpanded(BaseModel):
    id: str
    user_id: str
    game: GameDetail
    platform: str
    acquisition_type: AcquisitionType
    acquired_at: Optional[datetime] = None
    priority: Optional[int] = Field(default=None, ge=1, le=5)
    is_active: bool = True
    notes: Optional[str] = None
    playthroughs: list[dict] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CollectionListResponse(BaseModel):
    items: list[CollectionItemExpanded | dict]
    total_count: int
    limit: int
    offset: int
    filters_applied: Optional[dict] = None


class CollectionStats(BaseModel):
    total_games: int
    by_platform: dict[str, int]
    by_acquisition_type: dict[str, int]
    by_priority: dict[str, int | None]
    value_estimate: Optional[dict[str, int | float | str]] = None
    recent_additions: Optional[list[dict]] = None


class PlaythroughCreate(BaseModel):
    game_id: str = Field(..., description="Game ID for the playthrough")
    collection_id: Optional[str] = Field(
        None, description="Optional collection item ID"
    )
    status: PlaythroughStatus = Field(..., description="Playthrough status")
    platform: str = Field(..., description="Gaming platform")
    started_at: Optional[datetime] = Field(
        None, description="When the playthrough was started"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When the playthrough was completed"
    )
    play_time_hours: Optional[float] = Field(
        default=None, ge=0, description="Play time in hours"
    )
    playthrough_type: Optional[str] = Field(
        None, description="Type of playthrough (e.g., 'First Run', '100% Completion')"
    )
    difficulty: Optional[str] = Field(None, description="Difficulty level")
    rating: Optional[int] = Field(
        default=None, ge=1, le=10, description="Personal rating (1-10)"
    )
    notes: Optional[str] = Field(
        None, description="Personal notes about the playthrough"
    )


class PlaythroughUpdate(BaseModel):
    status: Optional[PlaythroughStatus] = Field(None, description="Playthrough status")
    platform: Optional[str] = Field(None, description="Gaming platform")
    started_at: Optional[datetime] = Field(
        None, description="When the playthrough was started"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When the playthrough was completed"
    )
    play_time_hours: Optional[float] = Field(
        default=None, ge=0, description="Play time in hours"
    )
    playthrough_type: Optional[str] = Field(
        None, description="Type of playthrough (e.g., 'First Run', '100% Completion')"
    )
    difficulty: Optional[str] = Field(None, description="Difficulty level")
    rating: Optional[int] = Field(
        default=None, ge=1, le=10, description="Personal rating (1-10)"
    )
    notes: Optional[str] = Field(
        None, description="Personal notes about the playthrough"
    )


class PlaythroughComplete(BaseModel):
    completion_type: CompletionType = Field(..., description="Type of completion")
    completed_at: Optional[datetime] = Field(
        None,
        description="When the playthrough was completed (auto-set if not provided)",
    )
    final_play_time_hours: Optional[float] = Field(
        default=None, ge=0, description="Final play time in hours"
    )
    rating: Optional[int] = Field(
        default=None, ge=1, le=10, description="Final rating (1-10)"
    )
    final_notes: Optional[str] = Field(
        None, description="Final notes about the playthrough"
    )


class PlaythroughDeleteResponse(BaseModel):
    success: bool = Field(..., description="Whether the deletion was successful")
    message: str = Field(..., description="Success message")


class BulkAction(str, Enum):
    UPDATE_STATUS = "update_status"
    UPDATE_PLATFORM = "update_platform"
    ADD_TIME = "add_time"
    DELETE = "delete"


class PlaythroughBulkRequest(BaseModel):
    action: BulkAction = Field(..., description="Bulk action to perform")
    playthrough_ids: list[str] = Field(
        ..., min_length=1, description="List of playthrough IDs"
    )
    data: Optional[dict] = Field(None, description="Action-specific data")


class BulkResultItem(BaseModel):
    id: str = Field(..., description="Playthrough ID")
    status: Optional[str] = Field(None, description="Updated status")
    platform: Optional[str] = Field(None, description="Updated platform")
    play_time_hours: Optional[float] = Field(None, description="Updated play time")


class BulkFailedItem(BaseModel):
    id: str = Field(..., description="Playthrough ID that failed")
    error: str = Field(..., description="Error message")


class PlaythroughBulkResponse(BaseModel):
    success: bool = Field(..., description="Whether the operation was fully successful")
    updated_count: int = Field(
        ..., description="Number of playthroughs successfully updated"
    )
    failed_count: Optional[int] = Field(
        None, description="Number of playthroughs that failed (for partial success)"
    )
    items: list[BulkResultItem] = Field(..., description="Successfully updated items")
    failed_items: Optional[list[BulkFailedItem]] = Field(
        None, description="Failed items (for partial success)"
    )


class PlaythroughResponse(BaseModel):
    id: str
    user_id: str
    game_id: str
    collection_id: Optional[str] = None
    status: PlaythroughStatus
    platform: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    play_time_hours: Optional[float] = Field(default=None, ge=0)
    playthrough_type: Optional[str] = None
    difficulty: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PlaythroughBase(BaseModel):
    id: str
    user_id: str
    status: PlaythroughStatus
    platform: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    play_time_hours: Optional[float] = Field(default=None, ge=0)
    playthrough_type: Optional[str] = None
    difficulty: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=10)
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PlaythroughListItem(PlaythroughBase):
    game: GameSummary
    collection: Optional[CollectionSnippet] = None


class Milestone(BaseModel):
    name: str
    achieved_at: datetime


class PlaythroughDetail(PlaythroughBase):
    game: GameDetail
    collection: Optional[CollectionSnippet] = None
    milestones: Optional[list[Milestone]] = None


class PlaythroughListResponse(BaseModel):
    items: list[PlaythroughListItem]
    total_count: int
    limit: int
    offset: int
    filters_applied: Optional[dict] = None


class CompletionType(str, Enum):
    COMPLETED = "COMPLETED"
    MASTERED = "MASTERED"
    DROPPED = "DROPPED"
    ON_HOLD = "ON_HOLD"


class PlaythroughStats(BaseModel):
    total_playthroughs: int
    by_status: dict[str, int]
    by_platform: dict[str, int]
    completion_stats: dict[str, float | int]
    yearly_stats: Optional[dict[str, dict[str, float | int]]] = None
    top_genres: Optional[list[dict[str, float | int | str]]] = None


# Convenience endpoint shapes


class BacklogItem(BaseModel):
    id: str
    game: GameSummary
    collection: Optional[CollectionSnippet] = None
    status: Literal["PLANNING"] = "PLANNING"
    created_at: datetime


class BacklogResponse(BaseModel):
    items: list[BacklogItem]
    total_count: int


class PlayingItem(BaseModel):
    id: str
    game: GameSummary
    status: Literal["PLAYING"] = "PLAYING"
    platform: str
    started_at: datetime
    play_time_hours: Optional[float] = None
    last_played: Optional[datetime] = None


class PlayingResponse(BaseModel):
    items: list[PlayingItem]
    total_count: int


class CompletedItem(BaseModel):
    id: str
    game: GameSummary
    status: Literal["COMPLETED"] = "COMPLETED"
    platform: str
    completed_at: datetime
    play_time_hours: Optional[float] = None
    rating: Optional[int] = None
    playthrough_type: Optional[str] = None


class CompletedResponse(BaseModel):
    items: list[CompletedItem]
    total_count: int
    completion_stats: Optional[dict[str, float | int | str]] = None


# ===== Bulk Operations =====


class BulkCollectionAction(str, Enum):
    UPDATE_PRIORITY = "update_priority"
    UPDATE_PLATFORM = "update_platform"
    HIDE = "hide"
    ACTIVATE = "activate"


class BulkCollectionRequest(BaseModel):
    action: BulkCollectionAction = Field(..., description="The action to perform")
    collection_ids: list[str] = Field(
        ..., min_length=1, description="Collection item IDs to update"
    )
    data: Optional[dict] = Field(None, description="Action-specific data")


class BulkCollectionResult(BaseModel):
    id: str
    success: bool
    error: Optional[str] = None
    updated_data: Optional[dict] = None


class BulkCollectionResponse(BaseModel):
    success: bool
    updated_count: int
    total_count: int
    results: list[BulkCollectionResult]
