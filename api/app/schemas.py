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
    UPDATED_AT = "updated_at"
    STARTED_AT = "started_at"
    COMPLETED_AT = "completed_at"
    RATING = "rating"
    PLAY_TIME = "play_time_hours"


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
