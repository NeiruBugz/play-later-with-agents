from datetime import datetime, timezone, date
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db import get_db, SessionLocal
from app.db_models import Game, CollectionItem, Playthrough
from app.schemas import AcquisitionType, PlaythroughStatus

client = TestClient(app)

# Ensure tables exist
from app.db import Base

Base.metadata.create_all(bind=SessionLocal.kw["bind"])


@pytest.fixture
def test_data():
    """Create test data for playthrough tests."""
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
                release_date=date(2015, 5, 19),
                igdb_id=1942,
            ),
            Game(
                id="game2",
                title="Elden Ring",
                cover_image_id="er_cover",
                release_date=date(2022, 2, 25),
                igdb_id=119171,
            ),
            Game(
                id="game3",
                title="Hollow Knight",
                cover_image_id="hk_cover",
                release_date=date(2017, 2, 24),
                igdb_id=26286,
            ),
            Game(
                id="game4",
                title="Cyberpunk 2077",
                cover_image_id="cp2077_cover",
                release_date=date(2020, 12, 10),
                igdb_id=1877,
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
        ]

        # Create test playthroughs
        playthroughs = [
            # Completed playthrough for user1
            Playthrough(
                id="pt1",
                user_id="user1",
                game_id="game1",
                collection_id="col1",
                status=PlaythroughStatus.COMPLETED.value,
                platform="PC",
                started_at=datetime(2023, 1, 15, tzinfo=timezone.utc),
                completed_at=datetime(2023, 3, 20, tzinfo=timezone.utc),
                play_time_hours=120.5,
                playthrough_type="First Run",
                difficulty="Normal",
                rating=9,
                notes="Amazing story and world",
                created_at=datetime(2023, 1, 15, tzinfo=timezone.utc),
                updated_at=datetime(2023, 3, 20, tzinfo=timezone.utc),
            ),
            # Currently playing playthrough for user1
            Playthrough(
                id="pt2",
                user_id="user1",
                game_id="game2",
                collection_id="col2",
                status=PlaythroughStatus.PLAYING.value,
                platform="PS5",
                started_at=datetime(2023, 2, 10, tzinfo=timezone.utc),
                play_time_hours=45.0,
                playthrough_type="First Run",
                difficulty="Hard",
                notes="Challenging but rewarding",
                created_at=datetime(2023, 2, 10, tzinfo=timezone.utc),
                updated_at=datetime(2023, 2, 15, tzinfo=timezone.utc),
            ),
            # Planning playthrough for user1
            Playthrough(
                id="pt3",
                user_id="user1",
                game_id="game3",
                collection_id=None,  # No collection item
                status=PlaythroughStatus.PLANNING.value,
                platform="Steam",
                playthrough_type="100% Run",
                difficulty="Normal",
                notes="Want to get all achievements",
                created_at=datetime(2023, 3, 1, tzinfo=timezone.utc),
                updated_at=datetime(2023, 3, 1, tzinfo=timezone.utc),
            ),
            # Dropped playthrough for user1
            Playthrough(
                id="pt4",
                user_id="user1",
                game_id="game4",
                collection_id=None,
                status=PlaythroughStatus.DROPPED.value,
                platform="PC",
                started_at=datetime(2022, 12, 15, tzinfo=timezone.utc),
                play_time_hours=5.0,
                playthrough_type="First Run",
                difficulty="Normal",
                notes="Too many bugs at launch",
                created_at=datetime(2022, 12, 15, tzinfo=timezone.utc),
                updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            ),
            # On hold playthrough for user1
            Playthrough(
                id="pt5",
                user_id="user1",
                game_id="game1",
                collection_id="col1",
                status=PlaythroughStatus.ON_HOLD.value,
                platform="PC",
                started_at=datetime(2023, 4, 1, tzinfo=timezone.utc),
                play_time_hours=15.0,
                playthrough_type="New Game+",
                difficulty="Death March",
                notes="Taking a break, too difficult",
                created_at=datetime(2023, 4, 1, tzinfo=timezone.utc),
                updated_at=datetime(2023, 4, 10, tzinfo=timezone.utc),
            ),
            # Playthrough for different user (user2)
            Playthrough(
                id="pt6",
                user_id="user2",
                game_id="game1",
                collection_id=None,
                status=PlaythroughStatus.PLAYING.value,
                platform="Xbox",
                started_at=datetime(2023, 3, 15, tzinfo=timezone.utc),
                play_time_hours=30.0,
                playthrough_type="First Run",
                difficulty="Normal",
                rating=8,
                notes="Playing on Game Pass",
                created_at=datetime(2023, 3, 15, tzinfo=timezone.utc),
                updated_at=datetime(2023, 3, 18, tzinfo=timezone.utc),
            ),
        ]

        # Add all data to database in correct order
        for game in games:
            db.add(game)
        db.commit()

        for item in collection_items:
            db.add(item)
        db.commit()

        for pt in playthroughs:
            db.add(pt)
        db.commit()

    yield

    # Cleanup after test
    with SessionLocal() as db:
        db.query(Playthrough).delete()
        db.query(CollectionItem).delete()
        db.query(Game).delete()
        db.commit()


