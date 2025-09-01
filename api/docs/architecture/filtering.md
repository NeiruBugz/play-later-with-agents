# Advanced Filtering Design

## Overview

The Play Later API provides sophisticated filtering capabilities across game collections and playthroughs. The filtering system is designed for performance, usability, and extensibility while maintaining type safety and clear API patterns.

## Core Filtering Concepts

### Separation of Filtering Domains
- **Collection Filters**: What games you own/access (platform, acquisition type, priority)
- **Playthrough Filters**: Your play history and status (status, rating, completion dates)  
- **Game Filters**: Game metadata (title search, release date, HLTB hours)
- **Combined Filters**: Cross-domain queries combining all above

### Query Parameter Patterns
```
# Array parameters (multiple values)
?platform=PS5,Steam&status=PLAYING,COMPLETED

# Range parameters  
?rating_min=8&rating_max=10&play_time_max=50

# Date parameters
?completed_after=2024-01-01&acquired_before=2024-12-31

# Search parameters
?search=elden&sort_by=title&sort_order=asc
```

## API Endpoint Design

### Collection Filtering
```python
@router.get("/collection")
async def get_user_collection(
    # Platform filters
    platform: Optional[List[str]] = Query(None),
    acquisition_type: Optional[List[AcquisitionType]] = Query(None),
    
    # Organization filters  
    priority: Optional[List[int]] = Query(None),
    is_active: Optional[bool] = Query(True),
    
    # Date filters
    acquired_after: Optional[date] = Query(None),
    acquired_before: Optional[date] = Query(None),
    
    # Pagination & sorting
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    sort_by: CollectionSortBy = Query(CollectionSortBy.ACQUIRED_AT),
    sort_order: SortOrder = Query(SortOrder.DESC),
    
    user: UserContext = Depends(get_current_user)
) -> CollectionFilterResponse:
    """Get user's game collection with filtering."""
    
    filters = CollectionFilters(
        user_id=user.user_id,
        platform=platform,
        acquisition_type=acquisition_type,
        priority=priority,
        is_active=is_active,
        acquired_after=acquired_after,
        acquired_before=acquired_before
    )
    
    result = await collection_service.get_filtered_collection(
        filters=filters,
        pagination=PaginationParams(limit=limit, offset=offset),
        sorting=SortingParams(sort_by=sort_by, sort_order=sort_order)
    )
    
    return result

class CollectionSortBy(str, Enum):
    TITLE = "title"
    ACQUIRED_AT = "acquired_at" 
    PRIORITY = "priority"
    PLATFORM = "platform"
```

### Playthrough Filtering
```python
@router.get("/playthroughs")
async def get_user_playthroughs(
    # Status filters
    status: Optional[List[PlaythroughStatus]] = Query(None),
    
    # Platform filters
    platform: Optional[List[str]] = Query(None),
    
    # Rating filters
    rating_min: Optional[int] = Query(None, ge=1, le=10),
    rating_max: Optional[int] = Query(None, ge=1, le=10), 
    
    # Time filters
    play_time_min: Optional[float] = Query(None, ge=0),
    play_time_max: Optional[float] = Query(None, ge=0),
    
    # Date filters
    started_after: Optional[date] = Query(None),
    completed_after: Optional[date] = Query(None),
    completed_before: Optional[date] = Query(None),
    
    # Game filters
    search: Optional[str] = Query(None),
    
    # Pagination & sorting  
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    sort_by: PlaythroughSortBy = Query(PlaythroughSortBy.UPDATED_AT),
    sort_order: SortOrder = Query(SortOrder.DESC),
    
    user: UserContext = Depends(get_current_user)
) -> PlaythroughFilterResponse:
    """Get user's playthroughs with advanced filtering."""
    
    filters = PlaythroughFilters(
        user_id=user.user_id,
        status=status,
        platform=platform,
        rating_min=rating_min,
        rating_max=rating_max,
        play_time_min=play_time_min,
        play_time_max=play_time_max,
        started_after=started_after,
        completed_after=completed_after,
        completed_before=completed_before,
        search=search
    )
    
    result = await playthrough_service.get_filtered_playthroughs(
        filters=filters,
        pagination=PaginationParams(limit=limit, offset=offset),
        sorting=SortingParams(sort_by=sort_by, sort_order=sort_order)
    )
    
    return result

class PlaythroughSortBy(str, Enum):
    TITLE = "title"
    STATUS = "status"
    STARTED_AT = "started_at"
    COMPLETED_AT = "completed_at"
    UPDATED_AT = "updated_at"
    RATING = "rating"
    PLAY_TIME = "play_time_hours"
```

