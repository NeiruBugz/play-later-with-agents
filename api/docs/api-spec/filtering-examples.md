# Filtering Examples and Patterns

## Overview

This document provides practical examples of filtering queries across the Play Later API, demonstrating how to combine multiple filters for complex user scenarios.

## Common Filtering Scenarios

### Backlog Management

#### High Priority Backlog
```http
GET /api/v1/games/library?
  status=PLANNING&
  priority=1,2&
  is_active=true&
  sort_by=priority&
  sort_order=asc
```

#### Platform-Specific Backlog
```http
GET /api/v1/games/library?
  status=PLANNING&
  platform=PS5&
  acquisition_type=DIGITAL,PHYSICAL&
  sort_by=acquired_at&
  sort_order=desc&
  limit=50
```

#### Recent Acquisitions Not Started
```http
GET /api/v1/games/library?
  unplayed_only=true&
  acquired_after=2024-01-01&
  platform=Steam,PS5&
  sort_by=acquired_at&
  sort_order=desc
```

---

### Progress Tracking

#### Currently Playing Games
```http
GET /api/v1/playthroughs?
  status=PLAYING&
  sort_by=updated_at&
  sort_order=desc
```

#### Games On Hold
```http
GET /api/v1/playthroughs?
  status=ON_HOLD&
  started_after=2024-01-01&
  sort_by=started_at&
  sort_order=desc
```

#### Long-Running Playthroughs
```http
GET /api/v1/playthroughs?
  status=PLAYING&
  play_time_min=50&
  sort_by=play_time&
  sort_order=desc
```

---

### Completion Analysis

#### Recent Completions
```http
GET /api/v1/playthroughs/completed?
  completed_after=2024-01-01&
  sort_by=completed_at&
  sort_order=desc&
  limit=20
```

#### Highly Rated Games
```http
GET /api/v1/playthroughs?
  status=COMPLETED&
  rating_min=9&
  sort_by=rating&
  sort_order=desc
```

#### Quick Completions
```http
GET /api/v1/playthroughs?
  status=COMPLETED&
  play_time_max=20&
  completed_after=2024-01-01&
  sort_by=play_time&
  sort_order=asc
```

#### Platform Completion Stats
```http
GET /api/v1/playthroughs?
  status=COMPLETED&
  platform=PS5&
  completed_after=2024-01-01&
  sort_by=completed_at&
  sort_order=desc
```

---

### Collection Insights

#### Digital Library Overview
```http
GET /api/v1/collection?
  acquisition_type=DIGITAL&
  is_active=true&
  sort_by=acquired_at&
  sort_order=desc&
  limit=100
```

#### Subscription Games
```http
GET /api/v1/collection?
  acquisition_type=SUBSCRIPTION&
  is_active=true&
  platform=Xbox&
  sort_by=title&
  sort_order=asc
```

#### Unplayed Purchases
```http
GET /api/v1/games/library?
  acquisition_type=DIGITAL,PHYSICAL&
  unplayed_only=true&
  priority=1,2,3&
  sort_by=acquired_at&
  sort_order=desc
```

---

## Advanced Filtering Combinations

### Year in Review Queries

#### 2024 Gaming Summary
```http
GET /api/v1/playthroughs?
  status=COMPLETED&
  completed_after=2024-01-01&
  completed_before=2024-12-31&
  rating_min=7&
  sort_by=rating&
  sort_order=desc
```

#### Best Games of the Year
```http
GET /api/v1/playthroughs?
  status=COMPLETED,MASTERED&
  completed_after=2024-01-01&
  rating_min=9&
  sort_by=rating&
  sort_order=desc
```

#### Most Time Invested
```http
GET /api/v1/playthroughs?
  status=COMPLETED&
  completed_after=2024-01-01&
  play_time_min=30&
  sort_by=play_time&
  sort_order=desc&
  limit=10
```

---

### Platform Migration Analysis

#### Cross-Platform Ownership
```http
# Games owned on multiple platforms
GET /api/v1/collection?
  search=game_title&
  platform=PS5,Steam,Xbox&
  group_by=game_id
```

#### Platform-Specific Completion Rates
```http
# PS5 completions vs Steam completions
GET /api/v1/playthroughs?
  status=COMPLETED&
  platform=PS5&
  completed_after=2024-01-01

GET /api/v1/playthroughs?
  status=COMPLETED&
  platform=Steam&
  completed_after=2024-01-01
```

---

### Discovery and Recommendations

#### Similar Playtime Games
```http
GET /api/v1/playthroughs?
  status=COMPLETED&
  play_time_min=40&
  play_time_max=60&
  rating_min=8&
  sort_by=rating&
  sort_order=desc
```

#### Quick Win Candidates
```http
GET /api/v1/games/library?
  status=PLANNING&
  main_story_max=15&
  priority=1,2&
  sort_by=main_story&
  sort_order=asc
```

#### Long-Form Experiences
```http
GET /api/v1/collection?
  main_story_min=50&
  acquisition_type=DIGITAL&
  is_active=true&
  sort_by=main_story&
  sort_order=desc
```

---

## Search and Text Filtering

### Game Title Search
```http
GET /api/v1/games/library?
  search=witcher&
  sort_by=title&
  sort_order=asc
```

### Notes Search
```http
GET /api/v1/playthroughs?
  search=boss fight&
  status=COMPLETED&
  sort_by=updated_at&
  sort_order=desc
```

