# Core Entity Design

## Overview

The Play Later API is built around three core entities that separate concerns for optimal flexibility and performance:

1. **Game** - Immutable game metadata cached from IGDB
2. **UserGameCollection** - User ownership/access to games on specific platforms  
3. **GamePlaythrough** - Individual play sessions with status tracking

This design enables multiple playthroughs per game, cross-platform ownership, and complex filtering scenarios.

## Entity Models

### Game

Central entity representing game metadata from IGDB with local caching.

```python
class Game(BaseModel):
    id: str                    # UUID primary key
    igdb_id: Optional[int]     # IGDB API identifier
    hltb_id: Optional[int]     # HowLongToBeat identifier  
    steam_app_id: Optional[int] # Steam store identifier
    title: str                 # Game title
    description: Optional[str] # Game description
    cover_image: Optional[str] # Cover art URL
    release_date: Optional[date] # Release date
    main_story: Optional[int]  # HLTB main story hours
    main_extra: Optional[int]  # HLTB main + extras hours
    completionist: Optional[int] # HLTB completionist hours
    created_at: datetime
    updated_at: datetime
```

**Key Characteristics:**
- Immutable after creation (except for HLTB updates)
- Shared across all users to minimize IGDB API calls
- Rich metadata for display and filtering
- Multiple external service integration points

### UserGameCollection

Represents games owned/accessible by a user on specific platforms.

```python
class UserGameCollection(BaseModel):
    id: str                        # UUID primary key
    user_id: str                   # AWS Cognito sub
    game_id: str                   # Foreign key to Game
    acquisition_type: AcquisitionType # How user acquired the game
    platform: str                  # Where the game is owned (PS5, Steam, etc.)
    acquired_at: datetime          # When user acquired the game
    is_active: bool = True         # Soft deletion flag
    priority: Optional[int]        # User-defined priority (1=high, 5=low)
    notes: Optional[str]           # User notes about ownership
    created_at: datetime
    updated_at: datetime
```

**Key Characteristics:**
- Separates ownership from playing
- Platform-specific ownership tracking
- Soft deletion for "hiding" games without data loss
- User-defined organization (priority, notes)

### GamePlaythrough

Individual play sessions/attempts with full lifecycle tracking.

```python
class GamePlaythrough(BaseModel):
    id: str                        # UUID primary key
    user_id: str                   # AWS Cognito sub
    game_id: str                   # Foreign key to Game
    collection_id: Optional[str]   # Optional link to UserGameCollection
    status: PlaythroughStatus      # Current playthrough status
    platform: str                  # Platform this playthrough is on
    started_at: Optional[datetime] # When playthrough began
    completed_at: Optional[datetime] # When playthrough finished
    play_time_hours: Optional[float] # Tracked play time
    playthrough_type: Optional[str] # "First Run", "NG+", "Speedrun", etc.
    difficulty: Optional[str]      # Game difficulty setting
    rating: Optional[int]          # User rating 1-10 for this playthrough
    notes: Optional[str]           # Playthrough-specific notes
    created_at: datetime
    updated_at: datetime
```