### Combined Library Filtering
```python
@router.get("/games/library")
async def get_user_library(
    # Collection filters
    platform: Optional[List[str]] = Query(None),
    acquisition_type: Optional[List[AcquisitionType]] = Query(None),
    priority: Optional[List[int]] = Query(None),
    
    # Playthrough filters
    status: Optional[List[PlaythroughStatus]] = Query(None),
    rating_min: Optional[int] = Query(None, ge=1, le=10),
    
    # Game filters
    search: Optional[str] = Query(None),
    release_year: Optional[int] = Query(None),
    
    # Special filters
    unplayed_only: Optional[bool] = Query(False),
    completed_only: Optional[bool] = Query(False),
    
    # Pagination & sorting
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    sort_by: LibrarySortBy = Query(LibrarySortBy.ACQUIRED_AT),
    sort_order: SortOrder = Query(SortOrder.DESC),
    
    user: UserContext = Depends(get_current_user)
) -> LibraryFilterResponse:
    """Get user's full game library with cross-domain filtering."""
    
    # Build complex query combining collection + playthrough + game data
    result = await library_service.get_filtered_library(
        user_id=user.user_id,
        filters=CombinedLibraryFilters(
            platform=platform,
            acquisition_type=acquisition_type,
            priority=priority,
            status=status,
            rating_min=rating_min,
            search=search,
            release_year=release_year,
            unplayed_only=unplayed_only,
            completed_only=completed_only
        ),
        pagination=PaginationParams(limit=limit, offset=offset),
        sorting=SortingParams(sort_by=sort_by, sort_order=sort_order)
    )
    
    return result

class LibrarySortBy(str, Enum):
    TITLE = "title"
    ACQUIRED_AT = "acquired_at"
    RELEASE_DATE = "release_date"  
    LAST_PLAYED = "last_played"
    COMPLETION_TIME = "completion_time"
    RATING = "rating"
```

## Convenience Endpoints

### Common Filter Scenarios
```python
# Quick access endpoints for common user scenarios

@router.get("/games/backlog")
async def get_backlog(
    platform: Optional[List[str]] = Query(None),
    limit: int = Query(20),
    user: UserContext = Depends(get_current_user)
):
    """Get games in backlog (status=PLANNING)."""
    return await library_service.get_backlog(user.user_id, platform, limit)

@router.get("/games/playing") 
async def get_currently_playing(
    platform: Optional[List[str]] = Query(None),
    user: UserContext = Depends(get_current_user)
):
    """Get currently playing games (status=PLAYING)."""
    return await library_service.get_currently_playing(user.user_id, platform)

@router.get("/games/completed")
async def get_completed_games(
    year: Optional[int] = Query(None),
    rating_min: Optional[int] = Query(None),
    platform: Optional[List[str]] = Query(None),
    limit: int = Query(50),
    user: UserContext = Depends(get_current_user)
):
    """Get completed games with optional filters."""
    return await library_service.get_completed_games(
        user.user_id, year, rating_min, platform, limit
    )

@router.get("/games/wishlist")
async def get_wishlist(
    platform: Optional[List[str]] = Query(None),
    user: UserContext = Depends(get_current_user)  
):
    """Get games user wants to play but doesn't own."""
    return await library_service.get_wishlist(user.user_id, platform)

@router.get("/games/high-priority")
async def get_high_priority_games(
    user: UserContext = Depends(get_current_user)
):
    """Get high priority games (priority 1-2) in backlog."""
    return await library_service.get_high_priority_backlog(user.user_id)
```

## Service Layer Implementation

