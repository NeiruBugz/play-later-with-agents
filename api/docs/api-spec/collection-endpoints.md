# Collection Management API Endpoints

## Overview

The Collection Management API handles user ownership and access to games across different platforms. These endpoints manage the relationship between users and games they own, have access to, or want to track.

## Base Path
```
/api/v1/collection
```

## Authentication
All collection endpoints require valid session authentication via secure HTTP-only cookies.

## Endpoints

### Get User Collection
Get user's game collection with optional filtering.

```http
GET /api/v1/collection
```

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `platform` | `string[]` | No | Filter by platforms (PS5, Steam, Xbox, Switch) |
| `acquisition_type` | `AcquisitionType[]` | No | Filter by acquisition method |
| `priority` | `int[]` | No | Filter by priority level (1-5) |
| `is_active` | `boolean` | No | Show only active items (default: true) |
| `acquired_after` | `date` | No | Items acquired after date (YYYY-MM-DD) |
| `acquired_before` | `date` | No | Items acquired before date (YYYY-MM-DD) |
| `search` | `string` | No | Search in game titles |
| `limit` | `int` | No | Number of items (max 100, default 20) |
| `offset` | `int` | No | Pagination offset (default 0) |
| `sort_by` | `CollectionSortBy` | No | Sort field (default: acquired_at) |
| `sort_order` | `SortOrder` | No | Sort direction (asc/desc, default: desc) |

#### Response
```json
{
  "items": [
    {
      "id": "col_abc123",
      "user_id": "usr_xyz789",
      "game": {
        "id": "game_456",
        "title": "Elden Ring",
        "cover_image_id": "co2lbd",
        "release_date": "2022-02-25",
        "main_story": 60,
        "main_extra": 90,
        "completionist": 140
      },
      "platform": "PS5",
      "acquisition_type": "DIGITAL",
      "acquired_at": "2024-03-15T10:30:00Z",
      "priority": 1,
      "is_active": true,
      "notes": "Bought on sale",
      "created_at": "2024-03-15T10:30:00Z",
      "updated_at": "2024-03-15T10:30:00Z"
    }
  ],
  "total_count": 156,
  "limit": 20,
  "offset": 0,
  "filters_applied": {
    "platform": ["PS5"],
    "priority": [1, 2]
  }
}
```

#### IGDB Image Usage
The `cover_image_id` field contains IGDB image identifiers that can be used to construct URLs for different sizes:

```javascript
// Frontend usage examples
const coverImageId = "co2lbd";

// Different sizes available
const thumbnailUrl = `https://images.igdb.com/igdb/image/upload/t_thumb/${coverImageId}.jpg`;
const coverSmallUrl = `https://images.igdb.com/igdb/image/upload/t_cover_small/${coverImageId}.jpg`;
const coverBigUrl = `https://images.igdb.com/igdb/image/upload/t_cover_big/${coverImageId}.jpg`;
const screenshotMedUrl = `https://images.igdb.com/igdb/image/upload/t_screenshot_med/${coverImageId}.jpg`;

// Responsive image component
<img 
  src={`https://images.igdb.com/igdb/image/upload/t_cover_small/${coverImageId}.jpg`}
  srcSet={`
    https://images.igdb.com/igdb/image/upload/t_thumb/${coverImageId}.jpg 90w,
    https://images.igdb.com/igdb/image/upload/t_cover_small/${coverImageId}.jpg 264w,
    https://images.igdb.com/igdb/image/upload/t_cover_big/${coverImageId}.jpg 374w
  `}
  sizes="(max-width: 768px) 90px, (max-width: 1024px) 264px, 374px"
  alt={game.title}
/>
```

#### Status Codes
- `200 OK` - Success
- `400 Bad Request` - Invalid query parameters
- `401 Unauthorized` - Authentication required
- `422 Unprocessable Entity` - Validation errors

---

### Add Game to Collection
Add a game to user's collection.

```http
POST /api/v1/collection
```

#### Request Body
```json
{
  "game_id": "game_456",
  "platform": "PS5",
  "acquisition_type": "DIGITAL",
  "acquired_at": "2024-03-15T10:30:00Z",
  "priority": 1,
  "notes": "Bought on sale"
}
```

#### Response
```json
{
  "id": "col_abc123",
  "user_id": "usr_xyz789",
  "game_id": "game_456",
  "platform": "PS5",
  "acquisition_type": "DIGITAL",
  "acquired_at": "2024-03-15T10:30:00Z",
  "priority": 1,
  "is_active": true,
  "notes": "Bought on sale",
  "created_at": "2024-03-15T10:30:00Z",
  "updated_at": "2024-03-15T10:30:00Z"
}
```

#### Status Codes
- `201 Created` - Game added successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `409 Conflict` - Game already in collection for this platform
- `422 Unprocessable Entity` - Validation errors

#### Validation Rules
- `game_id` must exist in games table
- `platform` is required and non-empty
- `acquisition_type` must be valid enum value
- `priority` must be 1-5 if provided
- `acquired_at` cannot be in future
- Unique constraint: user_id + game_id + platform

---

### Get Collection Item
Get specific collection item by ID.

```http
GET /api/v1/collection/{collection_id}
```

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_id` | `string` | Yes | Collection item UUID |

