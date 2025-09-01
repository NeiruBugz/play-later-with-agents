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
    response = client.get(
        "/api/v1/collection?is_active=true", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # col1 and col2 are active

    # Get inactive items only
    response = client.get(
        "/api/v1/collection?is_active=false", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # col3 is inactive


def test_list_collection_with_platform_filter(test_data):
    """Test filtering by platform."""
    response = client.get(
        "/api/v1/collection?platform=PC", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # game1 and game3 on PC

    response = client.get(
        "/api/v1/collection?platform=PS5", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # game2 on PS5


def test_list_collection_with_acquisition_type_filter(test_data):
    """Test filtering by acquisition type."""
    response = client.get(
        "/api/v1/collection?acquisition_type=DIGITAL", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # game1 and game3 are digital

    response = client.get(
        "/api/v1/collection?acquisition_type=PHYSICAL", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # game2 is physical


def test_list_collection_with_priority_filter(test_data):
    """Test filtering by priority."""
    response = client.get(
        "/api/v1/collection?priority=1", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only game1 has priority 1


def test_list_collection_with_search(test_data):
    """Test search functionality."""
    # Search in game title
    response = client.get(
        "/api/v1/collection?search=witcher", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1
    assert data["items"][0]["game"]["title"] == "The Witcher 3"

    # Search in notes
    response = client.get(
        "/api/v1/collection?search=souls-like", headers={"X-User-Id": "user1"}
    )
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
    witcher_item = next(
        item for item in data["items"] if item["game"]["title"] == "The Witcher 3"
    )

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
    response = client.get(
        "/api/v1/collection?sort_order=invalid", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 422

    # Invalid priority (out of range)
    response = client.get(
        "/api/v1/collection?priority=10", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 422

    # Invalid limit (too high)
    response = client.get(
        "/api/v1/collection?limit=1000", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 422