### Collection Service with Filtering
```python
class CollectionService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_filtered_collection(
        self,
        filters: CollectionFilters,
        pagination: PaginationParams,
        sorting: SortingParams
    ) -> CollectionFilterResponse:
        """Get filtered collection with efficient queries."""
        
        # Start with base query
        query = select(UserGameCollection).join(Game).where(
            UserGameCollection.user_id == filters.user_id
        )
        
        # Apply filters
        if filters.platform:
            query = query.where(UserGameCollection.platform.in_(filters.platform))
            
        if filters.acquisition_type:
            query = query.where(UserGameCollection.acquisition_type.in_(filters.acquisition_type))
            
        if filters.priority:
            query = query.where(UserGameCollection.priority.in_(filters.priority))
            
        if filters.is_active is not None:
            query = query.where(UserGameCollection.is_active == filters.is_active)
            
        if filters.acquired_after:
            query = query.where(UserGameCollection.acquired_at >= filters.acquired_after)
            
        if filters.acquired_before:
            query = query.where(UserGameCollection.acquired_at <= filters.acquired_before)
        
        # Apply sorting
        sort_column = getattr(UserGameCollection, sorting.sort_by)
        if sorting.sort_order == SortOrder.DESC:
            sort_column = sort_column.desc()
        query = query.order_by(sort_column)
        
        # Count total for pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await self.db.scalar(count_query)
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        # Execute query
        result = await self.db.execute(query)
        collection_items = result.scalars().all()
        
        return CollectionFilterResponse(
            items=collection_items,
            total_count=total_count,
            limit=pagination.limit,
            offset=pagination.offset,
            filters_applied=filters
        )
```

### Complex Library Queries
```python
class LibraryService:
    """Service for cross-domain library queries."""
    
    async def get_filtered_library(
        self, 
        user_id: str,
        filters: CombinedLibraryFilters,
        pagination: PaginationParams,
        sorting: SortingParams
    ) -> LibraryFilterResponse:
        """Complex query combining collection, playthrough, and game data."""
        
        # Build complex JOIN query
        query = (
            select(
                Game,
                UserGameCollection,
                func.max(GamePlaythrough.updated_at).label('last_played'),
                func.avg(GamePlaythrough.rating).label('avg_rating'),
                func.count(GamePlaythrough.id).label('playthrough_count')
            )
            .select_from(Game)
            .join(UserGameCollection, UserGameCollection.game_id == Game.id)
            .outerjoin(GamePlaythrough, and_(
                GamePlaythrough.game_id == Game.id,
                GamePlaythrough.user_id == user_id
            ))
            .where(UserGameCollection.user_id == user_id)
            .group_by(Game.id, UserGameCollection.id)
        )
        
        # Apply cross-domain filters
        if filters.platform:
            query = query.where(UserGameCollection.platform.in_(filters.platform))
            
        if filters.status:
            # Filter by playthrough status - requires subquery
            status_subquery = select(GamePlaythrough.game_id).where(
                and_(
                    GamePlaythrough.user_id == user_id,
                    GamePlaythrough.status.in_(filters.status)
                )
            )
            query = query.where(Game.id.in_(status_subquery))
            
        if filters.search:
            query = query.where(Game.title.ilike(f"%{filters.search}%"))
            
        if filters.unplayed_only:
            # Games with no playthroughs
            query = query.having(func.count(GamePlaythrough.id) == 0)
            
        if filters.completed_only:
            # Games with at least one completed playthrough
            completed_subquery = select(GamePlaythrough.game_id).where(
                and_(
                    GamePlaythrough.user_id == user_id,
                    GamePlaythrough.status == PlaythroughStatus.COMPLETED
                )
            )
            query = query.where(Game.id.in_(completed_subquery))
        
        # Apply sophisticated sorting
        if sorting.sort_by == "last_played":
            query = query.order_by(func.max(GamePlaythrough.updated_at).desc())
        elif sorting.sort_by == "avg_rating":
            query = query.order_by(func.avg(GamePlaythrough.rating).desc())
        else:
            sort_column = getattr(Game, sorting.sort_by, None) or getattr(UserGameCollection, sorting.sort_by)
            query = query.order_by(sort_column.desc() if sorting.sort_order == SortOrder.DESC else sort_column)
        
        # Pagination and execution
        total_count = await self._count_library_results(user_id, filters)
        
        results = await self.db.execute(
            query.offset(pagination.offset).limit(pagination.limit)
        )
        
        # Transform results into response format
        library_items = []
        for game, collection, last_played, avg_rating, playthrough_count in results:
            library_items.append(LibraryItem(
                game=game,
                collection=collection,
                last_played=last_played,
                avg_rating=avg_rating,
                playthrough_count=playthrough_count
            ))
        
        return LibraryFilterResponse(
            items=library_items,
            total_count=total_count,
            pagination=pagination,
            filters_applied=filters
        )
```