#### Response
```json
{
  "id": "col_abc123",
  "user_id": "usr_xyz789",
  "game": {
    "id": "game_456",
    "title": "Elden Ring",
    "cover_image_id": "co2lbd",
    "release_date": "2022-02-25",
    "description": "A fantasy action RPG...",
    "igdb_id": 119171,
    "hltb_id": 68151,
    "steam_app_id": 1245620
  },
  "platform": "PS5",
  "acquisition_type": "DIGITAL",
  "acquired_at": "2024-03-15T10:30:00Z",
  "priority": 1,
  "is_active": true,
  "notes": "Bought on sale",
  "playthroughs": [
    {
      "id": "play_789",
      "status": "COMPLETED",
      "rating": 9,
      "completed_at": "2024-04-20T15:45:00Z"
    }
  ],
  "created_at": "2024-03-15T10:30:00Z",
  "updated_at": "2024-03-15T10:30:00Z"
}
```

#### Status Codes
- `200 OK` - Success
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Collection item not found or not owned by user

---

### Update Collection Item
Update collection item details.

```http
PUT /api/v1/collection/{collection_id}
```

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_id` | `string` | Yes | Collection item UUID |

#### Request Body
```json
{
  "priority": 2,
  "notes": "Updated notes",
  "is_active": true
}
```

#### Response
```json
{
  "id": "col_abc123",
  "user_id": "usr_xyz789",
  "game_id": "game_456",
  "platform": "PS5",
  "acquisition_type": "DIGITAL",
  "acquired_at": "2024-03-15T10:30:00Z",
  "priority": 2,
  "is_active": true,
  "notes": "Updated notes",
  "created_at": "2024-03-15T10:30:00Z",
  "updated_at": "2024-03-16T09:20:00Z"
}
```

#### Status Codes
- `200 OK` - Updated successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Collection item not found
- `422 Unprocessable Entity` - Validation errors

#### Validation Rules
- `priority` must be 1-5 if provided
- Cannot modify `game_id`, `platform`, `acquisition_type`, or `acquired_at`

---

### Remove from Collection
Remove game from user's collection (soft delete).

```http
DELETE /api/v1/collection/{collection_id}
```

#### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_id` | `string` | Yes | Collection item UUID |

#### Query Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `hard_delete` | `boolean` | No | Permanently delete (default: false) |

#### Response
```json
{
  "success": true,
  "message": "Game removed from collection"
}
```

#### Status Codes
- `200 OK` - Removed successfully
- `401 Unauthorized` - Authentication required
- `404 Not Found` - Collection item not found

#### Notes
- Default behavior is soft delete (`is_active = false`)
- Hard delete removes record entirely and cascades to related playthroughs
- Hard delete requires confirmation and may be restricted

---

### Bulk Collection Operations
Perform operations on multiple collection items.

```http
POST /api/v1/collection/bulk
```

#### Request Body
```json
{
  "action": "update_priority",
  "collection_ids": ["col_abc123", "col_def456"],
  "data": {
    "priority": 1
  }
}
```

#### Supported Actions
- `update_priority` - Update priority for multiple items
- `update_platform` - Change platform for multiple items
- `hide` - Soft delete multiple items
- `activate` - Reactivate multiple items

#### Response
```json
{
  "success": true,
  "updated_count": 2,
  "items": [
    {
      "id": "col_abc123",
      "priority": 1
    },
    {
      "id": "col_def456", 
      "priority": 1
    }
  ]
}
```

#### Status Codes
- `200 OK` - Operation completed
- `400 Bad Request` - Invalid action or data
- `401 Unauthorized` - Authentication required
- `207 Multi-Status` - Partial success (some items failed)

---

## Collection Statistics

### Get Collection Statistics
Get user's collection statistics and insights.

```http
GET /api/v1/collection/stats
```