def test_list_playthroughs_requires_auth():
    """Test that playthroughs endpoint requires authentication."""
    response = client.get("/api/v1/playthroughs")
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_list_playthroughs_basic(test_data):
    """Test basic playthroughs listing for authenticated user."""
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user1"})
    assert response.status_code == 200

    data = response.json()
    assert data["total_count"] == 5  # All playthroughs for user1
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) == 5

    # Check first item structure
    item = data["items"][0]
    assert "id" in item
    assert "user_id" in item
    assert "game" in item
    assert "collection" in item
    assert "status" in item
    assert "platform" in item
    assert "created_at" in item
    assert "updated_at" in item

    # Verify game details are included
    game = item["game"]
    assert "id" in game
    assert "title" in game
    assert "cover_image_id" in game
    assert "release_date" in game
    assert "main_story" in game


def test_list_playthroughs_with_status_filter(test_data):
    """Test filtering by playthrough status."""
    # Filter by COMPLETED status
    response = client.get(
        "/api/v1/playthroughs?status=COMPLETED", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1 is completed
    assert data["items"][0]["status"] == "COMPLETED"

    # Filter by PLAYING status
    response = client.get(
        "/api/v1/playthroughs?status=PLAYING", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt2 is playing
    assert data["items"][0]["status"] == "PLAYING"

    # Filter by multiple statuses
    response = client.get(
        "/api/v1/playthroughs?status=COMPLETED&status=PLAYING",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt1 and pt2


def test_list_playthroughs_with_platform_filter(test_data):
    """Test filtering by platform."""
    # Filter by PC platform
    response = client.get(
        "/api/v1/playthroughs?platform=PC", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 3  # pt1, pt4, pt5 are on PC

    # Filter by PS5 platform
    response = client.get(
        "/api/v1/playthroughs?platform=PS5", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt2 is on PS5

    # Filter by multiple platforms
    response = client.get(
        "/api/v1/playthroughs?platform=PC&platform=Steam",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 4  # pt1, pt3, pt4, pt5


def test_list_playthroughs_with_rating_filter(test_data):
    """Test filtering by rating range."""
    # Filter by minimum rating
    response = client.get(
        "/api/v1/playthroughs?rating_min=8", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1 has rating 9

    # Filter by maximum rating
    response = client.get(
        "/api/v1/playthroughs?rating_max=9", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1 has rating

    # Filter by rating range
    response = client.get(
        "/api/v1/playthroughs?rating_min=8&rating_max=10",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1


def test_list_playthroughs_with_play_time_filter(test_data):
    """Test filtering by play time range."""
    # Filter by minimum play time
    response = client.get(
        "/api/v1/playthroughs?play_time_min=40", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt1 (120.5) and pt2 (45.0)

    # Filter by maximum play time
    response = client.get(
        "/api/v1/playthroughs?play_time_max=20", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt4 (5.0) and pt5 (15.0)

    # Filter by play time range
    response = client.get(
        "/api/v1/playthroughs?play_time_min=10&play_time_max=50",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt2 (45.0) and pt5 (15.0)


def test_list_playthroughs_with_difficulty_filter(test_data):
    """Test filtering by difficulty."""
    # Filter by Normal difficulty
    response = client.get(
        "/api/v1/playthroughs?difficulty=Normal", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 3  # pt1, pt3, pt4

    # Filter by Hard difficulty
    response = client.get(
        "/api/v1/playthroughs?difficulty=Hard", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt2

    # Filter by multiple difficulties
    response = client.get(
        "/api/v1/playthroughs?difficulty=Normal&difficulty=Death March",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 4  # pt1, pt3, pt4, pt5


def test_list_playthroughs_with_playthrough_type_filter(test_data):
    """Test filtering by playthrough type."""
    # Filter by First Run
    response = client.get(
        "/api/v1/playthroughs?playthrough_type=First Run",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 3  # pt1, pt2, pt4

    # Filter by New Game+
    response = client.get(
        "/api/v1/playthroughs?playthrough_type=New Game%2B",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt5


def test_list_playthroughs_with_date_filters(test_data):
    """Test filtering by start and completion dates."""
    # Filter by started after
    response = client.get(
        "/api/v1/playthroughs?started_after=2023-02-01", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt2, pt5 (pt3 has no started_at)

    # Filter by started before
    response = client.get(
        "/api/v1/playthroughs?started_before=2023-01-20", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt1, pt4

    # Filter by completed after
    response = client.get(
        "/api/v1/playthroughs?completed_after=2023-03-01",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1

    # Filter by completed before
    response = client.get(
        "/api/v1/playthroughs?completed_before=2023-12-31",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1


def test_list_playthroughs_with_search(test_data):
    """Test search functionality in game titles and notes."""
    # Search in game title
    response = client.get(
        "/api/v1/playthroughs?search=witcher", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt1 and pt5 (both Witcher 3)

    # Search in notes
    response = client.get(
        "/api/v1/playthroughs?search=challenging", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt2

    # Search in both
    response = client.get(
        "/api/v1/playthroughs?search=bugs", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt4


def test_list_playthroughs_sorting(test_data):
    """Test sorting functionality."""
    # Sort by updated_at descending (default)
    response = client.get(
        "/api/v1/playthroughs?sort_by=updated_at&sort_order=desc",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be ordered by updated_at desc: pt5, pt1, pt2, pt3, pt4
    first_item = data["items"][0]
    assert first_item["id"] == "pt5"  # Most recently updated

    # Sort by play_time_hours ascending
    response = client.get(
        "/api/v1/playthroughs?sort_by=play_time_hours&sort_order=asc",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()

    # Items with play_time should come first, sorted ascending
    # pt4 (5.0), pt5 (15.0), pt2 (45.0), pt1 (120.5), then pt3 (null)
    assert data["items"][0]["play_time_hours"] == 5.0  # pt4
    assert data["items"][1]["play_time_hours"] == 15.0  # pt5


def test_list_playthroughs_pagination(test_data):
    """Test pagination functionality."""
    # Get first page with limit 2
    response = client.get(
        "/api/v1/playthroughs?limit=2&offset=0&sort_by=updated_at&sort_order=desc",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert len(data["items"]) == 2

    # Get second page
    response = client.get(
        "/api/v1/playthroughs?limit=2&offset=2&sort_by=updated_at&sort_order=desc",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 2
    assert len(data["items"]) == 2


def test_list_playthroughs_user_isolation(test_data):
    """Test that users only see their own playthroughs."""
    # User1's playthroughs
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    user1_data = response.json()
    assert user1_data["total_count"] == 5

    # User2's playthroughs
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user2"})
    assert response.status_code == 200
    user2_data = response.json()
    assert user2_data["total_count"] == 1

    # User3 (no playthroughs)
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user3"})
    assert response.status_code == 200
    user3_data = response.json()
    assert user3_data["total_count"] == 0
    assert user3_data["items"] == []


def test_list_playthroughs_multiple_filters(test_data):
    """Test combining multiple filters."""
    response = client.get(
        "/api/v1/playthroughs?status=COMPLETED&platform=PC&rating_min=8",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1 matches all filters
    assert data["items"][0]["id"] == "pt1"


def test_list_playthroughs_filters_applied_in_response(test_data):
    """Test that applied filters are included in the response."""
    response = client.get(
        "/api/v1/playthroughs?status=COMPLETED&platform=PC&rating_min=8&search=amazing&sort_by=rating&sort_order=desc",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 200
    data = response.json()

    filters = data["filters_applied"]
    assert filters["status"] == ["COMPLETED"]
    assert filters["platform"] == ["PC"]
    assert filters["rating_min"] == 8
    assert filters["search"] == "amazing"
    assert filters["sort_by"] == "rating"
    assert filters["sort_order"] == "desc"
    # Null/unspecified filters
    assert filters["rating_max"] is None
    assert filters["play_time_min"] is None


def test_list_playthroughs_invalid_parameters(test_data):
    """Test validation of query parameters."""
    # Invalid sort_order
    response = client.get(
        "/api/v1/playthroughs?sort_order=invalid", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 422

    # Invalid rating range (min > max)
    response = client.get(
        "/api/v1/playthroughs?rating_min=8&rating_max=5", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 422

    # Invalid limit (too high)
    response = client.get(
        "/api/v1/playthroughs?limit=1000", headers={"X-User-Id": "user1"}
    )
    assert response.status_code == 422

    # Invalid date format
    response = client.get(
        "/api/v1/playthroughs?started_after=invalid-date",
        headers={"X-User-Id": "user1"},
    )
    assert response.status_code == 422


def test_list_playthroughs_collection_details(test_data):
    """Test that collection details are included when available."""
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user1"})
    assert response.status_code == 200
    data = response.json()

    # Find playthroughs with collection details
    pt1_item = next(item for item in data["items"] if item["id"] == "pt1")
    assert pt1_item["collection"] is not None
    assert pt1_item["collection"]["id"] == "col1"
    assert pt1_item["collection"]["platform"] == "PC"
    assert pt1_item["collection"]["acquisition_type"] == "DIGITAL"

    # Find playthrough without collection
    pt3_item = next(item for item in data["items"] if item["id"] == "pt3")
    assert pt3_item["collection"] is None