## Performance Optimization

### Database Indexing Strategy
```sql
-- Core indexes for filtering
CREATE INDEX idx_collection_user_platform ON user_game_collection(user_id, platform);
CREATE INDEX idx_collection_user_priority ON user_game_collection(user_id, priority);
CREATE INDEX idx_collection_user_acquired ON user_game_collection(user_id, acquired_at);
CREATE INDEX idx_collection_active ON user_game_collection(user_id, is_active);

CREATE INDEX idx_playthrough_user_status ON game_playthrough(user_id, status);
CREATE INDEX idx_playthrough_user_platform ON game_playthrough(user_id, platform);  
CREATE INDEX idx_playthrough_user_rating ON game_playthrough(user_id, rating);
CREATE INDEX idx_playthrough_user_completed ON game_playthrough(user_id, completed_at);
CREATE INDEX idx_playthrough_user_updated ON game_playthrough(user_id, updated_at);

CREATE INDEX idx_game_title_search ON game USING gin(to_tsvector('english', title));
CREATE INDEX idx_game_release_year ON game(extract(year from release_date));

-- Composite indexes for common filter combinations
CREATE INDEX idx_collection_platform_priority ON user_game_collection(user_id, platform, priority);
CREATE INDEX idx_playthrough_status_platform ON game_playthrough(user_id, status, platform);
CREATE INDEX idx_playthrough_status_rating ON game_playthrough(user_id, status, rating);
```

### Query Performance Patterns
```python
class PerformantFilterService:
    """Optimized filtering with performance considerations."""
    
    async def get_optimized_backlog(
        self, 
        user_id: str, 
        platform: Optional[List[str]] = None
    ) -> List[BacklogItem]:
        """Highly optimized backlog query."""
        
        # Use covering index to avoid table lookups
        query = (
            select(
                Game.id,
                Game.title,
                Game.cover_image,
                UserGameCollection.platform,
                UserGameCollection.priority,
                UserGameCollection.acquired_at
            )
            .select_from(UserGameCollection)
            .join(Game, Game.id == UserGameCollection.game_id)
            .outerjoin(
                GamePlaythrough,
                and_(
                    GamePlaythrough.game_id == Game.id,
                    GamePlaythrough.user_id == user_id,
                    GamePlaythrough.status != PlaythroughStatus.PLANNING
                )
            )
            .where(
                and_(
                    UserGameCollection.user_id == user_id,
                    UserGameCollection.is_active == True,
                    GamePlaythrough.id.is_(None)  # No non-planning playthroughs
                )
            )
        )
        
        if platform:
            query = query.where(UserGameCollection.platform.in_(platform))
        
        # Order by priority, then acquisition date
        query = query.order_by(
            UserGameCollection.priority.asc().nulls_last(),
            UserGameCollection.acquired_at.desc()
        )
        
        result = await self.db.execute(query)
        return [BacklogItem(**row._asdict()) for row in result]
```

### Caching Strategy
```python
from functools import lru_cache
import redis

class FilterCacheService:
    """Caching for expensive filter queries."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def get_cached_filter_result(
        self,
        cache_key: str,
        query_func,
        ttl: int = 300  # 5 minutes
    ):
        """Generic caching for filter results."""
        
        # Check cache first
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Execute query and cache result
        result = await query_func()
        await self.redis.setex(cache_key, ttl, json.dumps(result, default=str))
        
        return result
    
    def build_cache_key(self, user_id: str, filters: dict) -> str:
        """Build consistent cache key from filters."""
        # Sort filters for consistent keys
        filter_str = json.dumps(filters, sort_keys=True)
        return f"filter:{user_id}:{hash(filter_str)}"

# Usage in service
async def get_expensive_library_view(self, user_id: str, filters: dict):
    cache_key = self.cache_service.build_cache_key(user_id, filters)
    
    return await self.cache_service.get_cached_filter_result(
        cache_key,
        lambda: self._execute_expensive_query(user_id, filters),
        ttl=300
    )
```