#### Response
```json
{
  "total_games": 156,
  "by_platform": {
    "PS5": 45,
    "Steam": 89,
    "Xbox": 15,
    "Switch": 7
  },
  "by_acquisition_type": {
    "DIGITAL": 120,
    "PHYSICAL": 25,
    "SUBSCRIPTION": 11
  },
  "by_priority": {
    "1": 12,
    "2": 23,
    "3": 45,
    "4": 34,
    "5": 15,
    "null": 27
  },
  "value_estimate": {
    "digital": 2450.99,
    "physical": 890.50,
    "currency": "USD"
  },
  "recent_additions": [
    {
      "game": {
        "title": "Baldur's Gate 3",
        "cover_image_id": "co5vmg"
      },
      "platform": "PS5",
      "acquired_at": "2024-03-15T10:30:00Z"
    }
  ]
}
```

#### Status Codes
- `200 OK` - Success
- `401 Unauthorized` - Authentication required

---

## Error Responses

### Standard Error Format
```json
{
  "error": "validation_error",
  "message": "Invalid request data",
  "details": [
    {
      "field": "priority",
      "message": "Priority must be between 1 and 5"
    }
  ],
  "timestamp": "2024-03-15T10:30:00Z",
  "request_id": "req_abc123"
}
```

### Common Error Types
- `authentication_required` - Missing or invalid session
- `validation_error` - Request data validation failed
- `not_found` - Resource not found or not accessible
- `conflict` - Resource already exists
- `rate_limited` - Too many requests

---

## Data Types

### AcquisitionType
```typescript
enum AcquisitionType {
  PHYSICAL = "PHYSICAL",
  DIGITAL = "DIGITAL", 
  SUBSCRIPTION = "SUBSCRIPTION",
  BORROWED = "BORROWED",
  RENTAL = "RENTAL"
}
```

### CollectionSortBy
```typescript
enum CollectionSortBy {
  TITLE = "title",
  ACQUIRED_AT = "acquired_at",
  PRIORITY = "priority", 
  PLATFORM = "platform",
  UPDATED_AT = "updated_at"
}
```

### SortOrder
```typescript
enum SortOrder {
  ASC = "asc",
  DESC = "desc"
}
```

---

## IGDB Image Integration

### Image ID Format
IGDB provides image identifiers in formats like:
- `co2lbd` - Cover images
- `sc6zkq` - Screenshots  
- `ar7kb2` - Artworks

### Available Image Sizes
| Size Name | Dimensions | URL Template |
|-----------|------------|--------------|
| `t_thumb` | 90x128 | `https://images.igdb.com/igdb/image/upload/t_thumb/{image_id}.jpg` |
| `t_micro` | 35x35 | `https://images.igdb.com/igdb/image/upload/t_micro/{image_id}.jpg` |
| `t_cover_small` | 264x374 | `https://images.igdb.com/igdb/image/upload/t_cover_small/{image_id}.jpg` |
| `t_cover_big` | 374x500 | `https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg` |
| `t_screenshot_med` | 569x320 | `https://images.igdb.com/igdb/image/upload/t_screenshot_med/{image_id}.jpg` |
| `t_screenshot_big` | 889x500 | `https://images.igdb.com/igdb/image/upload/t_screenshot_big/{image_id}.jpg` |
| `t_screenshot_huge` | 1280x720 | `https://images.igdb.com/igdb/image/upload/t_screenshot_huge/{image_id}.jpg` |
| `t_1080p` | 1920x1080 | `https://images.igdb.com/igdb/image/upload/t_1080p/{image_id}.jpg` |

### Frontend Helper Functions
```typescript
// Utility functions for image URLs
export const getIgdbImageUrl = (imageId: string, size: string = 't_cover_small'): string => {
  if (!imageId) return '/placeholder-game.jpg';
  return `https://images.igdb.com/igdb/image/upload/${size}/${imageId}.jpg`;
};

export const getResponsiveImageProps = (imageId: string, alt: string) => ({
  src: getIgdbImageUrl(imageId, 't_cover_small'),
  srcSet: [
    `${getIgdbImageUrl(imageId, 't_thumb')} 90w`,
    `${getIgdbImageUrl(imageId, 't_cover_small')} 264w`,
    `${getIgdbImageUrl(imageId, 't_cover_big')} 374w`
  ].join(', '),
  sizes: '(max-width: 768px) 90px, (max-width: 1024px) 264px, 374px',
  alt
});
```

---

## Rate Limiting
- Standard rate limit: 100 requests per minute per user
- Bulk operations: 10 requests per minute per user
- Collection stats: 20 requests per minute per user

## Caching
- Collection list responses cached for 5 minutes
- Individual collection items cached for 15 minutes
- Statistics cached for 30 minutes
- Cache invalidated on any collection mutations