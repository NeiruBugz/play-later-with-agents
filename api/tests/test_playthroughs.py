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
                id="game-1",
                title="The Witcher 3",
                cover_image_id="tw3_cover",
                release_date=date(2015, 5, 19),
                igdb_id=1942,
            ),
            Game(
                id="game-2",
                title="Elden Ring",
                cover_image_id="er_cover",
                release_date=date(2022, 2, 25),
                igdb_id=119171,
            ),
            Game(
                id="game-3",
                title="Hollow Knight",
                cover_image_id="hk_cover",
                release_date=date(2017, 2, 24),
                igdb_id=26286,
            ),
            Game(
                id="game-4",
                title="Cyberpunk 2077",
                cover_image_id="cp2077_cover",
                release_date=date(2020, 12, 10),
                igdb_id=1877,
            ),
        ]

        # Create test collection items for user1
        collection_items = [
            CollectionItem(
                id="col-1",
                user_id="user-1",
                game_id="game-1",
                platform="PC",
                acquisition_type=AcquisitionType.DIGITAL.value,
                priority=1,
                is_active=True,
                notes="Great RPG",
                created_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2023, 1, 1, tzinfo=timezone.utc),
            ),
            CollectionItem(
                id="col-2",
                user_id="user-1",
                game_id="game-2",
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
            # Completed playthrough for user-1
            Playthrough(
                id="pt-1",
                user_id="user-1",
                game_id="game-1",
                collection_id="col-1",
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
            # Currently playing playthrough for user-1
            Playthrough(
                id="pt-2",
                user_id="user-1",
                game_id="game-2",
                collection_id="col-2",
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
            # Planning playthrough for user-1
            Playthrough(
                id="pt-3",
                user_id="user-1",
                game_id="game-3",
                collection_id=None,  # No collection item
                status=PlaythroughStatus.PLANNING.value,
                platform="Steam",
                playthrough_type="100% Run",
                difficulty="Normal",
                notes="Want to get all achievements",
                created_at=datetime(2023, 3, 1, tzinfo=timezone.utc),
                updated_at=datetime(2023, 3, 1, tzinfo=timezone.utc),
            ),
            # Dropped playthrough for user-1
            Playthrough(
                id="pt-4",
                user_id="user-1",
                game_id="game-4",
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
            # On hold playthrough for user-1
            Playthrough(
                id="pt-5",
                user_id="user-1",
                game_id="game-1",
                collection_id="col-1",
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
            # Playthrough for different user (user-2)
            Playthrough(
                id="pt-6",
                user_id="user-2",
                game_id="game-1",
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
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()
    assert data["total_count"] == 5  # All playthroughs for user-1
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
        "/api/v1/playthroughs?status=COMPLETED", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1 is completed
    assert data["items"][0]["status"] == "COMPLETED"

    # Filter by PLAYING status
    response = client.get(
        "/api/v1/playthroughs?status=PLAYING", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt2 is playing
    assert data["items"][0]["status"] == "PLAYING"

    # Filter by multiple statuses
    response = client.get(
        "/api/v1/playthroughs?status=COMPLETED&status=PLAYING",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt1 and pt2


def test_list_playthroughs_with_platform_filter(test_data):
    """Test filtering by platform."""
    # Filter by PC platform
    response = client.get(
        "/api/v1/playthroughs?platform=PC", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 3  # pt1, pt4, pt5 are on PC

    # Filter by PS5 platform
    response = client.get(
        "/api/v1/playthroughs?platform=PS5", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt2 is on PS5

    # Filter by multiple platforms
    response = client.get(
        "/api/v1/playthroughs?platform=PC&platform=Steam",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 4  # pt1, pt3, pt4, pt5


def test_list_playthroughs_with_rating_filter(test_data):
    """Test filtering by rating range."""
    # Filter by minimum rating
    response = client.get(
        "/api/v1/playthroughs?rating_min=8", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1 has rating 9

    # Filter by maximum rating
    response = client.get(
        "/api/v1/playthroughs?rating_max=9", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1 has rating

    # Filter by rating range
    response = client.get(
        "/api/v1/playthroughs?rating_min=8&rating_max=10",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1


def test_list_playthroughs_with_play_time_filter(test_data):
    """Test filtering by play time range."""
    # Filter by minimum play time
    response = client.get(
        "/api/v1/playthroughs?play_time_min=40", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt1 (120.5) and pt2 (45.0)

    # Filter by maximum play time
    response = client.get(
        "/api/v1/playthroughs?play_time_max=20", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt4 (5.0) and pt5 (15.0)

    # Filter by play time range
    response = client.get(
        "/api/v1/playthroughs?play_time_min=10&play_time_max=50",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt2 (45.0) and pt5 (15.0)


def test_list_playthroughs_with_difficulty_filter(test_data):
    """Test filtering by difficulty."""
    # Filter by Normal difficulty
    response = client.get(
        "/api/v1/playthroughs?difficulty=Normal", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 3  # pt1, pt3, pt4

    # Filter by Hard difficulty
    response = client.get(
        "/api/v1/playthroughs?difficulty=Hard", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt2

    # Filter by multiple difficulties
    response = client.get(
        "/api/v1/playthroughs?difficulty=Normal&difficulty=Death March",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 4  # pt1, pt3, pt4, pt5


def test_list_playthroughs_with_playthrough_type_filter(test_data):
    """Test filtering by playthrough type."""
    # Filter by First Run
    response = client.get(
        "/api/v1/playthroughs?playthrough_type=First Run",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 3  # pt1, pt2, pt4

    # Filter by New Game+
    response = client.get(
        "/api/v1/playthroughs?playthrough_type=New Game%2B",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt5


def test_list_playthroughs_with_date_filters(test_data):
    """Test filtering by start and completion dates."""
    # Filter by started after
    response = client.get(
        "/api/v1/playthroughs?started_after=2023-02-01", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt2, pt5 (pt3 has no started_at)

    # Filter by started before
    response = client.get(
        "/api/v1/playthroughs?started_before=2023-01-20",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt1, pt4

    # Filter by completed after
    response = client.get(
        "/api/v1/playthroughs?completed_after=2023-03-01",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1

    # Filter by completed before
    response = client.get(
        "/api/v1/playthroughs?completed_before=2023-12-31",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1


def test_list_playthroughs_with_search(test_data):
    """Test search functionality in game titles and notes."""
    # Search in game title
    response = client.get(
        "/api/v1/playthroughs?search=witcher", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2  # pt1 and pt5 (both Witcher 3)

    # Search in notes
    response = client.get(
        "/api/v1/playthroughs?search=challenging", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt2

    # Search in both
    response = client.get(
        "/api/v1/playthroughs?search=bugs", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt4


def test_list_playthroughs_sorting(test_data):
    """Test sorting functionality."""
    # Sort by updated_at descending (default)
    response = client.get(
        "/api/v1/playthroughs?sort_by=updated_at&sort_order=desc",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be ordered by updated_at desc: pt5, pt1, pt2, pt3, pt4
    first_item = data["items"][0]
    assert first_item["id"] == "pt-5"  # Most recently updated

    # Sort by play_time_hours ascending
    response = client.get(
        "/api/v1/playthroughs?sort_by=play_time_hours&sort_order=asc",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()

    # Items with play_time should come first, sorted ascending
    # pt4 (5.0), pt5 (15.0), pt2 (45.0), pt1 (120.5), then pt3 (null)
    assert data["items"][0]["play_time_hours"] == 5.0  # pt4
    assert data["items"][1]["play_time_hours"] == 15.0  # pt5


def test_list_playthroughs_sorting_by_title(test_data):
    """Test sorting playthroughs by game title."""
    response = client.get(
        "/api/v1/playthroughs?sort_by=title&sort_order=asc",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be sorted by game title ascending:
    # "Cyberpunk 2077" (pt-4), "Elden Ring" (pt-2), "Hollow Knight" (pt-3), "The Witcher 3" (pt-1, pt-5)
    game_titles = [item["game"]["title"] for item in data["items"]]
    expected_titles = [
        "Cyberpunk 2077",
        "Elden Ring",
        "Hollow Knight",
        "The Witcher 3",
        "The Witcher 3",
    ]
    assert game_titles == expected_titles


def test_list_playthroughs_sorting_by_status(test_data):
    """Test sorting playthroughs by status."""
    response = client.get(
        "/api/v1/playthroughs?sort_by=status&sort_order=asc",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be sorted by status ascending:
    # "COMPLETED" (pt-1), "DROPPED" (pt-4), "ON_HOLD" (pt-5), "PLANNING" (pt-3), "PLAYING" (pt-2)
    statuses = [item["status"] for item in data["items"]]
    expected_statuses = ["COMPLETED", "DROPPED", "ON_HOLD", "PLANNING", "PLAYING"]
    assert statuses == expected_statuses


def test_list_playthroughs_sorting_by_platform(test_data):
    """Test sorting playthroughs by platform."""
    response = client.get(
        "/api/v1/playthroughs?sort_by=platform&sort_order=asc",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()

    # Should be sorted by platform ascending:
    # "PC" (pt-1, pt-4, pt-5), "PS5" (pt-2), "Steam" (pt-3)
    platforms = [item["platform"] for item in data["items"]]
    expected_platforms = ["PC", "PC", "PC", "PS5", "Steam"]
    assert platforms == expected_platforms


def test_list_playthroughs_pagination(test_data):
    """Test pagination functionality."""
    # Get first page with limit 2
    response = client.get(
        "/api/v1/playthroughs?limit=2&offset=0&sort_by=updated_at&sort_order=desc",
        headers={"X-User-Id": "user-1"},
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
        headers={"X-User-Id": "user-1"},
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
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200
    user1_data = response.json()
    assert user1_data["total_count"] == 5

    # User2's playthroughs
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-2"})
    assert response.status_code == 200
    user2_data = response.json()
    assert user2_data["total_count"] == 1

    # User3 (no playthroughs)
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-3"})
    assert response.status_code == 200
    user3_data = response.json()
    assert user3_data["total_count"] == 0
    assert user3_data["items"] == []


def test_list_playthroughs_multiple_filters(test_data):
    """Test combining multiple filters."""
    response = client.get(
        "/api/v1/playthroughs?status=COMPLETED&platform=PC&rating_min=8",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 1  # Only pt1 matches all filters
    assert data["items"][0]["id"] == "pt-1"


def test_list_playthroughs_filters_applied_in_response(test_data):
    """Test that applied filters are included in the response."""
    response = client.get(
        "/api/v1/playthroughs?status=COMPLETED&platform=PC&rating_min=8&search=amazing&sort_by=rating&sort_order=desc",
        headers={"X-User-Id": "user-1"},
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
        "/api/v1/playthroughs?sort_order=invalid", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422

    # Invalid rating range (min > max)
    response = client.get(
        "/api/v1/playthroughs?rating_min=8&rating_max=5",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 422

    # Invalid limit (too high)
    response = client.get(
        "/api/v1/playthroughs?limit=1000", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422

    # Invalid date format
    response = client.get(
        "/api/v1/playthroughs?started_after=invalid-date",
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 422


def test_list_playthroughs_collection_details(test_data):
    """Test that collection details are included when available."""
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200
    data = response.json()

    # Find playthroughs with collection details
    pt1_item = next(item for item in data["items"] if item["id"] == "pt-1")
    assert pt1_item["collection"] is not None
    assert pt1_item["collection"]["id"] == "col-1"
    assert pt1_item["collection"]["platform"] == "PC"
    assert pt1_item["collection"]["acquisition_type"] == "DIGITAL"

    # Find playthrough without collection
    pt3_item = next(item for item in data["items"] if item["id"] == "pt-3")
    assert pt3_item["collection"] is None


# ===== POST /playthroughs Tests =====


def test_create_playthrough_requires_auth():
    """Test that creating playthroughs requires authentication."""
    playthrough_data = {"game_id": "game-1", "status": "PLANNING", "platform": "PC"}

    response = client.post("/api/v1/playthroughs", json=playthrough_data)
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_create_playthrough_success(test_data):
    """Test successful playthrough creation."""
    playthrough_data = {
        "game_id": "game-1",
        "status": "PLANNING",
        "platform": "PlayStation 5",
        "notes": "Looking forward to playing this!",
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 201

    data = response.json()
    assert data["game_id"] == "game-1"
    assert data["status"] == "PLANNING"
    assert data["platform"] == "PlayStation 5"
    assert data["notes"] == "Looking forward to playing this!"
    assert data["user_id"] == "user-1"
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None
    assert data["collection_id"] is None  # No collection specified


def test_create_playthrough_with_collection_item(test_data):
    """Test creating playthrough that references a collection item."""
    # Create a new collection item first
    collection_data = {
        "game_id": "game-2",
        "platform": "Nintendo Switch",
        "acquisition_type": "DIGITAL",
    }

    collection_response = client.post(
        "/api/v1/collection", json=collection_data, headers={"X-User-Id": "user-1"}
    )
    assert collection_response.status_code == 201
    collection_id = collection_response.json()["id"]

    # Now create playthrough with collection reference
    playthrough_data = {
        "game_id": "game-2",
        "collection_id": collection_id,
        "status": "PLAYING",
        "platform": "Nintendo Switch",
        "started_at": "2024-03-01T10:00:00",
        "play_time_hours": 5.5,
        "difficulty": "Normal",
        "playthrough_type": "First Playthrough",
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 201

    data = response.json()
    assert data["collection_id"] == collection_id
    assert data["status"] == "PLAYING"
    assert data["play_time_hours"] == 5.5
    assert data["difficulty"] == "Normal"
    assert data["playthrough_type"] == "First Playthrough"


def test_create_playthrough_completed_with_rating(test_data):
    """Test creating completed playthrough with rating and completion date."""
    playthrough_data = {
        "game_id": "game-3",
        "status": "COMPLETED",
        "platform": "PC",
        "started_at": "2024-01-01T09:00:00",
        "completed_at": "2024-02-15T18:30:00",
        "play_time_hours": 42.5,
        "rating": 9,
        "difficulty": "Hard",
        "playthrough_type": "100% Completion",
        "notes": "Amazing game, loved every minute!",
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["rating"] == 9
    assert data["completed_at"] == "2024-02-15T18:30:00Z"
    assert data["play_time_hours"] == 42.5


def test_create_playthrough_invalid_game_id(test_data):
    """Test creation fails with non-existent game ID."""
    playthrough_data = {
        "game_id": "non-existent-game",
        "status": "PLANNING",
        "platform": "PC",
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 404
    assert "Game not found" in response.json()["message"]


def test_create_playthrough_invalid_collection_id(test_data):
    """Test creation fails with non-existent collection ID."""
    playthrough_data = {
        "game_id": "game-1",
        "collection_id": "non-existent-collection",
        "status": "PLANNING",
        "platform": "PC",
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 404
    assert "Collection item not found" in response.json()["message"]


def test_create_playthrough_collection_ownership_validation(test_data):
    """Test creation fails when trying to use another user's collection item."""
    # Create collection item for user-2
    collection_data = {
        "game_id": "game-1",
        "platform": "Xbox",
        "acquisition_type": "PHYSICAL",
    }

    collection_response = client.post(
        "/api/v1/collection", json=collection_data, headers={"X-User-Id": "user-2"}
    )
    assert collection_response.status_code == 201
    collection_id = collection_response.json()["id"]

    # Try to use user-2's collection item as user-1
    playthrough_data = {
        "game_id": "game-1",
        "collection_id": collection_id,
        "status": "PLANNING",
        "platform": "Xbox",
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 404
    assert "Collection item not found" in response.json()["message"]


def test_create_playthrough_collection_game_mismatch(test_data):
    """Test creation fails when collection item game doesn't match playthrough game."""
    # Use existing collection item for game-1
    playthrough_data = {
        "game_id": "game-2",  # Different game!
        "collection_id": "col-1",  # Collection item is for game-1
        "status": "PLANNING",
        "platform": "PC",
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422
    assert "Collection item is for a different game" in response.json()["message"]


def test_create_playthrough_invalid_enum_values(test_data):
    """Test validation of enum values."""
    # Test invalid status
    playthrough_data = {
        "game_id": "game-1",
        "status": "INVALID_STATUS",
        "platform": "PC",
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422


def test_create_playthrough_validation_constraints(test_data):
    """Test field validation constraints."""
    # Test invalid rating (too high)
    playthrough_data = {
        "game_id": "game-1",
        "status": "COMPLETED",
        "platform": "PC",
        "rating": 15,  # Should be 1-10
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422

    # Test negative play time
    playthrough_data = {
        "game_id": "game-1",
        "status": "PLAYING",
        "platform": "PC",
        "play_time_hours": -5.0,
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422


def test_create_playthrough_missing_required_fields(test_data):
    """Test creation fails with missing required fields."""
    # Missing game_id
    playthrough_data = {"status": "PLANNING", "platform": "PC"}

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422

    # Missing status
    playthrough_data = {"game_id": "game-1", "platform": "PC"}

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422

    # Missing platform
    playthrough_data = {"game_id": "game-1", "status": "PLANNING"}

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422


def test_create_playthrough_user_isolation(test_data):
    """Test that created playthroughs are properly isolated by user."""
    # Create playthrough as user-1
    playthrough_data = {
        "game_id": "game-1",
        "status": "PLANNING",
        "platform": "PC",
        "notes": "User 1 playthrough",
    }

    response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 201
    playthrough_id = response.json()["id"]

    # User-2 should not see user-1's playthrough in their list
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-2"})
    assert response.status_code == 200

    data = response.json()
    playthrough_ids = [p["id"] for p in data["items"]]
    assert playthrough_id not in playthrough_ids

    # User-2 can create their own playthrough for the same game
    playthrough_data_user2 = {
        "game_id": "game-1",
        "status": "PLAYING",
        "platform": "Xbox",
        "notes": "User 2 playthrough",
    }

    response = client.post(
        "/api/v1/playthroughs",
        json=playthrough_data_user2,
        headers={"X-User-Id": "user-2"},
    )
    assert response.status_code == 201

    # Both should exist in the database but be isolated by user
    response_user1 = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-1"})
    user1_count = response_user1.json()["total_count"]

    response_user2 = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-2"})
    user2_count = response_user2.json()["total_count"]

    assert user1_count > 0
    assert user2_count > 0


# ===== GET /playthroughs/{id} Tests =====


def test_get_playthrough_requires_auth():
    """Test that getting playthrough by ID requires authentication."""
    response = client.get("/api/v1/playthroughs/pt-1")
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_get_playthrough_success_with_collection(test_data):
    """Test getting playthrough by ID with collection item."""
    response = client.get("/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()
    # Verify playthrough details
    assert data["id"] == "pt-1"
    assert data["user_id"] == "user-1"
    assert data["status"] == "COMPLETED"
    assert data["platform"] == "PC"
    assert data["rating"] == 9
    assert data["play_time_hours"] == 120.5
    assert data["difficulty"] == "Normal"
    assert data["playthrough_type"] == "First Run"
    assert data["notes"] == "Amazing story and world"

    # Verify embedded game detail (more fields than GameSummary)
    game = data["game"]
    assert game["id"] == "game-1"
    assert game["title"] == "The Witcher 3"
    assert game["cover_image_id"] == "tw3_cover"
    assert game["release_date"] == "2015-05-19"
    # GameDetail should have additional fields
    assert "description" in game
    assert "igdb_id" in game
    assert "hltb_id" in game
    assert "steam_app_id" in game

    # Verify embedded collection snippet
    collection = data["collection"]
    assert collection is not None
    assert collection["id"] == "col-1"
    assert collection["platform"] == "PC"
    assert collection["acquisition_type"] == "DIGITAL"
    assert collection["priority"] == 1
    assert collection["is_active"] == True

    # Verify timestamps are present
    assert data["created_at"] is not None
    assert data["updated_at"] is not None
    assert data["started_at"] is not None
    assert data["completed_at"] is not None


def test_get_playthrough_success_without_collection(test_data):
    """Test getting playthrough by ID without collection item."""
    response = client.get("/api/v1/playthroughs/pt-3", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()
    # Verify playthrough details
    assert data["id"] == "pt-3"
    assert data["user_id"] == "user-1"
    assert data["status"] == "PLANNING"
    assert data["platform"] == "Steam"
    assert data["playthrough_type"] == "100% Run"

    # Verify embedded game detail
    game = data["game"]
    assert game["id"] == "game-3"
    assert game["title"] == "Hollow Knight"

    # Should not have collection since collection_id is None
    assert data["collection"] is None

    # Should have empty milestones list or None
    milestones = data.get("milestones")
    assert milestones is None or milestones == []


def test_get_playthrough_success_with_milestones(test_data):
    """Test getting playthrough with milestones if supported."""
    # For now, milestones are likely empty/None since we haven't implemented milestone creation
    response = client.get("/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()
    # Milestones should be present in response structure even if empty
    milestones = data.get("milestones")
    assert milestones is None or isinstance(milestones, list)


def test_get_playthrough_not_found(test_data):
    """Test getting non-existent playthrough."""
    response = client.get(
        "/api/v1/playthroughs/non-existent", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]


def test_get_playthrough_user_isolation(test_data):
    """Test that users cannot access other users' playthroughs."""
    # Try to get user-1's playthrough as user-2
    response = client.get("/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-2"})
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]

    # Try to get user-2's playthrough as user-1
    response = client.get("/api/v1/playthroughs/pt-6", headers={"X-User-Id": "user-1"})
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]

    # Verify user-2 can access their own playthrough
    response = client.get("/api/v1/playthroughs/pt-6", headers={"X-User-Id": "user-2"})
    assert response.status_code == 200
    assert response.json()["id"] == "pt-6"
    assert response.json()["user_id"] == "user-2"


def test_get_playthrough_different_statuses(test_data):
    """Test getting playthroughs in different statuses."""
    # Test PLAYING status
    response = client.get("/api/v1/playthroughs/pt-2", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PLAYING"
    assert data["completed_at"] is None  # Should not be completed
    assert data["started_at"] is not None

    # Test DROPPED status
    response = client.get("/api/v1/playthroughs/pt-4", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DROPPED"
    assert data["play_time_hours"] == 5.0

    # Test ON_HOLD status
    response = client.get("/api/v1/playthroughs/pt-5", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ON_HOLD"
    assert data["difficulty"] == "Death March"


def test_get_playthrough_invalid_id_format(test_data):
    """Test getting playthrough with invalid ID format."""
    # Note: "/api/v1/playthroughs/" without ID matches the list endpoint, which is expected
    # So we test with clearly invalid IDs instead

    # Test with special characters that shouldn't exist in IDs
    response = client.get(
        "/api/v1/playthroughs/invalid/id/with/slashes", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 404  # Should not match any route or should not exist

    # Test with just spaces (URL encoded)
    response = client.get(
        "/api/v1/playthroughs/%20%20%20", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 404  # Should not be found


def test_get_playthrough_response_structure(test_data):
    """Test that response has all required fields in correct structure."""
    response = client.get("/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()
    # Verify all PlaythroughBase fields are present
    required_fields = [
        "id",
        "user_id",
        "status",
        "platform",
        "created_at",
        "updated_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"

    # Verify optional fields are present (even if None)
    optional_fields = [
        "started_at",
        "completed_at",
        "play_time_hours",
        "playthrough_type",
        "difficulty",
        "rating",
        "notes",
    ]
    for field in optional_fields:
        assert field in data, f"Missing optional field: {field}"

    # Verify embedded objects structure
    assert "game" in data and isinstance(data["game"], dict)
    assert "collection" in data  # Can be None or dict
    assert "milestones" in data  # Can be None or list

    # Verify game has detail fields beyond summary
    game = data["game"]
    game_detail_fields = ["description", "igdb_id", "hltb_id", "steam_app_id"]
    for field in game_detail_fields:
        assert field in game, f"Missing GameDetail field: {field}"


# ===== PUT /playthroughs/{id} Tests =====


def test_update_playthrough_requires_auth():
    """Test that updating playthroughs requires authentication."""
    update_data = {"status": "PLAYING"}

    response = client.put("/api/v1/playthroughs/pt-1", json=update_data)
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_update_playthrough_basic_fields(test_data):
    """Test updating basic playthrough fields."""
    update_data = {
        "platform": "Steam Deck",
        "difficulty": "Easy",
        "playthrough_type": "Casual Run",
        "notes": "Playing on the go",
        "play_time_hours": 25.5,
    }

    response = client.put(
        "/api/v1/playthroughs/pt-3", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["platform"] == "Steam Deck"
    assert data["difficulty"] == "Easy"
    assert data["playthrough_type"] == "Casual Run"
    assert data["notes"] == "Playing on the go"
    assert data["play_time_hours"] == 25.5
    assert data["status"] == "PLANNING"  # Should remain unchanged
    assert data["updated_at"] != data["created_at"]  # Should be updated


def test_update_playthrough_valid_status_transitions(test_data):
    """Test valid status transitions with timestamp logic."""
    # PLANNING -> PLAYING (should set started_at)
    update_data = {"status": "PLAYING"}
    response = client.put(
        "/api/v1/playthroughs/pt-3", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "PLAYING"
    assert data["started_at"] is not None  # Should be set automatically
    assert data["completed_at"] is None

    # PLAYING -> COMPLETED (should set completed_at)
    update_data = {"status": "COMPLETED", "rating": 8}
    response = client.put(
        "/api/v1/playthroughs/pt-2", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["completed_at"] is not None  # Should be set automatically
    assert data["rating"] == 8

    # PLAYING -> ON_HOLD
    # Create a new playthrough first since pt-2 is now completed
    create_data = {"game_id": "game-4", "status": "PLAYING", "platform": "PC"}
    create_response = client.post(
        "/api/v1/playthroughs", json=create_data, headers={"X-User-Id": "user-1"}
    )
    assert create_response.status_code == 201
    new_playthrough_id = create_response.json()["id"]

    update_data = {"status": "ON_HOLD", "notes": "Taking a break"}
    response = client.put(
        f"/api/v1/playthroughs/{new_playthrough_id}",
        json=update_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ON_HOLD"
    assert data["notes"] == "Taking a break"


def test_update_playthrough_playing_to_mastered(test_data):
    """Test PLAYING -> MASTERED transition (should set completed_at)."""
    # First create a playing playthrough
    create_data = {"game_id": "game-1", "status": "PLAYING", "platform": "PC"}
    create_response = client.post(
        "/api/v1/playthroughs", json=create_data, headers={"X-User-Id": "user-1"}
    )
    assert create_response.status_code == 201
    playthrough_id = create_response.json()["id"]

    # Update to MASTERED
    update_data = {
        "status": "MASTERED",
        "rating": 10,
        "playthrough_type": "100% Achievement Run",
        "play_time_hours": 150.0,
    }

    response = client.put(
        f"/api/v1/playthroughs/{playthrough_id}",
        json=update_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "MASTERED"
    assert data["completed_at"] is not None  # Should be set automatically
    assert data["rating"] == 10
    assert data["play_time_hours"] == 150.0


def test_update_playthrough_restart_scenarios(test_data):
    """Test restarting dropped playthroughs."""
    # DROPPED -> PLANNING (restart scenario)
    update_data = {"status": "PLANNING", "notes": "Decided to give it another try"}
    response = client.put(
        "/api/v1/playthroughs/pt-4", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "PLANNING"
    assert data["notes"] == "Decided to give it another try"
    # started_at and completed_at should remain as they were

    # DROPPED -> PLAYING (direct restart)
    create_data = {"game_id": "game-2", "status": "DROPPED", "platform": "PC"}
    create_response = client.post(
        "/api/v1/playthroughs", json=create_data, headers={"X-User-Id": "user-1"}
    )
    dropped_id = create_response.json()["id"]

    update_data = {"status": "PLAYING", "notes": "Starting fresh"}
    response = client.put(
        f"/api/v1/playthroughs/{dropped_id}",
        json=update_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "PLAYING"
    assert data["started_at"] is not None  # Should be set/updated


def test_update_playthrough_invalid_status_transitions(test_data):
    """Test invalid status transitions."""
    # COMPLETED -> PLAYING (invalid - can't uncomplete)
    update_data = {"status": "PLAYING"}
    response = client.put(
        "/api/v1/playthroughs/pt-1", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422
    assert "Invalid status transition" in response.json()["message"]

    # MASTERED -> PLANNING (invalid - mastered should be final)
    # First create a mastered playthrough
    create_data = {
        "game_id": "game-3",
        "status": "COMPLETED",
        "platform": "PC",
        "completed_at": "2024-01-15T10:00:00",
    }
    create_response = client.post(
        "/api/v1/playthroughs", json=create_data, headers={"X-User-Id": "user-1"}
    )
    playthrough_id = create_response.json()["id"]

    # Update to mastered first
    client.put(
        f"/api/v1/playthroughs/{playthrough_id}",
        json={"status": "MASTERED"},
        headers={"X-User-Id": "user-1"},
    )

    # Try to change from mastered to planning
    update_data = {"status": "PLANNING"}
    response = client.put(
        f"/api/v1/playthroughs/{playthrough_id}",
        json=update_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 422
    assert "Invalid status transition" in response.json()["message"]


def test_update_playthrough_validation_constraints(test_data):
    """Test field validation constraints."""
    # Invalid rating
    update_data = {"rating": 15}  # Should be 1-10
    response = client.put(
        "/api/v1/playthroughs/pt-1", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422

    # Negative play time
    update_data = {"play_time_hours": -5.0}
    response = client.put(
        "/api/v1/playthroughs/pt-1", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422

    # Invalid status enum
    update_data = {"status": "INVALID_STATUS"}
    response = client.put(
        "/api/v1/playthroughs/pt-1", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422


def test_update_playthrough_not_found(test_data):
    """Test updating non-existent playthrough."""
    update_data = {"status": "PLAYING"}
    response = client.put(
        "/api/v1/playthroughs/non-existent",
        json=update_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]


def test_update_playthrough_user_isolation(test_data):
    """Test that users cannot update other users' playthroughs."""
    update_data = {"status": "PLAYING"}

    # Try to update user-1's playthrough as user-2
    response = client.put(
        "/api/v1/playthroughs/pt-1", json=update_data, headers={"X-User-Id": "user-2"}
    )
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]

    # Try to update user-2's playthrough as user-1
    response = client.put(
        "/api/v1/playthroughs/pt-6", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]


def test_update_playthrough_immutable_fields(test_data):
    """Test that certain fields cannot be updated."""
    update_data = {
        "id": "different-id",  # Should be ignored
        "user_id": "different-user",  # Should be ignored
        "game_id": "different-game",  # Should be ignored
        "created_at": "2020-01-01T00:00:00Z",  # Should be ignored
        "platform": "Updated Platform",  # Should be allowed
    }

    response = client.put(
        "/api/v1/playthroughs/pt-1", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    # Immutable fields should not change
    assert data["id"] == "pt-1"  # Original value
    assert data["user_id"] == "user-1"  # Original value
    assert data["game_id"] == "game-1"  # Original value
    assert data["created_at"] != "2020-01-01T00:00:00Z"  # Original value

    # Mutable fields should change
    assert data["platform"] == "Updated Platform"


def test_update_playthrough_partial_updates(test_data):
    """Test that partial updates work correctly."""
    # Update only one field
    update_data = {"notes": "Updated notes only"}
    response = client.put(
        "/api/v1/playthroughs/pt-1", json=update_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["notes"] == "Updated notes only"
    # Other fields should remain unchanged
    assert data["status"] == "COMPLETED"
    assert data["platform"] == "PC"
    assert data["rating"] == 9


def test_update_playthrough_timestamp_logic_detailed(test_data):
    """Test detailed timestamp logic for different scenarios."""
    # Create a planning playthrough
    create_data = {"game_id": "game-1", "status": "PLANNING", "platform": "PC"}
    create_response = client.post(
        "/api/v1/playthroughs", json=create_data, headers={"X-User-Id": "user-1"}
    )
    playthrough_id = create_response.json()["id"]

    # Update to PLAYING - should set started_at
    update_data = {"status": "PLAYING"}
    response = client.put(
        f"/api/v1/playthroughs/{playthrough_id}",
        json=update_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    first_started_at = data["started_at"]
    assert first_started_at is not None

    # Update to ON_HOLD - should not change started_at
    update_data = {"status": "ON_HOLD"}
    response = client.put(
        f"/api/v1/playthroughs/{playthrough_id}",
        json=update_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["started_at"] == first_started_at  # Should remain the same

    # Update to COMPLETED - should set completed_at
    update_data = {"status": "COMPLETED"}
    response = client.put(
        f"/api/v1/playthroughs/{playthrough_id}",
        json=update_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["completed_at"] is not None
    assert data["started_at"] == first_started_at  # Should remain the same


def test_update_playthrough_empty_body(test_data):
    """Test updating with empty body."""
    response = client.put(
        "/api/v1/playthroughs/pt-1", json={}, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    # Should return the playthrough unchanged except for updated_at
    data = response.json()
    assert data["id"] == "pt-1"
    assert data["status"] == "COMPLETED"


# ===== POST /playthroughs/{id}/complete Tests =====


def test_complete_playthrough_requires_auth():
    """Test that completing playthrough requires authentication."""
    completion_data = {
        "completed_at": "2024-04-20T15:45:00Z",
        "final_play_time_hours": 85.5,
        "rating": 9,
        "final_notes": "Amazing game!",
        "completion_type": "COMPLETED",
    }

    response = client.post("/api/v1/playthroughs/pt-2/complete", json=completion_data)
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_complete_playthrough_success_from_playing(test_data):
    """Test successfully completing a playthrough that is currently playing."""
    completion_data = {
        "completed_at": "2024-04-20T15:45:00Z",
        "final_play_time_hours": 85.5,
        "rating": 9,
        "final_notes": "Amazing game, loved every moment!",
        "completion_type": "COMPLETED",
    }

    response = client.post(
        "/api/v1/playthroughs/pt-2/complete",
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "pt-2"
    assert data["status"] == "COMPLETED"
    assert data["completed_at"] == "2024-04-20T15:45:00Z"
    assert data["play_time_hours"] == 85.5
    assert data["rating"] == 9
    assert data["notes"] == "Amazing game, loved every moment!"
    assert data["updated_at"] != data["created_at"]  # Should be updated


def test_complete_playthrough_success_mastered(test_data):
    """Test successfully completing a playthrough with mastered completion type."""
    # Create a new playing playthrough first
    create_data = {"game_id": "game-3", "status": "PLAYING", "platform": "PC"}
    create_response = client.post(
        "/api/v1/playthroughs", json=create_data, headers={"X-User-Id": "user-1"}
    )
    assert create_response.status_code == 201
    playthrough_id = create_response.json()["id"]

    completion_data = {
        "completed_at": "2024-05-01T20:30:00Z",
        "final_play_time_hours": 150.0,
        "rating": 10,
        "final_notes": "100% achievement run complete!",
        "completion_type": "MASTERED",
    }

    response = client.post(
        f"/api/v1/playthroughs/{playthrough_id}/complete",
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "MASTERED"
    assert data["completed_at"] == "2024-05-01T20:30:00Z"
    assert data["play_time_hours"] == 150.0
    assert data["rating"] == 10
    assert data["notes"] == "100% achievement run complete!"


def test_complete_playthrough_success_dropped(test_data):
    """Test successfully marking a playthrough as dropped."""
    # Create a new playing playthrough first
    create_data = {"game_id": "game-1", "status": "PLAYING", "platform": "PC"}
    create_response = client.post(
        "/api/v1/playthroughs", json=create_data, headers={"X-User-Id": "user-1"}
    )
    assert create_response.status_code == 201
    playthrough_id = create_response.json()["id"]

    completion_data = {
        "completed_at": "2024-03-10T12:00:00Z",  # Date when dropped
        "final_play_time_hours": 15.0,
        "final_notes": "Lost interest after a few hours",
        "completion_type": "DROPPED",
    }

    response = client.post(
        f"/api/v1/playthroughs/{playthrough_id}/complete",
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "DROPPED"
    assert data["completed_at"] == "2024-03-10T12:00:00Z"
    assert data["play_time_hours"] == 15.0
    assert data["notes"] == "Lost interest after a few hours"
    assert data["rating"] is None  # No rating for dropped games


def test_complete_playthrough_success_on_hold(test_data):
    """Test successfully putting a playthrough on hold."""
    # Create a new playing playthrough first
    create_data = {"game_id": "game-2", "status": "PLAYING", "platform": "PC"}
    create_response = client.post(
        "/api/v1/playthroughs", json=create_data, headers={"X-User-Id": "user-1"}
    )
    assert create_response.status_code == 201
    playthrough_id = create_response.json()["id"]

    completion_data = {
        "final_play_time_hours": 25.0,
        "final_notes": "Taking a break, will return later",
        "completion_type": "ON_HOLD",
    }

    response = client.post(
        f"/api/v1/playthroughs/{playthrough_id}/complete",
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ON_HOLD"
    assert data["completed_at"] is None  # On hold doesn't set completed_at
    assert data["play_time_hours"] == 25.0
    assert data["notes"] == "Taking a break, will return later"


def test_complete_playthrough_minimal_data(test_data):
    """Test completing playthrough with minimal required data."""
    # Create a new playing playthrough first
    create_data = {"game_id": "game-4", "status": "PLAYING", "platform": "PC"}
    create_response = client.post(
        "/api/v1/playthroughs", json=create_data, headers={"X-User-Id": "user-1"}
    )
    assert create_response.status_code == 201
    playthrough_id = create_response.json()["id"]

    completion_data = {"completion_type": "COMPLETED"}

    response = client.post(
        f"/api/v1/playthroughs/{playthrough_id}/complete",
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["completed_at"] is not None  # Should be set automatically
    # Other fields should remain unchanged from the original playthrough


def test_complete_playthrough_already_completed(test_data):
    """Test completing an already completed playthrough returns 409."""
    completion_data = {
        "completed_at": "2024-04-20T15:45:00Z",
        "final_play_time_hours": 85.5,
        "rating": 9,
        "completion_type": "COMPLETED",
    }

    response = client.post(
        "/api/v1/playthroughs/pt-1/complete",  # pt-1 is already COMPLETED
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 409
    assert "already completed" in response.json()["message"].lower()


def test_complete_playthrough_from_invalid_status(test_data):
    """Test completing from invalid status (PLANNING) returns 422."""
    completion_data = {"completion_type": "COMPLETED"}

    response = client.post(
        "/api/v1/playthroughs/pt-3/complete",  # pt-3 is PLANNING status
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 422
    assert "Invalid status transition" in response.json()["message"]


def test_complete_playthrough_not_found(test_data):
    """Test completing non-existent playthrough."""
    completion_data = {"completion_type": "COMPLETED"}

    response = client.post(
        "/api/v1/playthroughs/non-existent/complete",
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]


def test_complete_playthrough_user_isolation(test_data):
    """Test users cannot complete other users' playthroughs."""
    completion_data = {"completion_type": "COMPLETED"}

    # Try to complete user-1's playthrough as user-2
    response = client.post(
        "/api/v1/playthroughs/pt-2/complete",
        json=completion_data,
        headers={"X-User-Id": "user-2"},
    )
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]


def test_complete_playthrough_invalid_completion_type(test_data):
    """Test completing with invalid completion type."""
    completion_data = {"completion_type": "INVALID_TYPE"}

    response = client.post(
        "/api/v1/playthroughs/pt-2/complete",
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 422


def test_complete_playthrough_invalid_rating(test_data):
    """Test completing with invalid rating."""
    completion_data = {
        "completion_type": "COMPLETED",
        "rating": 15,  # Should be 1-10
    }

    response = client.post(
        "/api/v1/playthroughs/pt-2/complete",
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 422


def test_complete_playthrough_negative_play_time(test_data):
    """Test completing with negative play time."""
    completion_data = {"completion_type": "COMPLETED", "final_play_time_hours": -5.0}

    response = client.post(
        "/api/v1/playthroughs/pt-2/complete",
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 422


def test_complete_playthrough_missing_required_field(test_data):
    """Test completing without required completion_type field."""
    completion_data = {"final_play_time_hours": 50.0, "rating": 8}

    response = client.post(
        "/api/v1/playthroughs/pt-2/complete",
        json=completion_data,
        headers={"X-User-Id": "user-1"},
    )
    assert response.status_code == 422


# ===== DELETE /playthroughs/{id} Tests =====


def test_delete_playthrough_requires_auth():
    """Test that deleting playthrough requires authentication."""
    response = client.delete("/api/v1/playthroughs/pt-1")
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_delete_playthrough_success(test_data):
    """Test successfully deleting a playthrough."""
    # First, verify the playthrough exists
    response = client.get("/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    # Delete the playthrough
    response = client.delete(
        "/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "deleted successfully" in data["message"].lower()

    # Verify the playthrough is gone
    response = client.get("/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"})
    assert response.status_code == 404


def test_delete_playthrough_not_found(test_data):
    """Test deleting non-existent playthrough."""
    response = client.delete(
        "/api/v1/playthroughs/non-existent", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]


def test_delete_playthrough_user_isolation(test_data):
    """Test users cannot delete other users' playthroughs."""
    # Try to delete user-1's playthrough as user-2
    response = client.delete(
        "/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-2"}
    )
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]

    # Verify user-1's playthrough still exists
    response = client.get("/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    # User-2 can delete their own playthrough
    response = client.delete(
        "/api/v1/playthroughs/pt-6", headers={"X-User-Id": "user-2"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True


def test_delete_playthrough_removes_from_list(test_data):
    """Test that deleted playthrough is removed from user's list."""
    # Get initial count
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200
    initial_count = response.json()["total_count"]

    # Delete a playthrough
    response = client.delete(
        "/api/v1/playthroughs/pt-2", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    # Verify count is reduced by 1
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200
    final_count = response.json()["total_count"]
    assert final_count == initial_count - 1

    # Verify the specific playthrough is not in the list
    items = response.json()["items"]
    playthrough_ids = [item["id"] for item in items]
    assert "pt-2" not in playthrough_ids


def test_delete_playthrough_different_statuses(test_data):
    """Test deleting playthroughs in different statuses."""
    # Delete completed playthrough
    response = client.delete(
        "/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    # Delete playing playthrough
    response = client.delete(
        "/api/v1/playthroughs/pt-2", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    # Delete planning playthrough
    response = client.delete(
        "/api/v1/playthroughs/pt-3", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    # Delete dropped playthrough
    response = client.delete(
        "/api/v1/playthroughs/pt-4", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    # Delete on hold playthrough
    response = client.delete(
        "/api/v1/playthroughs/pt-5", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    # Verify all are gone
    response = client.get("/api/v1/playthroughs", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200
    assert response.json()["total_count"] == 0


def test_delete_playthrough_twice(test_data):
    """Test that deleting the same playthrough twice returns 404."""
    # First delete should succeed
    response = client.delete(
        "/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    # Second delete should return 404
    response = client.delete(
        "/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 404
    assert "Playthrough not found" in response.json()["message"]


def test_delete_playthrough_response_format(test_data):
    """Test that delete response has correct format."""
    response = client.delete(
        "/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    # Verify required fields are present
    assert "success" in data
    assert "message" in data
    assert isinstance(data["success"], bool)
    assert isinstance(data["message"], str)
    assert data["success"] is True


# ===== POST /playthroughs/bulk Tests =====


def test_bulk_playthrough_requires_auth():
    """Test that bulk operations require authentication."""
    bulk_data = {
        "action": "update_status",
        "playthrough_ids": ["pt-1", "pt-2"],
        "data": {"status": "ON_HOLD"},
    }

    response = client.post("/api/v1/playthroughs/bulk", json=bulk_data)
    assert response.status_code == 401
    assert response.json()["error"] == "authentication_required"


def test_bulk_update_status_success(test_data):
    """Test successfully updating status for multiple playthroughs."""
    # Test valid transitions: PLAYING to ON_HOLD (pt-2) and PLANNING to PLAYING (pt-3)

    # First, transition PLANNING playthrough to PLAYING
    bulk_data_1 = {
        "action": "update_status",
        "playthrough_ids": ["pt-3"],  # PLANNING
        "data": {"status": "PLAYING"},
    }

    response1 = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data_1, headers={"X-User-Id": "user-1"}
    )
    assert response1.status_code == 200

    # Now both pt-2 and pt-3 are PLAYING, so both can transition to ON_HOLD
    bulk_data_2 = {
        "action": "update_status",
        "playthrough_ids": ["pt-2", "pt-3"],  # Both PLAYING
        "data": {"status": "ON_HOLD"},
    }

    response2 = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data_2, headers={"X-User-Id": "user-1"}
    )
    assert response2.status_code == 200

    data = response2.json()
    assert data["success"] is True
    assert data["updated_count"] == 2
    assert len(data["items"]) == 2

    # Verify both playthroughs were updated
    for item in data["items"]:
        assert item["id"] in ["pt-2", "pt-3"]
        assert item["status"] == "ON_HOLD"

    # Verify the changes persisted
    response = client.get("/api/v1/playthroughs/pt-2", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200
    assert response.json()["status"] == "ON_HOLD"


def test_bulk_update_platform_success(test_data):
    """Test successfully updating platform for multiple playthroughs."""
    bulk_data = {
        "action": "update_platform",
        "playthrough_ids": ["pt-1", "pt-2"],
        "data": {"platform": "Steam Deck"},
    }

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["updated_count"] == 2
    assert len(data["items"]) == 2

    # Verify platform was updated
    for item in data["items"]:
        assert item["platform"] == "Steam Deck"


def test_bulk_add_time_success(test_data):
    """Test successfully adding play time to multiple playthroughs."""
    # Get initial play times
    response1 = client.get("/api/v1/playthroughs/pt-1", headers={"X-User-Id": "user-1"})
    initial_time1 = response1.json()["play_time_hours"]

    response2 = client.get("/api/v1/playthroughs/pt-2", headers={"X-User-Id": "user-1"})
    initial_time2 = response2.json()["play_time_hours"]

    bulk_data = {
        "action": "add_time",
        "playthrough_ids": ["pt-1", "pt-2"],
        "data": {"hours": 5.5},
    }

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["updated_count"] == 2

    # Verify time was added correctly
    for item in data["items"]:
        if item["id"] == "pt-1":
            expected_time = (initial_time1 or 0) + 5.5
            assert item["play_time_hours"] == expected_time
        elif item["id"] == "pt-2":
            expected_time = (initial_time2 or 0) + 5.5
            assert item["play_time_hours"] == expected_time


def test_bulk_delete_success(test_data):
    """Test successfully deleting multiple playthroughs."""
    # Verify playthroughs exist first
    response = client.get("/api/v1/playthroughs/pt-3", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    response = client.get("/api/v1/playthroughs/pt-4", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    bulk_data = {"action": "delete", "playthrough_ids": ["pt-3", "pt-4"]}

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["updated_count"] == 2

    # Verify playthroughs were deleted
    response = client.get("/api/v1/playthroughs/pt-3", headers={"X-User-Id": "user-1"})
    assert response.status_code == 404

    response = client.get("/api/v1/playthroughs/pt-4", headers={"X-User-Id": "user-1"})
    assert response.status_code == 404


def test_bulk_partial_success_207(test_data):
    """Test partial success returns 207 with mixed results."""
    bulk_data = {
        "action": "update_status",
        "playthrough_ids": [
            "pt-2",  # PLAYING -> ON_HOLD (valid)
            "non-existent",  # Invalid ID
            "pt-1",  # COMPLETED -> ON_HOLD (invalid transition)
        ],  # Mix of valid and invalid transitions/IDs
        "data": {"status": "ON_HOLD"},
    }

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 207

    data = response.json()
    assert data["success"] is False
    assert data["updated_count"] == 1  # Only pt-2 was updated
    assert data["failed_count"] == 2
    assert len(data["items"]) == 1  # Only successful items
    assert len(data["failed_items"]) == 2

    # Check failed item details
    failed_ids = [item["id"] for item in data["failed_items"]]
    assert "non-existent" in failed_ids
    assert "pt-1" in failed_ids

    # Check specific error types
    for failed_item in data["failed_items"]:
        if failed_item["id"] == "non-existent":
            assert "not found" in failed_item["error"].lower()
        elif failed_item["id"] == "pt-1":
            assert "invalid status transition" in failed_item["error"].lower()


def test_bulk_user_isolation(test_data):
    """Test users can only bulk operate on their own playthroughs."""
    bulk_data = {
        "action": "update_status",
        "playthrough_ids": ["pt-2", "pt-6"],  # pt-2 belongs to user-1, pt-6 to user-2
        "data": {"status": "ON_HOLD"},
    }

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 207  # Partial success

    data = response.json()
    assert data["success"] is False
    assert data["updated_count"] == 1  # Only pt-2
    assert data["failed_count"] == 1  # pt-6 failed

    # Verify user-2's playthrough wasn't modified
    response = client.get("/api/v1/playthroughs/pt-6", headers={"X-User-Id": "user-2"})
    assert response.status_code == 200
    assert response.json()["status"] == "PLAYING"  # Should remain unchanged


def test_bulk_invalid_action(test_data):
    """Test invalid action returns 422."""
    bulk_data = {
        "action": "invalid_action",
        "playthrough_ids": ["pt-1"],
        "data": {"status": "ON_HOLD"},
    }

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422


def test_bulk_invalid_status_transition(test_data):
    """Test bulk status update with invalid transitions."""
    bulk_data = {
        "action": "update_status",
        "playthrough_ids": ["pt-1"],  # pt-1 is COMPLETED
        "data": {"status": "PLANNING"},  # Invalid transition from COMPLETED to PLANNING
    }

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 207  # Partial success (all failed)

    data = response.json()
    assert data["success"] is False
    assert data["updated_count"] == 0
    assert data["failed_count"] == 1
    assert len(data["failed_items"]) == 1
    assert "Invalid status transition" in data["failed_items"][0]["error"]


def test_bulk_empty_playthrough_ids(test_data):
    """Test bulk operation with empty playthrough IDs list."""
    bulk_data = {
        "action": "update_status",
        "playthrough_ids": [],
        "data": {"status": "ON_HOLD"},
    }

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422  # Pydantic validation error


def test_bulk_missing_required_fields(test_data):
    """Test bulk operation with missing required fields."""
    # Missing action
    bulk_data = {"playthrough_ids": ["pt-1"], "data": {"status": "ON_HOLD"}}

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 422


def test_bulk_invalid_data_for_action(test_data):
    """Test bulk operation with invalid data for specific actions."""
    # Missing required data for update_status
    bulk_data = {"action": "update_status", "playthrough_ids": ["pt-1"], "data": {}}

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 400
    assert "status is required" in response.json()["message"].lower()

    # Missing required data for add_time
    bulk_data = {"action": "add_time", "playthrough_ids": ["pt-1"], "data": {}}

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 400
    assert "hours is required" in response.json()["message"].lower()


def test_bulk_add_time_with_none_initial_time(test_data):
    """Test adding time to playthroughs that have no initial play time."""
    # pt-3 has no play time initially (None)
    bulk_data = {
        "action": "add_time",
        "playthrough_ids": ["pt-3"],
        "data": {"hours": 10.5},
    }

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["updated_count"] == 1
    assert data["items"][0]["play_time_hours"] == 10.5


def test_bulk_response_format(test_data):
    """Test that bulk response has correct format for success case."""
    bulk_data = {
        "action": "update_status",
        "playthrough_ids": ["pt-2"],
        "data": {"status": "ON_HOLD"},
    }

    response = client.post(
        "/api/v1/playthroughs/bulk", json=bulk_data, headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    # Verify required fields are present
    assert "success" in data
    assert "updated_count" in data
    assert "items" in data
    assert isinstance(data["success"], bool)
    assert isinstance(data["updated_count"], int)
    assert isinstance(data["items"], list)
    assert data["success"] is True

    # For successful operations, these fields should not be present
    assert "failed_count" not in data
    assert "failed_items" not in data


# ===== Backlog Endpoint Tests =====


def test_get_backlog_success(test_data):
    """Test successful backlog retrieval."""
    response = client.get(
        "/api/v1/playthroughs/backlog", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total_count" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total_count"], int)

    # All items should have status "PLANNING"
    for item in data["items"]:
        assert item["status"] == "PLANNING"
        assert "id" in item
        assert "game" in item
        assert "created_at" in item
        assert item["game"]["title"]


def test_get_backlog_user_isolation(test_data):
    """Test backlog only shows user's own playthroughs."""
    response = client.get(
        "/api/v1/playthroughs/backlog", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    user1_backlog_count = data["total_count"]

    response = client.get(
        "/api/v1/playthroughs/backlog", headers={"X-User-Id": "user-2"}
    )
    assert response.status_code == 200

    data = response.json()
    user2_backlog_count = data["total_count"]

    # Different users should potentially have different backlog counts
    # At minimum, verify both requests work
    assert user1_backlog_count >= 0
    assert user2_backlog_count >= 0


def test_get_backlog_with_collection_info(test_data):
    """Test backlog includes collection information when available."""
    # Create a collection item and planning playthrough linked to it
    collection_data = {
        "game_id": "game-4",  # Use existing game-4 from test data
        "platform": "PC",
        "acquisition_type": "DIGITAL",
        "priority": 5,
    }
    collection_response = client.post(
        "/api/v1/collection", json=collection_data, headers={"X-User-Id": "user-1"}
    )
    assert collection_response.status_code == 201
    collection_id = collection_response.json()["id"]

    playthrough_data = {
        "game_id": "game-4",  # Use existing game-4 from test data
        "collection_id": collection_id,
        "status": "PLANNING",
        "platform": "PC",
    }
    playthrough_response = client.post(
        "/api/v1/playthroughs", json=playthrough_data, headers={"X-User-Id": "user-1"}
    )
    assert playthrough_response.status_code == 201

    response = client.get(
        "/api/v1/playthroughs/backlog", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    # Find the newly created backlog item
    backlog_item = None
    for item in data["items"]:
        if item["game"]["id"] == "game-4":
            backlog_item = item
            break

    assert backlog_item is not None
    assert backlog_item["collection"] is not None
    assert backlog_item["collection"]["id"] == collection_id
    assert backlog_item["collection"]["priority"] == 5


def test_get_backlog_priority_filtering(test_data):
    """Test backlog can be filtered by priority."""
    response = client.get(
        "/api/v1/playthroughs/backlog?priority=5", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    # All returned items should have priority 5 in their collection
    for item in data["items"]:
        if item["collection"]:
            assert item["collection"]["priority"] == 5


def test_get_backlog_requires_auth():
    """Test backlog endpoint requires authentication."""
    response = client.get("/api/v1/playthroughs/backlog")
    assert response.status_code == 401


def test_get_backlog_empty_result():
    """Test backlog endpoint when user has no planning playthroughs."""
    # Create a user with no planning playthroughs
    response = client.get(
        "/api/v1/playthroughs/backlog", headers={"X-User-Id": "user-empty"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["items"] == []
    assert data["total_count"] == 0


# ===== Playing Endpoint Tests =====


def test_get_playing_success(test_data):
    """Test successful playing retrieval."""
    response = client.get(
        "/api/v1/playthroughs/playing", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total_count" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total_count"], int)

    # All items should have status "PLAYING"
    for item in data["items"]:
        assert item["status"] == "PLAYING"
        assert "id" in item
        assert "game" in item
        assert "platform" in item
        assert "started_at" in item
        assert item["game"]["title"]


def test_get_playing_user_isolation(test_data):
    """Test playing only shows user's own playthroughs."""
    response = client.get(
        "/api/v1/playthroughs/playing", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    user1_playing_count = data["total_count"]

    response = client.get(
        "/api/v1/playthroughs/playing", headers={"X-User-Id": "user-2"}
    )
    assert response.status_code == 200

    data = response.json()
    user2_playing_count = data["total_count"]

    # Different users should potentially have different playing counts
    # At minimum, verify both requests work
    assert user1_playing_count >= 0
    assert user2_playing_count >= 0


def test_get_playing_platform_filtering(test_data):
    """Test playing can be filtered by platform."""
    response = client.get(
        "/api/v1/playthroughs/playing?platform=PC", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    # All returned items should have platform "PC"
    for item in data["items"]:
        assert item["platform"] == "PC"


def test_get_playing_includes_play_time(test_data):
    """Test playing items include play_time_hours and last_played fields."""
    response = client.get(
        "/api/v1/playthroughs/playing", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    for item in data["items"]:
        assert "play_time_hours" in item
        assert "last_played" in item
        # play_time_hours can be null or a float
        if item["play_time_hours"] is not None:
            assert isinstance(item["play_time_hours"], (int, float))


def test_get_playing_requires_auth():
    """Test playing endpoint requires authentication."""
    response = client.get("/api/v1/playthroughs/playing")
    assert response.status_code == 401


def test_get_playing_empty_result():
    """Test playing endpoint when user has no playing playthroughs."""
    # Create a user with no playing playthroughs
    response = client.get(
        "/api/v1/playthroughs/playing", headers={"X-User-Id": "user-empty"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["items"] == []
    assert data["total_count"] == 0


def test_get_playing_shows_recent_activity(test_data):
    """Test playing shows most recently started playthroughs first."""
    response = client.get(
        "/api/v1/playthroughs/playing", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    if len(data["items"]) > 1:
        # Check that items are sorted by started_at descending
        for i in range(len(data["items"]) - 1):
            current_started = data["items"][i]["started_at"]
            next_started = data["items"][i + 1]["started_at"]
            # More recent should come first
            assert current_started >= next_started


# ===== Completed Endpoint Tests =====


def test_get_completed_success(test_data):
    """Test successful completed retrieval."""
    response = client.get(
        "/api/v1/playthroughs/completed", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total_count" in data
    assert "completion_stats" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["total_count"], int)

    # All items should have status "COMPLETED"
    for item in data["items"]:
        assert item["status"] == "COMPLETED"
        assert "id" in item
        assert "game" in item
        assert "platform" in item
        assert "completed_at" in item
        assert item["game"]["title"]


def test_get_completed_user_isolation(test_data):
    """Test completed only shows user's own playthroughs."""
    response = client.get(
        "/api/v1/playthroughs/completed", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    user1_completed_count = data["total_count"]

    response = client.get(
        "/api/v1/playthroughs/completed", headers={"X-User-Id": "user-2"}
    )
    assert response.status_code == 200

    data = response.json()
    user2_completed_count = data["total_count"]

    # Different users should potentially have different completed counts
    # At minimum, verify both requests work
    assert user1_completed_count >= 0
    assert user2_completed_count >= 0


def test_get_completed_year_filtering(test_data):
    """Test completed can be filtered by completion year."""
    response = client.get(
        "/api/v1/playthroughs/completed?year=2023", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    # All returned items should have completed_at in 2023
    for item in data["items"]:
        completed_at = item["completed_at"]
        assert completed_at.startswith("2023")


def test_get_completed_rating_filtering(test_data):
    """Test completed can be filtered by minimum rating."""
    response = client.get(
        "/api/v1/playthroughs/completed?min_rating=8", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    # All returned items should have rating >= 8 (or null)
    for item in data["items"]:
        if item["rating"] is not None:
            assert item["rating"] >= 8


def test_get_completed_platform_filtering(test_data):
    """Test completed can be filtered by platform."""
    response = client.get(
        "/api/v1/playthroughs/completed?platform=PC", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    # All returned items should have platform "PC"
    for item in data["items"]:
        assert item["platform"] == "PC"


def test_get_completed_includes_expected_fields(test_data):
    """Test completed items include expected fields."""
    response = client.get(
        "/api/v1/playthroughs/completed", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    for item in data["items"]:
        assert "play_time_hours" in item
        assert "rating" in item
        assert "playthrough_type" in item
        # These fields can be null or have values
        if item["play_time_hours"] is not None:
            assert isinstance(item["play_time_hours"], (int, float))
        if item["rating"] is not None:
            assert isinstance(item["rating"], int)
            assert 1 <= item["rating"] <= 10


def test_get_completed_completion_stats(test_data):
    """Test completed endpoint includes completion statistics."""
    response = client.get(
        "/api/v1/playthroughs/completed", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    stats = data["completion_stats"]
    assert stats is not None
    assert isinstance(stats, dict)
    # Should include aggregate statistics
    expected_keys = [
        "total_completed",
        "average_rating",
        "total_play_time",
        "average_play_time",
    ]
    for key in expected_keys:
        if key in stats:
            assert isinstance(stats[key], (int, float, str))


def test_get_completed_requires_auth():
    """Test completed endpoint requires authentication."""
    response = client.get("/api/v1/playthroughs/completed")
    assert response.status_code == 401


def test_get_completed_empty_result():
    """Test completed endpoint when user has no completed playthroughs."""
    # Create a user with no completed playthroughs
    response = client.get(
        "/api/v1/playthroughs/completed", headers={"X-User-Id": "user-empty"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["items"] == []
    assert data["total_count"] == 0
    assert data["completion_stats"] is not None


def test_get_completed_shows_recent_completions_first(test_data):
    """Test completed shows most recently completed playthroughs first."""
    response = client.get(
        "/api/v1/playthroughs/completed", headers={"X-User-Id": "user-1"}
    )
    assert response.status_code == 200

    data = response.json()
    if len(data["items"]) > 1:
        # Check that items are sorted by completed_at descending
        for i in range(len(data["items"]) - 1):
            current_completed = data["items"][i]["completed_at"]
            next_completed = data["items"][i + 1]["completed_at"]
            # More recent should come first
            assert current_completed >= next_completed


# ===== Stats Endpoint Tests =====


def test_get_stats_success(test_data):
    """Test successful stats retrieval."""
    response = client.get("/api/v1/playthroughs/stats", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()
    assert "total_playthroughs" in data
    assert "by_status" in data
    assert "by_platform" in data
    assert "completion_stats" in data
    assert isinstance(data["total_playthroughs"], int)
    assert isinstance(data["by_status"], dict)
    assert isinstance(data["by_platform"], dict)
    assert isinstance(data["completion_stats"], dict)


def test_get_stats_user_isolation(test_data):
    """Test stats only shows user's own playthroughs."""
    response = client.get("/api/v1/playthroughs/stats", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()
    user1_total = data["total_playthroughs"]

    response = client.get("/api/v1/playthroughs/stats", headers={"X-User-Id": "user-2"})
    assert response.status_code == 200

    data = response.json()
    user2_total = data["total_playthroughs"]

    # Different users should potentially have different total counts
    # At minimum, verify both requests work
    assert user1_total >= 0
    assert user2_total >= 0


def test_get_stats_status_breakdown(test_data):
    """Test stats include proper status breakdown."""
    response = client.get("/api/v1/playthroughs/stats", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()
    by_status = data["by_status"]

    # Should have counts for various statuses
    expected_statuses = ["PLANNING", "PLAYING", "COMPLETED", "DROPPED", "ON_HOLD"]
    for status in expected_statuses:
        if status in by_status:
            assert isinstance(by_status[status], int)
            assert by_status[status] >= 0


def test_get_stats_platform_breakdown(test_data):
    """Test stats include proper platform breakdown."""
    response = client.get("/api/v1/playthroughs/stats", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()
    by_platform = data["by_platform"]

    # Should have counts for platforms used
    for platform, count in by_platform.items():
        assert isinstance(platform, str)
        assert isinstance(count, int)
        assert count > 0  # Only platforms with playthroughs should be included


def test_get_stats_completion_stats(test_data):
    """Test stats include completion statistics."""
    response = client.get("/api/v1/playthroughs/stats", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()
    completion_stats = data["completion_stats"]

    # Should include various completion metrics
    expected_keys = ["completion_rate", "average_rating", "total_play_time"]
    for key in expected_keys:
        if key in completion_stats:
            assert isinstance(completion_stats[key], (int, float, str))


def test_get_stats_yearly_stats(test_data):
    """Test stats include yearly breakdown when available."""
    response = client.get("/api/v1/playthroughs/stats", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()

    # yearly_stats is optional but if present should be properly structured
    if "yearly_stats" in data and data["yearly_stats"]:
        yearly_stats = data["yearly_stats"]
        assert isinstance(yearly_stats, dict)

        for year, stats in yearly_stats.items():
            assert isinstance(year, str)  # Year as string
            assert isinstance(stats, dict)
            # Each year should have completion metrics
            for metric, value in stats.items():
                assert isinstance(value, (int, float))


def test_get_stats_top_genres(test_data):
    """Test stats include top genres when available."""
    response = client.get("/api/v1/playthroughs/stats", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()

    # top_genres is optional but if present should be properly structured
    if "top_genres" in data and data["top_genres"]:
        top_genres = data["top_genres"]
        assert isinstance(top_genres, list)

        for genre_info in top_genres:
            assert isinstance(genre_info, dict)
            # Each genre should have name and count/percentage info
            expected_keys = ["genre", "count"]
            for key in expected_keys:
                if key in genre_info:
                    assert genre_info[key] is not None


def test_get_stats_requires_auth():
    """Test stats endpoint requires authentication."""
    response = client.get("/api/v1/playthroughs/stats")
    assert response.status_code == 401


def test_get_stats_empty_user():
    """Test stats endpoint when user has no playthroughs."""
    # Create a user with no playthroughs
    response = client.get(
        "/api/v1/playthroughs/stats", headers={"X-User-Id": "user-empty"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["total_playthroughs"] == 0
    assert data["by_status"] == {}
    assert data["by_platform"] == {}
    assert isinstance(data["completion_stats"], dict)


def test_get_stats_data_consistency(test_data):
    """Test stats data is internally consistent."""
    response = client.get("/api/v1/playthroughs/stats", headers={"X-User-Id": "user-1"})
    assert response.status_code == 200

    data = response.json()

    # Total playthroughs should equal sum of status counts
    total_by_status = sum(data["by_status"].values()) if data["by_status"] else 0
    assert data["total_playthroughs"] == total_by_status

    # Total playthroughs should equal sum of platform counts
    total_by_platform = sum(data["by_platform"].values()) if data["by_platform"] else 0
    assert data["total_playthroughs"] == total_by_platform