**Key Characteristics:**
- Multiple playthroughs per game supported
- Flexible status lifecycle management
- Rich metadata for each playthrough attempt
- Optional collection linking (can play games you don't own)

## Enums

### AcquisitionType

How a user acquired access to a game.

```python
class AcquisitionType(str, Enum):
    PHYSICAL = "PHYSICAL"      # Physical copy owned
    DIGITAL = "DIGITAL"        # Digital purchase/download
    SUBSCRIPTION = "SUBSCRIPTION" # GamePass, PS Plus, etc.
    BORROWED = "BORROWED"      # Borrowed from friend/library
    RENTAL = "RENTAL"          # Short-term rental
```

### PlaythroughStatus

Current state of a playthrough.

```python
class PlaythroughStatus(str, Enum):
    PLANNING = "PLANNING"      # Want to play (backlog)
    PLAYING = "PLAYING"        # Currently playing
    COMPLETED = "COMPLETED"    # Finished main story/objectives
    DROPPED = "DROPPED"        # Abandoned playthrough
    ON_HOLD = "ON_HOLD"       # Temporarily paused
    MASTERED = "MASTERED"     # 100% completion/platinum
```

## Entity Relationships

```
Game (1) ←→ (Many) UserGameCollection
Game (1) ←→ (Many) GamePlaythrough  
UserGameCollection (1) ←→ (Many) GamePlaythrough [Optional]
User ←→ (Many) UserGameCollection
User ←→ (Many) GamePlaythrough
```

### Key Relationship Rules

1. **Game is immutable** - Shared across all users
2. **Collection is platform-specific** - User can own same game on multiple platforms
3. **Playthroughs are independent** - Can exist without collection entry (borrowed games)
4. **User isolation** - All user-specific data filtered by user_id

## Business Logic Examples

### Multiple Playthroughs
```python
# User owns Elden Ring on Steam
collection = UserGameCollection(
    user_id="cognito-user-123",
    game_id="elden-ring-uuid",
    platform="Steam",
    acquisition_type=AcquisitionType.DIGITAL
)

# First playthrough - normal difficulty
playthrough_1 = GamePlaythrough(
    user_id="cognito-user-123", 
    game_id="elden-ring-uuid",
    collection_id=collection.id,
    status=PlaythroughStatus.COMPLETED,
    difficulty="Normal",
    playthrough_type="First Run",
    rating=9
)

# Second playthrough - NG+ challenge run
playthrough_2 = GamePlaythrough(
    user_id="cognito-user-123",
    game_id="elden-ring-uuid", 
    collection_id=collection.id,
    status=PlaythroughStatus.PLAYING,
    difficulty="NG+",
    playthrough_type="Challenge Run"
)
```

### Cross-Platform Ownership
```python
# User owns same game on multiple platforms
ps5_collection = UserGameCollection(
    user_id="user-123",
    game_id="game-uuid",
    platform="PS5",
    acquisition_type=AcquisitionType.PHYSICAL
)

steam_collection = UserGameCollection(
    user_id="user-123", 
    game_id="game-uuid",
    platform="Steam",
    acquisition_type=AcquisitionType.DIGITAL
)

# Can play on either platform
ps5_playthrough = GamePlaythrough(
    user_id="user-123",
    game_id="game-uuid",
    platform="PS5",
    collection_id=ps5_collection.id
)
```

### Playing Without Owning
```python
# Play borrowed game without collection entry
borrowed_playthrough = GamePlaythrough(
    user_id="user-123",
    game_id="borrowed-game-uuid", 
    platform="PS5",
    collection_id=None,  # No collection entry
    status=PlaythroughStatus.PLAYING,
    notes="Borrowed from friend"
)
```

## Comparison with Current Prisma Schema

### Problems Solved

1. **Multiple Playthroughs**: 
   - **Before**: One BacklogItem per user/game limits replay tracking
   - **After**: Unlimited GamePlaythrough records per game

2. **Separation of Concerns**:
   - **Before**: BacklogItem mixes ownership and play status  
   - **After**: Collection (ownership) + Playthrough (playing) separation

3. **Cross-Platform Support**:
   - **Before**: Platform field on BacklogItem doesn't handle multi-platform ownership
   - **After**: Separate collection entries per platform

4. **Flexible Relationships**:
   - **Before**: Tight coupling between ownership and playing
   - **After**: Can play without owning, own without playing

### Data Migration Considerations

- `BacklogItem.status` → `GamePlaythrough.status` 
- `BacklogItem.acquisitionType` → `UserGameCollection.acquisition_type`
- `BacklogItem.platform` → Split into Collection.platform + Playthrough.platform
- Multiple BacklogItems for same game/user → Multiple GamePlaythrough records

## Validation Rules

### Game
- `title` is required and non-empty
- `igdb_id` must be unique if provided
- External IDs (IGDB, HLTB, Steam) are immutable after creation

### UserGameCollection  
- `user_id` + `game_id` + `platform` must be unique
- `priority` must be 1-5 if provided
- `acquired_at` cannot be in the future

### GamePlaythrough
- `completed_at` must be after `started_at` if both provided
- `rating` must be 1-10 if provided  
- `status` transitions must follow logical flow
- `user_id` must match token claims

## Performance Considerations

### Indexing Strategy
```sql
-- Primary indexes
CREATE INDEX idx_collection_user_platform ON user_game_collection(user_id, platform);
CREATE INDEX idx_playthrough_user_status ON game_playthrough(user_id, status);
CREATE INDEX idx_playthrough_game_user ON game_playthrough(game_id, user_id);

-- Filtering indexes  
CREATE INDEX idx_collection_priority ON user_game_collection(user_id, priority);
CREATE INDEX idx_playthrough_completed ON game_playthrough(user_id, completed_at);
CREATE INDEX idx_playthrough_rating ON game_playthrough(user_id, rating);
```

### Query Patterns
- Collections and playthroughs always filtered by `user_id` first
- Complex filters use composite indexes
- Game metadata denormalized where needed for performance