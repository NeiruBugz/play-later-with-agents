from datetime import datetime, date

from app.schemas import (
    AcquisitionType,
    CollectionItem,
    GameSummary,
    PlaythroughListItem,
    PlaythroughStatus,
    CollectionSnippet,
)


def test_game_summary_serialization() -> None:
    g = GameSummary(
        id="game_1",
        title="Elden Ring",
        cover_image_id="co2lbd",
        release_date=date(2022, 2, 25),
    )
    data = g.model_dump()
    assert data["title"] == "Elden Ring"
    assert data["cover_image_id"] == "co2lbd"


def test_collection_item_priority_validation() -> None:
    c = CollectionItem(
        id="col_1",
        user_id="usr_1",
        game_id="game_1",
        platform="PS5",
        acquisition_type=AcquisitionType.DIGITAL,
        priority=3,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    assert c.priority == 3


def test_playthrough_list_item_status_enum() -> None:
    p = PlaythroughListItem(
        id="play_1",
        user_id="usr_1",
        status=PlaythroughStatus.PLAYING,
        platform="PS5",
        game=GameSummary(id="game_1", title="Foo"),
        collection=CollectionSnippet(id="c1", platform="PS5", acquisition_type=AcquisitionType.DIGITAL),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    assert p.status == PlaythroughStatus.PLAYING