### Combined Text and Filters
```http
GET /api/v1/playthroughs?
  search=souls&
  status=COMPLETED&
  rating_min=8&
  difficulty=Hard&
  sort_by=rating&
  sort_order=desc
```

---

## Date Range Filtering

### Acquisition Windows
```http
# Games bought during Steam sales
GET /api/v1/collection?
  platform=Steam&
  acquired_after=2024-06-20&
  acquired_before=2024-07-10&
  sort_by=acquired_at&
  sort_order=asc
```

### Completion Timeframes
```http
# Summer 2024 completions
GET /api/v1/playthroughs?
  status=COMPLETED&
  completed_after=2024-06-01&
  completed_before=2024-09-01&
  sort_by=completed_at&
  sort_order=asc
```

### Activity Periods
```http
# What was I playing last month?
GET /api/v1/playthroughs?
  status=PLAYING,COMPLETED&
  started_after=2024-02-01&
  started_before=2024-03-01&
  sort_by=started_at&
  sort_order=desc
```

---

## Bulk Operations Examples

### Priority Rebalancing
```http
POST /api/v1/collection/bulk
{
  "action": "update_priority",
  "filters": {
    "platform": ["PS5"],
    "priority": [3, 4, 5]
  },
  "data": {
    "priority": 2
  }
}
```

### Platform Migration
```http
POST /api/v1/playthroughs/bulk  
{
  "action": "update_platform",
  "filters": {
    "platform": ["PS4"],
    "status": ["PLANNING", "PLAYING"]
  },
  "data": {
    "platform": "PS5"
  }
}
```

### Cleanup Operations
```http
POST /api/v1/collection/bulk
{
  "action": "hide",
  "filters": {
    "acquisition_type": ["SUBSCRIPTION"],
    "last_played_before": "2023-01-01"
  }
}
```

---

## Performance-Optimized Queries

### Indexed Filter Combinations
```http
# Optimized for user_id + platform + status index
GET /api/v1/playthroughs?
  platform=PS5&
  status=PLAYING&
  limit=10
```

### Efficient Pagination
```http
# Use cursor-based pagination for large results
GET /api/v1/collection?
  sort_by=created_at&
  sort_order=desc&
  after_cursor=eyJjcmVhdGVkX2F0IjoiMjAyNC0wMy0xNSJ9&
  limit=50
```

### Statistics-Friendly Queries
```http
# Aggregate-friendly filtering
GET /api/v1/playthroughs/stats?
  completed_after=2024-01-01&
  platform=PS5,Steam
```

---

## Error Handling Examples

### Invalid Filter Combinations
```http
GET /api/v1/playthroughs?
  rating_min=11&
  play_time_max=-5

# Response:
{
  "error": "validation_error",
  "details": [
    {
      "field": "rating_min",
      "message": "Rating must be between 1 and 10"
    },
    {
      "field": "play_time_max", 
      "message": "Play time must be non-negative"
    }
  ]
}
```

### Conflicting Filters
```http
GET /api/v1/games/library?
  unplayed_only=true&
  status=COMPLETED

# Response:
{
  "error": "conflicting_filters",
  "message": "Cannot combine 'unplayed_only' with completed status filters"
}
```

---

## Frontend Integration Patterns

### React Query with Filters
```typescript
const useFilteredLibrary = (filters: LibraryFilters) => {
  return useQuery({
    queryKey: ['library', filters],
    queryFn: () => api.getLibrary(filters),
    enabled: Object.keys(filters).length > 0
  });
};

// Usage
const { data } = useFilteredLibrary({
  platform: ['PS5', 'Steam'],
  status: ['PLANNING'],
  priority: [1, 2]
});
```

### Debounced Search
```typescript
const useLibrarySearch = () => {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebounce(search, 300);
  
  return useQuery({
    queryKey: ['library-search', debouncedSearch],
    queryFn: () => api.getLibrary({ search: debouncedSearch }),
    enabled: debouncedSearch.length > 2
  });
};
```

### Filter State Management
```typescript
const useFilterState = () => {
  const [filters, setFilters] = useState<LibraryFilters>({});
  
  const updateFilter = (key: keyof LibraryFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };
  
  const clearFilters = () => setFilters({});
  
  const hasActiveFilters = Object.keys(filters).length > 0;
  
  return { filters, updateFilter, clearFilters, hasActiveFilters };
};
```

---

## API Response Caching Strategies

### Filter-Aware Caching
```typescript
// Cache keys include filter parameters
const getCacheKey = (endpoint: string, filters: Record<string, any>) => {
  const sortedFilters = Object.keys(filters)
    .sort()
    .reduce((result, key) => {
      result[key] = filters[key];
      return result;
    }, {} as Record<string, any>);
  
  return `${endpoint}:${JSON.stringify(sortedFilters)}`;
};
```

### Smart Cache Invalidation
```typescript
// Invalidate relevant caches on mutations
const invalidateLibraryCaches = () => {
  queryClient.invalidateQueries({ queryKey: ['library'] });
  queryClient.invalidateQueries({ queryKey: ['playthroughs'] });
  queryClient.invalidateQueries({ queryKey: ['collection'] });
};
```

This comprehensive filtering system enables users to slice and dice their gaming data in sophisticated ways while maintaining excellent performance and user experience.