## Frontend Integration

### TypeScript Filter Types  
```typescript
// Auto-generated from OpenAPI schema
interface CollectionFilters {
  platform?: string[];
  acquisition_type?: AcquisitionType[];
  priority?: number[];
  is_active?: boolean;
  acquired_after?: string;
  acquired_before?: string;
}

interface PlaythroughFilters {
  status?: PlaythroughStatus[];
  platform?: string[];
  rating_min?: number;
  rating_max?: number;
  play_time_min?: number;
  play_time_max?: number;
  started_after?: string;
  completed_after?: string;
  completed_before?: string;
  search?: string;
}

interface PaginationParams {
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}
```

### React Filter Hook
```typescript
import { useCallback, useState } from 'react';
import { LibraryService } from '@/shared/api/generated';

export function useLibraryFilters() {
  const [filters, setFilters] = useState<LibraryFilters>({});
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<LibraryItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  
  const applyFilters = useCallback(async (newFilters: Partial<LibraryFilters>) => {
    setLoading(true);
    
    const combinedFilters = { ...filters, ...newFilters };
    setFilters(combinedFilters);
    
    try {
      const response = await LibraryService.getUserLibrary({
        ...combinedFilters,
        limit: 20,
        offset: 0
      });
      
      setResults(response.items);
      setTotalCount(response.total_count);
    } catch (error) {
      console.error('Filter error:', error);
    } finally {
      setLoading(false);
    }
  }, [filters]);
  
  const clearFilters = useCallback(() => {
    setFilters({});
    applyFilters({});
  }, [applyFilters]);
  
  return {
    filters,
    results,
    totalCount,
    loading,
    applyFilters,
    clearFilters
  };
}
```

### Filter UI Component
```typescript
interface FilterPanelProps {
  onFiltersChange: (filters: Partial<LibraryFilters>) => void;
  currentFilters: LibraryFilters;
}

export function FilterPanel({ onFiltersChange, currentFilters }: FilterPanelProps) {
  return (
    <div className="space-y-4">
      {/* Platform filter */}
      <MultiSelect
        label="Platform"
        options={['PS5', 'Steam', 'Xbox', 'Switch']}
        value={currentFilters.platform || []}
        onChange={(platform) => onFiltersChange({ platform })}
      />
      
      {/* Status filter */}
      <MultiSelect
        label="Status"
        options={['PLANNING', 'PLAYING', 'COMPLETED', 'DROPPED']}
        value={currentFilters.status || []}
        onChange={(status) => onFiltersChange({ status })}
      />
      
      {/* Rating range */}
      <RangeSlider
        label="Rating"
        min={1}
        max={10}
        value={[currentFilters.rating_min || 1, currentFilters.rating_max || 10]}
        onChange={([rating_min, rating_max]) => 
          onFiltersChange({ rating_min, rating_max })
        }
      />
      
      {/* Quick filters */}
      <div className="flex gap-2">
        <Button 
          variant={currentFilters.unplayed_only ? 'default' : 'outline'}
          onClick={() => onFiltersChange({ unplayed_only: !currentFilters.unplayed_only })}
        >
          Unplayed Only
        </Button>
        
        <Button
          variant={currentFilters.completed_only ? 'default' : 'outline'} 
          onClick={() => onFiltersChange({ completed_only: !currentFilters.completed_only })}
        >
          Completed Only
        </Button>
      </div>
    </div>
  );
}
```

## Example Filter Scenarios

### Complex Real-World Queries
```python
# "Show me high-priority PS5/Steam games I haven't started, 
#  acquired in the last 6 months, sorted by acquisition date"
GET /api/v1/games/library?
  platform=PS5,Steam&
  priority=1,2&
  unplayed_only=true&
  acquired_after=2024-06-01&
  sort_by=acquired_at&
  sort_order=desc

# "Show completed games from 2024 with rating 8+ on any platform"
GET /api/v1/games/completed?
  year=2024&
  rating_min=8

# "Show currently playing games with more than 10 hours logged"
GET /api/v1/playthroughs?
  status=PLAYING&
  play_time_min=10&
  sort_by=play_time&
  sort_order=desc
```

This filtering system provides both power and performance, enabling users to slice and dice their game libraries in sophisticated ways while maintaining fast query responses.