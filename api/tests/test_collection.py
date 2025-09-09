from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db import get_db, SessionLocal
from app.db_models import Game, CollectionItem, Playthrough
from app.schemas import AcquisitionType

client = TestClient(app)

# Ensure tables exist
from app.db import Base

Base.metadata.create_all(bind=SessionLocal.kw["bind"])


@pytest.fixture
def test_data():
    """Create test data for collection tests."""
    with SessionLocal() as db:
        # Clean up existing data
        db.query(Playthrough).delete()
        db.query(CollectionItem).delete()
        db.query(Game).delete()
        db.commit()

        # Create test games
        games = [
            Game(
                id="game1",
                title="The Witcher 3",
                cover_image_id="tw3_cover",
                igdb_id=1942,
            ),
            Game(
                id="game2",
                title="Elden Ring",
                cover_image_id="er_cover",
                igdb_id=119171,
            ),
            Game(
                id="game3",
                title="Hollow Knight",
                cover_image_id="hk_cover",
                igdb_id=26286,
            ),
        ]

        # Create test collection items for user1
        collection_items = [
            CollectionItem(
                id="col1",
                user_id="user1",
                game_id="game1",
                platform="PC",
                acquisition_type=AcquisitionType.DIGITAL.value,
                priority=1,
                is_active=True,
                notes="Great RPG",
                created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            ),
            CollectionItem(
                id="col2",
                user_id="user1",
                game_id="game2",
                platform="PS5",
                acquisition_type=AcquisitionType.PHYSICAL.value,
                priority=2,
                is_active=True,
                notes="Souls-like masterpiece",
                created_at=datetime(2023, 2, 1, tzinfo=timezone.utc),
                updated_at=datetime(2023, 2, 1, tzinfo=timezone.utc),
            ),
            CollectionItem(
                id="col3",
                user_id="user1",
                game_id="game3",
                platform="PC",
                acquisition_type=AcquisitionType.DIGITAL.value,
                priority=3,
                is_active=False,  # Inactive item
                notes="Beautiful metroidvania",
                created_at=datetime(2023, 3, 1, tzinfo=timezone.utc),
                updated_at=datetime(2023, 3, 1, tzinfo=timezone.utc),
            ),
            # Collection item for different user
            CollectionItem(
                id="col4",
                user_id="user2",
                game_id="game1",
                platform="Xbox",
                acquisition_type=AcquisitionType.SUBSCRIPTION.value,
                priority=1,
                is_active=True,
                notes="Playing on Game Pass",
                created_at=datetime(2023, 1, 15, tzinfo=timezone.utc),
                updated_at=datetime(2023, 1, 15, tzinfo=timezone.utc),
            ),
        ]

        # Create test playthroughs
        playthroughs = [
            Playthrough(
                id="pt1",
                user_id="user1",
                game_id="game1",
                collection_id="col1",
                status="COMPLETED",
                platform="PC",
                play_time_hours=150.5,
                rating=9,
                created_at=datetime(2023, 1, 5, tzinfo=timezone.utc),
                updated_at=datetime(2023, 1, 5, tzinfo=timezone.utc),
            ),
            Playthrough(
                id="pt2",
                user_id="user1",
                game_id="game2",
                collection_id="col2",
                status="PLAYING",
                platform="PS5",
                play_time_hours=25.0,
                created_at=datetime(2023, 2, 5, tzinfo=timezone.utc),
                updated_at=datetime(2023, 2, 5, tzinfo=timezone.utc),
            ),
        ]

        # Add all data to database in correct order (games first, then collection_items, then playthroughs)
        for game in games:
            db.add(game)
        db.commit()  # Commit games first

        for item in collection_items:
            db.add(item)
        db.commit()  # Commit collection items second

        for pt in playthroughs:
            db.add(pt)
        db.commit()  # Commit playthroughs last

    yield

    # Cleanup after test
    with SessionLocal() as db:
        db.query(Playthrough).delete()
        db.query(CollectionItem).delete()
        db.query(Game).delete()
        db.commit()


def test_list_collection_requires_auth():
    """Test that collection endpoint requires authentication."""
    response = client.get("/api/v1/collection")
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_list_collection_basic(test_data):
    """Test basic collection listing for authenticated user."""
    response = client.get("/api/v1/collection", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    assert data["total_count"] == 3  # All items for user1
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) == 3

    # Check first item structure
    item = data["items"][0]
    assert "id" in item
    assert "user_id" in item
    assert "game" in item
    assert "platform" in item
    assert "acquisition_type" in item
    assert "is_active" in item
    assert "playthroughs" in item
    assert "created_at" in item
    assert "updated_at" in item


def test_list_collection_with_is_active_filter(test_data):
    """Test filtering by is_active status."""
    # Get active items only
    response = client.get("/api/v1/collection?is_active=true", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # col1 and col2 are active

    # Get inactive items only
    response = client.get("/api/v1/collection?is_active=false", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # col3 is inactive


def test_list_collection_with_platform_filter(test_data):
    """Test filtering by platform."""
    response = client.get("/api/v1/collection?platform=PC", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # game1 and game3 on PC

    response = client.get("/api/v1/collection?platform=PS5", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # game2 on PS5


def test_list_collection_with_acquisition_type_filter(test_data):
    """Test filtering by acquisition type."""
    response = client.get("/api/v1/collection?acquisition_type=DIGITAL", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # game1 and game3 are digital

    response = client.get("/api/v1/collection?acquisition_type=PHYSICAL", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # game2 is physical


def test_list_collection_with_priority_filter(test_data):
    """Test filtering by priority."""
    response = client.get("/api/v1/collection?priority=1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only game1 has priority 1


def test_list_collection_with_search(test_data):
    """Test search functionality."""
    # Search in game title
    response = client.get("/api/v1/collection?search=witcher", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert data["items"][0]["game"]["title"] == "The Witcher 3"

    # Search in notes
    response = client.get("/api/v1/collection?search=souls-like", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert data["items"][0]["game"]["title"] == "Elden Ring"


def test_list_collection_sorting(test_data):
    """Test sorting functionality."""
    # Sort by updated_at descending (newest first)
    response = client.get(
        "/api/v1/collection?sort_by=updated_at&sort_order=desc",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be ordered: game3 (2023-03-01), game2 (2023-02-01), game1 (2023-01-01)
    titles = [item["game"]["title"] for item in data["items"]]
    assert titles == ["Hollow Knight", "Elden Ring", "The Witcher 3"]

    # Sort by updated_at ascending (oldest first)
    response = client.get(
        "/api/v1/collection?sort_by=updated_at&sort_order=asc",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()

    titles = [item["game"]["title"] for item in data["items"]]
    assert titles == ["The Witcher 3", "Elden Ring", "Hollow Knight"]


def test_list_collection_pagination(test_data):
    """Test pagination functionality."""
    # Get first page with limit 2
    response = client.get(
        "/api/v1/collection?limit=2&offset=0&sort_by=updated_at&sort_order=asc",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) == 2

    # Get second page
    response = client.get(
        "/api/v1/collection?limit=2&offset=2&sort_by=updated_at&sort_order=asc",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 3
    assert data["limit"] == 2
    assert data["offset"] == 2
    assert len(data["items"]) == 1  # Only 1 item left


def test_list_collection_with_playthroughs(test_data):
    """Test that collection items include playthrough data."""
    response = client.get("/api/v1/collection", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()

    # Find The Witcher 3 item (should have 1 playthrough)
    witcher_item = next(item for item in data["items"] if item["game"]["title"] == "The Witcher 3")

    assert len(witcher_item["playthroughs"]) == 1
    playthrough = witcher_item["playthroughs"][0]
    assert playthrough["status"] == "COMPLETED"
    assert playthrough["platform"] == "PC"
    assert playthrough["play_time_hours"] == 150.5
    assert playthrough["rating"] == 9


def test_list_collection_user_isolation(test_data):
    """Test that users only see their own collection items."""
    # User1's collection
    response = client.get("/api/v1/collection", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    user1_data = response.json()
    assert user1_data["total_count"] == 3

    # User2's collection
    response = client.get("/api/v1/collection", headers={"X-User-Id": "user2"})
    assert response.status_code == 200
    user2_data = response.json()
    assert user2_data["total_count"] == 1

    # User3 (no collection)
    response = client.get("/api/v1/collection", headers={"X-User-Id": "user3"})
    assert response.status_code == 200
    user3_data = response.json()
    assert user3_data["total_count"] == 0
    assert user3_data["items"] == []


def test_list_collection_multiple_filters(test_data):
    """Test combining multiple filters."""
    response = client.get(
        "/api/v1/collection?platform=PC&is_active=true&acquisition_type=DIGITAL",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only game1 matches all filters
    assert data["items"][0]["game"]["title"] == "The Witcher 3"


def test_list_collection_filters_applied_in_response(test_data):
    """Test that applied filters are included in the response."""
    response = client.get(
        "/api/v1/collection?platform=PC&priority=1&search=witcher&sort_by=priority&sort_order=asc",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()

    filters = data["filters_applied"]
    assert filters["platform"] == "PC"
    assert filters["priority"] == 1
    assert filters["search"] == "witcher"
    assert filters["sort_by"] == "priority"
    assert filters["sort_order"] == "asc"
    assert filters["acquisition_type"] is None  # Not specified
    assert filters["is_active"] is None  # Not specified


def test_list_collection_invalid_parameters(test_data):
    """Test validation of query parameters."""
    # Invalid sort_order
    response = client.get("/api/v1/collection?sort_order=invalid", headers={"X-User-Id": "user1"})
    assert response.status_code == 422

    # Invalid priority (out of range)
    response = client.get("/api/v1/collection?priority=10", headers={"X-User-Id": "user1"})
    assert response.status_code == 422

    # Invalid limit (too high)
    response = client.get("/api/v1/collection?limit=1000", headers={"X-User-Id": "user1"})
    assert response.status_code == 422


# ===== POST /collection tests =====


def test_create_collection_item_requires_auth():
    """Test that collection creation endpoint requires authentication."""
    response = client.post(
        "/api/v1/collection",
        json={"game_id": "game1", "platform": "PC", "acquisition_type": "DIGITAL"},
    )
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_create_collection_item_success(test_data):
    """Test successful collection item creation."""
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={
            "game_id": "game1",
            "platform": "Switch",  # New platform for game1
            "acquisition_type": "PHYSICAL",
            "priority": 2,
            "notes": "Birthday gift",
        },
    )
    assert response.status_code == 201

    data = response.json()
    assert data["user_id"] == "user1"
    assert data["game"]["id"] == "game1"
    assert data["game"]["title"] == "The Witcher 3"
    assert data["platform"] == "Switch"
    assert data["acquisition_type"] == "PHYSICAL"
    assert data["priority"] == 2
    assert data["is_active"] is True
    assert data["notes"] == "Birthday gift"
    assert data["playthroughs"] == []  # No playthroughs for new item
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_collection_item_minimal_data(test_data):
    """Test collection creation with only required fields."""
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={"game_id": "game2", "platform": "Switch", "acquisition_type": "DIGITAL"},
    )
    assert response.status_code == 201

    data = response.json()
    assert data["user_id"] == "user1"
    assert data["game"]["id"] == "game2"
    assert data["platform"] == "Switch"
    assert data["acquisition_type"] == "DIGITAL"
    assert data["priority"] is None
    assert data["notes"] is None
    assert data["acquired_at"] is None


def test_create_collection_item_with_acquired_at(test_data):
    """Test collection creation with acquired_at timestamp."""
    acquired_at = "2023-12-25T10:00:00Z"
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={
            "game_id": "game3",
            "platform": "Switch",
            "acquisition_type": "PHYSICAL",
            "acquired_at": acquired_at,
            "priority": 1,
            "notes": "Christmas present",
        },
    )
    assert response.status_code == 201

    data = response.json()
    assert data["acquired_at"] == acquired_at
    assert data["priority"] == 1
    assert data["notes"] == "Christmas present"


def test_create_collection_item_duplicate_conflict(test_data):
    """Test that creating a duplicate item returns 409 conflict."""
    # Try to create item that already exists (user1, game1, PC)
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={
            "game_id": "game1",
            "platform": "PC",  # This combination already exists
            "acquisition_type": "DIGITAL",
        },
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["message"].lower()


def test_create_collection_item_nonexistent_game(test_data):
    """Test creating collection item for non-existent game returns 404."""
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={
            "game_id": "nonexistent-game",
            "platform": "PC",
            "acquisition_type": "DIGITAL",
        },
    )
    assert response.status_code == 404
    assert "Game not found" in response.json()["message"]


def test_create_collection_item_invalid_priority(test_data):
    """Test validation of priority field."""
    # Priority too low
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={
            "game_id": "game1",
            "platform": "Switch",
            "acquisition_type": "DIGITAL",
            "priority": 0,
        },
    )
    assert response.status_code == 422

    # Priority too high
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={
            "game_id": "game1",
            "platform": "Switch",
            "acquisition_type": "DIGITAL",
            "priority": 6,
        },
    )
    assert response.status_code == 422


def test_create_collection_item_invalid_acquisition_type(test_data):
    """Test validation of acquisition_type enum."""
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={"game_id": "game1", "platform": "PC", "acquisition_type": "INVALID_TYPE"},
    )
    assert response.status_code == 422


def test_create_collection_item_missing_required_fields(test_data):
    """Test that missing required fields return 422."""
    # Missing game_id
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={"platform": "PC", "acquisition_type": "DIGITAL"},
    )
    assert response.status_code == 422

    # Missing platform
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={"game_id": "game1", "acquisition_type": "DIGITAL"},
    )
    assert response.status_code == 422

    # Missing acquisition_type
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user1"},
        json={"game_id": "game1", "platform": "PC"},
    )
    assert response.status_code == 422


def test_create_collection_item_user_isolation(test_data):
    """Test that different users can create items for the same game+platform."""
    # User1 already has game1 on PC, but user2 should be able to create it
    response = client.post(
        "/api/v1/collection",
        headers={"X-User-Id": "user2"},
        json={
            "game_id": "game1",
            "platform": "PC",  # Same as user1's existing item
            "acquisition_type": "SUBSCRIPTION",
            "notes": "Game Pass",
        },
    )
    assert response.status_code == 201

    data = response.json()
    assert data["user_id"] == "user2"
    assert data["game"]["id"] == "game1"
    assert data["platform"] == "PC"
    assert data["acquisition_type"] == "SUBSCRIPTION"


def test_create_collection_item_all_acquisition_types(test_data):
    """Test creating items with all valid acquisition types."""
    acquisition_types = ["PHYSICAL", "DIGITAL", "SUBSCRIPTION", "BORROWED", "RENTAL"]

    for i, acq_type in enumerate(acquisition_types):
        response = client.post(
            "/api/v1/collection",
            headers={"X-User-Id": "user3"},  # Clean user
            json={
                "game_id": f"game{(i % 3) + 1}",  # Cycle through available games
                "platform": f"Platform{i}",  # Unique platform for each
                "acquisition_type": acq_type,
                "priority": (i % 5) + 1,
            },
        )
        assert response.status_code == 201

        data = response.json()
        assert data["acquisition_type"] == acq_type
        assert data["priority"] == (i % 5) + 1


# ===== GET /collection/{id} tests =====


def test_get_collection_item_requires_auth():
    """Test that collection get endpoint requires authentication."""
    response = client.get("/api/v1/collection/col1")
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_get_collection_item_success(test_data):
    """Test successful retrieval of collection item."""
    response = client.get("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "col1"
    assert data["user_id"] == "user1"
    assert data["game"]["id"] == "game1"
    assert data["game"]["title"] == "The Witcher 3"
    assert data["platform"] == "PC"
    assert data["acquisition_type"] == "DIGITAL"
    assert data["priority"] == 1
    assert data["is_active"] is True
    assert data["notes"] == "Great RPG"
    assert len(data["playthroughs"]) == 1  # Has one playthrough
    assert data["playthroughs"][0]["status"] == "COMPLETED"
    assert "created_at" in data
    assert "updated_at" in data


def test_get_collection_item_with_playthroughs(test_data):
    """Test that collection item includes complete playthrough data."""
    response = client.get("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    playthrough = data["playthroughs"][0]
    assert playthrough["id"] == "pt1"
    assert playthrough["status"] == "COMPLETED"
    assert playthrough["platform"] == "PC"
    assert playthrough["play_time_hours"] == 150.5
    assert playthrough["rating"] == 9
    # Note: started_at and completed_at are not set in test data, so they should be None


def test_get_collection_item_without_playthroughs(test_data):
    """Test collection item that has no playthroughs."""
    response = client.get("/api/v1/collection/col3", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "col3"
    assert data["game"]["title"] == "Hollow Knight"
    assert data["playthroughs"] == []  # No playthroughs


def test_get_collection_item_not_found(test_data):
    """Test 404 when collection item doesn't exist."""
    response = client.get("/api/v1/collection/nonexistent", headers={"X-User-Id": "user1"})
    assert response.status_code == 404
    assert "Collection item not found" in response.json()["message"]


def test_get_collection_item_wrong_user(test_data):
    """Test that users can't access other users' collection items."""
    # user1's collection item, but accessed by user2
    response = client.get("/api/v1/collection/col1", headers={"X-User-Id": "user2"})
    assert response.status_code == 404
    assert "Collection item not found" in response.json()["message"]


def test_get_collection_item_user_isolation(test_data):
    """Test proper user isolation - users only see their own items."""
    # User1 can see their own items
    response = client.get("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user1"

    response = client.get("/api/v1/collection/col2", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user1"

    # User2 can see their own items
    response = client.get("/api/v1/collection/col4", headers={"X-User-Id": "user2"})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user2"

    # But user2 cannot see user1's items
    response = client.get("/api/v1/collection/col1", headers={"X-User-Id": "user2"})
    assert response.status_code == 404


def test_get_collection_item_includes_all_game_details(test_data):
    """Test that response includes full game details."""
    response = client.get("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    game = data["game"]
    assert game["id"] == "game1"
    assert game["title"] == "The Witcher 3"
    assert game["cover_image_id"] == "tw3_cover"
    assert game["igdb_id"] == 1942
    # description, release_date, hltb_id, steam_app_id should be None in test data
    assert game["description"] is None
    assert game["release_date"] is None
    assert game["hltb_id"] is None
    assert game["steam_app_id"] is None


def test_get_collection_item_inactive_item(test_data):
    """Test that inactive collection items can still be retrieved."""
    response = client.get("/api/v1/collection/col3", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "col3"
    assert data["is_active"] is False
    assert data["game"]["title"] == "Hollow Knight"


def test_get_collection_item_all_fields_present(test_data):
    """Test that response includes all expected fields."""
    response = client.get("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()

    # Collection item fields
    required_fields = [
        "id",
        "user_id",
        "platform",
        "acquisition_type",
        "is_active",
        "created_at",
        "updated_at",
        "game",
        "playthroughs",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Optional fields that might be None
    optional_fields = ["acquired_at", "priority", "notes"]
    for field in optional_fields:
        assert field in data, f"Missing optional field: {field}"

    # Game fields
    game_fields = [
        "id",
        "title",
        "cover_image_id",
        "release_date",
        "description",
        "igdb_id",
        "hltb_id",
        "steam_app_id",
    ]
    for field in game_fields:
        assert field in data["game"], f"Missing game field: {field}"


# ===== PUT /collection/{id} tests =====


def test_update_collection_item_requires_auth():
    """Test that collection update endpoint requires authentication."""
    response = client.put("/api/v1/collection/col1", json={"priority": 3})
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_update_collection_item_success(test_data):
    """Test successful update of collection item."""
    update_data = {
        "acquisition_type": "PHYSICAL",
        "priority": 3,
        "notes": "Updated notes",
        "is_active": False,
    }

    response = client.put("/api/v1/collection/col1", headers={"X-User-Id": "user1"}, json=update_data)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "col1"
    assert data["user_id"] == "user1"
    assert data["acquisition_type"] == "PHYSICAL"  # Updated
    assert data["priority"] == 3  # Updated
    assert data["notes"] == "Updated notes"  # Updated
    assert data["is_active"] is False  # Updated

    # Immutable fields should remain unchanged
    assert data["game"]["id"] == "game1"
    assert data["platform"] == "PC"

    # Check that updated_at was updated
    assert "updated_at" in data


def test_update_collection_item_partial_update(test_data):
    """Test updating only some fields."""
    response = client.put(
        "/api/v1/collection/col2",
        headers={"X-User-Id": "user1"},
        json={"priority": 1},  # Only update priority
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "col2"
    assert data["priority"] == 1  # Updated

    # Other fields should remain unchanged
    assert data["acquisition_type"] == "PHYSICAL"  # Original value
    assert data["notes"] == "Souls-like masterpiece"  # Original value
    assert data["is_active"] is True  # Original value


def test_update_collection_item_no_changes(test_data):
    """Test update with no actual changes (all fields None or not provided)."""
    response = client.put(
        "/api/v1/collection/col1",
        headers={"X-User-Id": "user1"},
        json={},  # No fields to update
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "col1"
    # Should return current values unchanged
    assert data["acquisition_type"] == "DIGITAL"
    assert data["priority"] == 1
    assert data["notes"] == "Great RPG"


def test_update_collection_item_acquired_at(test_data):
    """Test updating acquired_at timestamp."""
    acquired_at = "2024-01-15T14:30:00Z"
    response = client.put(
        "/api/v1/collection/col1",
        headers={"X-User-Id": "user1"},
        json={"acquired_at": acquired_at},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["acquired_at"] == acquired_at


def test_update_collection_item_notes_to_null(test_data):
    """Test setting notes to empty/null."""
    response = client.put("/api/v1/collection/col1", headers={"X-User-Id": "user1"}, json={"notes": ""})
    assert response.status_code == 200

    data = response.json()
    assert data["notes"] == ""


def test_update_collection_item_not_found(test_data):
    """Test 404 when collection item doesn't exist."""
    response = client.put(
        "/api/v1/collection/nonexistent",
        headers={"X-User-Id": "user1"},
        json={"priority": 2},
    )
    assert response.status_code == 404
    assert "Collection item not found" in response.json()["message"]


def test_update_collection_item_wrong_user(test_data):
    """Test that users can't update other users' collection items."""
    response = client.put(
        "/api/v1/collection/col1",  # user1's item
        headers={"X-User-Id": "user2"},  # accessed by user2
        json={"priority": 5},
    )
    assert response.status_code == 404
    assert "Collection item not found" in response.json()["message"]


def test_update_collection_item_invalid_priority(test_data):
    """Test validation of priority field."""
    # Priority too low
    response = client.put("/api/v1/collection/col1", headers={"X-User-Id": "user1"}, json={"priority": 0})
    assert response.status_code == 422

    # Priority too high
    response = client.put("/api/v1/collection/col1", headers={"X-User-Id": "user1"}, json={"priority": 6})
    assert response.status_code == 422


def test_update_collection_item_invalid_acquisition_type(test_data):
    """Test validation of acquisition_type enum."""
    response = client.put(
        "/api/v1/collection/col1",
        headers={"X-User-Id": "user1"},
        json={"acquisition_type": "INVALID_TYPE"},
    )
    assert response.status_code == 422


def test_update_collection_item_all_acquisition_types(test_data):
    """Test updating to all valid acquisition types."""
    acquisition_types = ["PHYSICAL", "DIGITAL", "SUBSCRIPTION", "BORROWED", "RENTAL"]

    for acq_type in acquisition_types:
        response = client.put(
            "/api/v1/collection/col1",
            headers={"X-User-Id": "user1"},
            json={"acquisition_type": acq_type},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["acquisition_type"] == acq_type


def test_update_collection_item_preserves_playthroughs(test_data):
    """Test that update preserves existing playthrough data."""
    response = client.put("/api/v1/collection/col1", headers={"X-User-Id": "user1"}, json={"priority": 4})
    assert response.status_code == 200

    data = response.json()
    assert data["priority"] == 4  # Updated
    # Should still have the playthrough
    assert len(data["playthroughs"]) == 1
    assert data["playthroughs"][0]["id"] == "pt1"
    assert data["playthroughs"][0]["status"] == "COMPLETED"


def test_update_collection_item_user_isolation(test_data):
    """Test proper user isolation during updates."""
    # User1 can update their own items
    response = client.put("/api/v1/collection/col1", headers={"X-User-Id": "user1"}, json={"priority": 2})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user1"
    assert response.json()["priority"] == 2

    # User2 can update their own items
    response = client.put("/api/v1/collection/col4", headers={"X-User-Id": "user2"}, json={"priority": 3})
    assert response.status_code == 200
    assert response.json()["user_id"] == "user2"
    assert response.json()["priority"] == 3

    # But user2 cannot update user1's items
    response = client.put("/api/v1/collection/col1", headers={"X-User-Id": "user2"}, json={"priority": 5})
    assert response.status_code == 404


def test_update_collection_item_all_fields_present(test_data):
    """Test that response includes all expected fields after update."""
    response = client.put(
        "/api/v1/collection/col1",
        headers={"X-User-Id": "user1"},
        json={"priority": 5, "notes": "Updated"},
    )
    assert response.status_code == 200

    data = response.json()

    # Collection item fields
    required_fields = [
        "id",
        "user_id",
        "platform",
        "acquisition_type",
        "is_active",
        "created_at",
        "updated_at",
        "game",
        "playthroughs",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Optional fields
    optional_fields = ["acquired_at", "priority", "notes"]
    for field in optional_fields:
        assert field in data, f"Missing optional field: {field}"


# ===== DELETE /collection/{id} tests =====


def test_delete_collection_item_requires_auth():
    """Test that collection delete endpoint requires authentication."""
    response = client.delete("/api/v1/collection/col1")
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_delete_collection_item_soft_delete_success(test_data):
    """Test successful soft delete of collection item."""
    # Verify item exists and is active before deletion (use col2 which is active)
    response = client.get("/api/v1/collection/col2", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    assert response.json()["is_active"] is True

    # Perform soft delete (default behavior)
    response = client.delete("/api/v1/collection/col2", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Collection item soft deleted"
    assert data["id"] == "col2"
    assert data["is_active"] is False  # Should be set to false

    # Verify item still exists but is inactive when fetched
    response = client.get("/api/v1/collection/col2", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_delete_collection_item_hard_delete_success(test_data):
    """Test successful hard delete of collection item."""
    # Verify item exists before deletion (use col3 which has no playthroughs)
    response = client.get("/api/v1/collection/col3", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    # Perform hard delete
    response = client.delete("/api/v1/collection/col3?hard_delete=true", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Collection item permanently deleted"
    assert data["id"] == "col3"

    # Verify item no longer exists
    response = client.get("/api/v1/collection/col3", headers={"X-User-Id": "user1"})
    assert response.status_code == 404


def test_delete_collection_item_not_found(test_data):
    """Test 404 when collection item doesn't exist."""
    response = client.delete("/api/v1/collection/nonexistent", headers={"X-User-Id": "user1"})
    assert response.status_code == 404
    assert "Collection item not found" in response.json()["message"]


def test_delete_collection_item_wrong_user(test_data):
    """Test that users can't delete other users' collection items."""
    response = client.delete(
        "/api/v1/collection/col1",  # user1's item
        headers={"X-User-Id": "user2"},  # accessed by user2
    )
    assert response.status_code == 404
    assert "Collection item not found" in response.json()["message"]


def test_delete_collection_item_hard_delete_with_playthroughs_fails(test_data):
    """Test that hard delete fails when collection item has associated playthroughs."""
    # col1 has a playthrough (pt1), so hard delete should fail
    response = client.delete("/api/v1/collection/col1?hard_delete=true", headers={"X-User-Id": "user1"})
    assert response.status_code == 409
    assert "Cannot hard delete: collection item has associated playthroughs" in response.json()["message"]

    # Verify item still exists
    response = client.get("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_delete_collection_item_soft_delete_with_playthroughs_succeeds(test_data):
    """Test that soft delete succeeds even when collection item has associated playthroughs."""
    # col1 has a playthrough (pt1), but soft delete should succeed
    response = client.delete("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Collection item soft deleted"
    assert data["id"] == "col1"
    assert data["is_active"] is False

    # Verify item still exists but is inactive
    response = client.get("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    assert response.json()["is_active"] is False
    # Playthroughs should still be accessible
    assert len(response.json()["playthroughs"]) == 1


def test_delete_collection_item_already_soft_deleted(test_data):
    """Test deleting an already soft-deleted item."""
    # First soft delete (use col1 since col2 and col3 are used by other tests)
    response = client.delete("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    # Try to delete again
    response = client.delete("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    assert response.json()["message"] == "Collection item soft deleted"
    assert response.json()["is_active"] is False


def test_delete_collection_item_hard_delete_no_playthroughs(test_data):
    """Test hard delete succeeds when no associated playthroughs exist."""
    # col3 has no playthroughs, so hard delete should work
    response = client.delete("/api/v1/collection/col3?hard_delete=true", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Collection item permanently deleted"
    assert data["id"] == "col3"

    # Verify item no longer exists
    response = client.get("/api/v1/collection/col3", headers={"X-User-Id": "user1"})
    assert response.status_code == 404


def test_delete_collection_item_user_isolation(test_data):
    """Test proper user isolation during deletions."""
    # User1 can delete their own items
    response = client.delete("/api/v1/collection/col1", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    # User2 can delete their own items
    response = client.delete("/api/v1/collection/col4", headers={"X-User-Id": "user2"})
    assert response.status_code == 200

    # But user2 cannot delete user1's remaining items
    response = client.delete("/api/v1/collection/col2", headers={"X-User-Id": "user2"})
    assert response.status_code == 404


def test_delete_collection_item_query_param_variations(test_data):
    """Test different query parameter formats for hard_delete."""
    # Test hard_delete=false (explicit soft delete)
    response = client.delete("/api/v1/collection/col2?hard_delete=false", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    assert response.json()["message"] == "Collection item soft deleted"
    assert response.json()["is_active"] is False

    # Test hard_delete=True (case insensitive)
    response = client.delete("/api/v1/collection/col3?hard_delete=True", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    assert response.json()["message"] == "Collection item permanently deleted"


# ===== POST /collection/bulk tests =====


def test_bulk_collection_operations_requires_auth():
    """Test that bulk operations endpoint requires authentication."""
    response = client.post(
        "/api/v1/collection/bulk",
        json={
            "action": "update_priority",
            "collection_ids": ["col1", "col2"],
            "data": {"priority": 1},
        },
    )
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_bulk_update_priority_all_success(test_data):
    """Test bulk priority update when all operations succeed."""
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "update_priority",
            "collection_ids": ["col1", "col2"],
            "data": {"priority": 5},
        },
    )
    assert response.status_code == 200  # All operations successful

    data = response.json()
    assert data["success"] is True
    assert data["updated_count"] == 2
    assert data["total_count"] == 2
    assert len(data["results"]) == 2

    # Check each result
    for result in data["results"]:
        assert result["success"] is True
        assert result["error"] is None
        assert result["updated_data"]["priority"] == 5
        assert result["id"] in ["col1", "col2"]


def test_bulk_update_priority_partial_success(test_data):
    """Test bulk priority update with partial success (some items not found)."""
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "update_priority",
            "collection_ids": ["col1", "nonexistent", "col2"],
            "data": {"priority": 3},
        },
    )
    assert response.status_code == 207  # Multi-Status for partial success

    data = response.json()
    assert data["success"] is False  # Not all successful
    assert data["updated_count"] == 2  # Only col1 and col2 updated
    assert data["total_count"] == 3  # 3 items attempted
    assert len(data["results"]) == 3

    # Check successful results
    successful_results = [r for r in data["results"] if r["success"]]
    failed_results = [r for r in data["results"] if not r["success"]]

    assert len(successful_results) == 2
    assert len(failed_results) == 1

    # Failed result should be the nonexistent one
    failed_result = failed_results[0]
    assert failed_result["id"] == "nonexistent"
    assert "not found" in failed_result["error"].lower()


def test_bulk_update_platform_all_success(test_data):
    """Test bulk platform update when all operations succeed."""
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "update_platform",
            "collection_ids": [
                "col1",
                "col3",
            ],  # col3 is inactive but should still be updatable
            "data": {"platform": "Xbox"},
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["updated_count"] == 2
    assert data["total_count"] == 2

    # Verify the updates by getting the items
    for col_id in ["col1", "col3"]:
        response = client.get(f"/api/v1/collection/{col_id}", headers={"X-User-Id": "user1"})
        assert response.status_code == 200
        assert response.json()["platform"] == "Xbox"


def test_bulk_hide_all_success(test_data):
    """Test bulk hide (soft delete) operation when all succeed."""
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={"action": "hide", "collection_ids": ["col1", "col2"]},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["updated_count"] == 2
    assert data["total_count"] == 2

    # Verify items are hidden
    for col_id in ["col1", "col2"]:
        response = client.get(f"/api/v1/collection/{col_id}", headers={"X-User-Id": "user1"})
        assert response.status_code == 200
        assert response.json()["is_active"] is False


def test_bulk_activate_all_success(test_data):
    """Test bulk activate operation when all succeed."""
    # First hide col1 and col2
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={"action": "hide", "collection_ids": ["col1", "col2"]},
    )
    assert response.status_code == 200

    # Now activate them back
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "activate",
            "collection_ids": ["col1", "col2", "col3"],  # col3 was already inactive
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["updated_count"] == 3
    assert data["total_count"] == 3

    # Verify items are active
    for col_id in ["col1", "col2", "col3"]:
        response = client.get(f"/api/v1/collection/{col_id}", headers={"X-User-Id": "user1"})
        assert response.status_code == 200
        assert response.json()["is_active"] is True


def test_bulk_operations_user_isolation(test_data):
    """Test that users can only perform bulk operations on their own items."""
    # user1 tries to update user2's item (col4) along with their own
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "update_priority",
            "collection_ids": ["col1", "col4"],  # col4 belongs to user2
            "data": {"priority": 2},
        },
    )
    assert response.status_code == 207  # Partial success

    data = response.json()
    assert data["success"] is False
    assert data["updated_count"] == 1  # Only col1 updated
    assert data["total_count"] == 2

    # Check that col4 was not found/updated
    failed_results = [r for r in data["results"] if not r["success"]]
    assert len(failed_results) == 1
    assert failed_results[0]["id"] == "col4"


def test_bulk_operations_empty_collection_ids(test_data):
    """Test validation when collection_ids is empty."""
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "update_priority",
            "collection_ids": [],
            "data": {"priority": 2},
        },
    )
    assert response.status_code == 422  # Validation error


def test_bulk_operations_invalid_action(test_data):
    """Test validation with invalid action."""
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "invalid_action",
            "collection_ids": ["col1"],
            "data": {"priority": 2},
        },
    )
    assert response.status_code == 422


def test_bulk_update_priority_invalid_data(test_data):
    """Test validation when priority data is invalid."""
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "update_priority",
            "collection_ids": ["col1"],
            "data": {"priority": 10},  # Invalid priority (must be 1-5)
        },
    )
    assert response.status_code == 207  # Partial success - validation happens per item

    data = response.json()
    assert data["success"] is False
    assert data["updated_count"] == 0
    assert data["total_count"] == 1

    failed_result = data["results"][0]
    assert failed_result["success"] is False
    assert "priority" in failed_result["error"].lower()


def test_bulk_update_priority_missing_data(test_data):
    """Test when required data is missing for update_priority."""
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "update_priority",
            "collection_ids": ["col1"],
            "data": {},  # Missing priority
        },
    )
    assert response.status_code == 400  # Bad request for missing required data


def test_bulk_update_platform_missing_data(test_data):
    """Test when required data is missing for update_platform."""
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "update_platform",
            "collection_ids": ["col1"],
            "data": {},  # Missing platform
        },
    )
    assert response.status_code == 400  # Bad request for missing required data


def test_bulk_hide_activate_no_data_required(test_data):
    """Test that hide and activate actions don't require data parameter."""
    # Hide should work without data
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={"action": "hide", "collection_ids": ["col1"]},
    )
    assert response.status_code == 200

    # Activate should work without data
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={"action": "activate", "collection_ids": ["col1"]},
    )
    assert response.status_code == 200


def test_bulk_operations_all_not_found(test_data):
    """Test when all collection IDs are not found or not owned."""
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "update_priority",
            "collection_ids": ["nonexistent1", "nonexistent2"],
            "data": {"priority": 3},
        },
    )
    assert response.status_code == 207  # Multi-status

    data = response.json()
    assert data["success"] is False
    assert data["updated_count"] == 0
    assert data["total_count"] == 2
    assert len(data["results"]) == 2

    # All results should be failures
    for result in data["results"]:
        assert result["success"] is False
        assert "not found" in result["error"].lower()


def test_bulk_operations_large_batch(test_data):
    """Test bulk operations with many items (test performance/batching)."""
    # Create additional test items for user1
    from app.db_models import CollectionItem
    from app.schemas import AcquisitionType
    from app.db import SessionLocal

    with SessionLocal() as db:
        # Create additional collection items
        additional_items = []
        for i in range(4, 8):  # col4-col7 (col4 is used by user2, so let's use col5-col8)
            col_id = f"col{i+1}"
            item = CollectionItem(
                id=col_id,
                user_id="user1",
                game_id="game1",  # Reuse existing game
                platform=f"Platform{i}",
                acquisition_type=AcquisitionType.DIGITAL.value,
                priority=i % 5 + 1,
                is_active=True,
                created_at=datetime(2023, 1, i, tzinfo=timezone.utc),
                updated_at=datetime(2023, 1, i, tzinfo=timezone.utc),
            )
            additional_items.append(item)
            db.add(item)
        db.commit()

    # Now test bulk operation with many IDs
    all_col_ids = ["col1", "col2", "col3", "col5", "col6", "col7", "col8"]
    response = client.post(
        "/api/v1/collection/bulk",
        headers={"X-User-Id": "user1"},
        json={
            "action": "update_priority",
            "collection_ids": all_col_ids,
            "data": {"priority": 4},
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["updated_count"] == 7
    assert data["total_count"] == 7
    assert len(data["results"]) == 7


# ===== GET /collection/stats tests =====


def test_collection_stats_requires_auth():
    """Test that collection stats endpoint requires authentication."""
    response = client.get("/api/v1/collection/stats")
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_collection_stats_success(test_data):
    """Test successful retrieval of collection statistics."""
    response = client.get("/api/v1/collection/stats", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()

    # Check basic structure
    assert "total_games" in data
    assert "by_platform" in data
    assert "by_acquisition_type" in data
    assert "by_priority" in data

    # Check deterministic values based on test data
    # user1 has 3 items: col1 (Witcher3/PC/DIGITAL/priority=1), col2 (Elden Ring/PS5/PHYSICAL/priority=2), col3 (Hollow Knight/PC/DIGITAL/priority=3/inactive)
    assert data["total_games"] == 3

    # Platform counts
    assert data["by_platform"]["PC"] == 2  # col1, col3
    assert data["by_platform"]["PS5"] == 1  # col2

    # Acquisition type counts
    assert data["by_acquisition_type"]["DIGITAL"] == 2  # col1, col3
    assert data["by_acquisition_type"]["PHYSICAL"] == 1  # col2

    # Priority counts (as strings since they're dict keys)
    assert data["by_priority"]["1"] == 1  # col1
    assert data["by_priority"]["2"] == 1  # col2
    assert data["by_priority"]["3"] == 1  # col3


def test_collection_stats_empty_collection():
    """Test collection stats for user with no collection items."""
    response = client.get("/api/v1/collection/stats", headers={"X-User-Id": "user3"})
    assert response.status_code == 200

    data = response.json()
    assert data["total_games"] == 0
    assert data["by_platform"] == {}
    assert data["by_acquisition_type"] == {}
    assert data["by_priority"] == {}


def test_collection_stats_user_isolation(test_data):
    """Test that stats only include user's own items."""
    # user2 has 1 item: col4 (Witcher3/Xbox/SUBSCRIPTION/priority=1)
    response = client.get("/api/v1/collection/stats", headers={"X-User-Id": "user2"})
    assert response.status_code == 200

    data = response.json()
    assert data["total_games"] == 1
    assert data["by_platform"]["Xbox"] == 1
    assert data["by_acquisition_type"]["SUBSCRIPTION"] == 1
    assert data["by_priority"]["1"] == 1


def test_collection_stats_includes_inactive_items(test_data):
    """Test that stats include inactive items by default."""
    response = client.get("/api/v1/collection/stats", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    # Should include all 3 items (including inactive col3)
    assert data["total_games"] == 3


def test_collection_stats_with_null_priority(test_data):
    """Test stats handling of items with null priority."""
    # Create a collection item with null priority for testing
    from app.db_models import CollectionItem
    from app.schemas import AcquisitionType
    from app.db import SessionLocal

    with SessionLocal() as db:
        # Add item with null priority
        item = CollectionItem(
            id="col_null_priority",
            user_id="user1",
            game_id="game1",
            platform="Nintendo Switch",
            acquisition_type=AcquisitionType.BORROWED.value,
            priority=None,  # Null priority
            is_active=True,
            created_at=datetime(2023, 1, 10, tzinfo=timezone.utc),
            updated_at=datetime(2023, 1, 10, tzinfo=timezone.utc),
        )
        db.add(item)
        db.commit()

    response = client.get("/api/v1/collection/stats", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    # Should now have 4 items
    assert data["total_games"] == 4

    # Check null priority is counted
    assert "null" in data["by_priority"]
    assert data["by_priority"]["null"] == 1

    # Check new platform and acquisition type
    assert data["by_platform"]["Nintendo Switch"] == 1
    assert data["by_acquisition_type"]["BORROWED"] == 1


def test_collection_stats_recent_additions(test_data):
    """Test that recent additions are included and sorted by acquired_at."""
    # Create items with specific acquired_at dates
    from app.db_models import CollectionItem
    from app.schemas import AcquisitionType
    from app.db import SessionLocal

    with SessionLocal() as db:
        # Add items with acquired_at dates
        recent_items = []
        for i, (game_id, platform, acq_date) in enumerate(
            [
                (
                    "game1",
                    "Steam",
                    datetime(2024, 3, 20, tzinfo=timezone.utc),
                ),  # Most recent
                ("game2", "Epic", datetime(2024, 3, 15, tzinfo=timezone.utc)),  # Middle
                ("game3", "GOG", datetime(2024, 3, 10, tzinfo=timezone.utc)),  # Oldest
            ]
        ):
            item = CollectionItem(
                id=f"col_recent_{i}",
                user_id="user1",
                game_id=game_id,
                platform=platform,
                acquisition_type=AcquisitionType.DIGITAL.value,
                acquired_at=acq_date,
                priority=1,
                is_active=True,
                created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
            recent_items.append(item)
            db.add(item)
        db.commit()

    response = client.get("/api/v1/collection/stats", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()

    # Check recent_additions exist and are sorted by acquired_at desc
    assert "recent_additions" in data
    recent = data["recent_additions"]
    assert len(recent) >= 3

    # Should be sorted by acquired_at descending (most recent first)
    # The first item should be from Steam (2024-03-20)
    assert recent[0]["platform"] == "Steam"
    assert recent[0]["game"]["title"] == "The Witcher 3"  # game1


def test_collection_stats_aggregation_accuracy(test_data):
    """Test that all aggregations are mathematically correct."""
    # Add more diverse data to test aggregations
    from app.db_models import CollectionItem
    from app.schemas import AcquisitionType
    from app.db import SessionLocal

    test_items = [
        ("game1", "PS4", AcquisitionType.PHYSICAL, 1),
        ("game2", "PS4", AcquisitionType.DIGITAL, 2),  # Different game same platform
        ("game2", "Xbox", AcquisitionType.SUBSCRIPTION, None),
        ("game3", "Steam", AcquisitionType.RENTAL, 5),  # Use Steam to avoid PC conflict
    ]

    with SessionLocal() as db:
        for i, (game_id, platform, acq_type, priority) in enumerate(test_items):
            item = CollectionItem(
                id=f"col_agg_test_{i}",
                user_id="user1",
                game_id=game_id,
                platform=platform,
                acquisition_type=acq_type.value,
                priority=priority,
                is_active=True,
                created_at=datetime(2023, 1, i + 20, tzinfo=timezone.utc),
                updated_at=datetime(2023, 1, i + 20, tzinfo=timezone.utc),
            )
            db.add(item)
        db.commit()

    response = client.get("/api/v1/collection/stats", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()

    # Total should be original 3 + 4 new = 7
    assert data["total_games"] == 7

    # Platform verification
    expected_platforms = {
        "PC": 2,  # original col1, col3
        "PS5": 1,  # original col2
        "PS4": 2,  # two new PS4 items
        "Xbox": 1,  # one new Xbox item
        "Steam": 1,  # one new Steam item
    }
    for platform, expected_count in expected_platforms.items():
        assert data["by_platform"][platform] == expected_count, f"Platform {platform} count mismatch"

    # Acquisition type verification
    expected_acquisition = {
        "DIGITAL": 3,  # original col1, col3 + new PS4 digital
        "PHYSICAL": 2,  # original col2 + new PS4 physical
        "SUBSCRIPTION": 1,  # new Xbox item
        "RENTAL": 1,  # new Steam item
    }
    for acq_type, expected_count in expected_acquisition.items():
        assert data["by_acquisition_type"][acq_type] == expected_count, f"Acquisition type {acq_type} count mismatch"

    # Priority verification
    expected_priorities = {
        "1": 2,  # original col1 + new PS4 physical
        "2": 2,  # original col2 + new PS4 digital
        "3": 1,  # original col3
        "5": 1,  # new Steam item
        "null": 1,  # new Xbox item
    }
    for priority, expected_count in expected_priorities.items():
        assert data["by_priority"][priority] == expected_count, f"Priority {priority} count mismatch"


def test_collection_stats_all_fields_present(test_data):
    """Test that response includes all expected fields."""
    response = client.get("/api/v1/collection/stats", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()

    # Required fields
    required_fields = [
        "total_games",
        "by_platform",
        "by_acquisition_type",
        "by_priority",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Optional fields that should be present
    optional_fields = ["value_estimate", "recent_additions"]
    for field in optional_fields:
        # These may be None/empty but should be present in response
        assert field in data, f"Missing optional field: {field}"
