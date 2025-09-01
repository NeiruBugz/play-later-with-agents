from typing import Optional

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db import get_db, Base as DBBase, SessionLocal
from app.session_store import (
    create_session,
    get_session,
    deactivate_session,
    verify_refresh_token,
    update_refresh_token,
    SessionRecord,
)


# Ensure tables exist for tests
DBBase.metadata.create_all(bind=SessionLocal.kw["bind"])


@app.post("/api/v1/_test/session", include_in_schema=False)
def _create_session(user_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    rec = create_session(db, user_id=user_id)
    return {"id": rec.id, "user_id": rec.user_id}


@app.get("/api/v1/_test/session/{sid}", include_in_schema=False)
def _get_session(sid: str, db: Session = Depends(get_db)) -> dict[str, Optional[str]]:
    rec = get_session(db, sid)
    return {"id": rec.id if rec else None, "user_id": rec.user_id if rec else None}


@app.post("/api/v1/_test/session/{sid}/deactivate", include_in_schema=False)
def _deactivate_session(sid: str, db: Session = Depends(get_db)) -> dict[str, bool]:
    ok = deactivate_session(db, sid)
    return {"success": ok}


def test_session_crud_via_store(client: TestClient) -> None:
    # Create
    r = client.post("/api/v1/_test/session", params={"user_id": "user-x"})
    assert r.status_code == 200
    sid = r.json()["id"]

    # Fetch
    r = client.get(f"/api/v1/_test/session/{sid}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == sid
    assert data["user_id"] == "user-x"

    # Deactivate
    r = client.post(f"/api/v1/_test/session/{sid}/deactivate")
    assert r.status_code == 200
    assert r.json()["success"] is True


def test_refresh_token_hashing_and_verification() -> None:
    """Test that refresh tokens are properly hashed and can be verified."""
    with SessionLocal() as db:
        # Create session with refresh token
        test_token = "super-secret-refresh-token-123"
        session = create_session(db, user_id="test-user", refresh_token=test_token)

        # Verify the token is hashed (not stored in plaintext)
        assert session.refresh_token_hash is not None
        assert test_token not in session.refresh_token_hash
        assert ":" in session.refresh_token_hash  # Should have salt:hash format

        # Verify correct token returns True
        assert verify_refresh_token(db, session.id, test_token) is True

        # Verify wrong token returns False
        assert verify_refresh_token(db, session.id, "wrong-token") is False

        # Test updating refresh token
        new_token = "new-refresh-token-456"
        assert update_refresh_token(db, session.id, new_token) is True

        # Old token should no longer work
        assert verify_refresh_token(db, session.id, test_token) is False

        # New token should work
        assert verify_refresh_token(db, session.id, new_token) is True

        # Deactivated session should fail verification
        deactivate_session(db, session.id)
        assert verify_refresh_token(db, session.id, new_token) is False


def test_session_without_refresh_token() -> None:
    """Test session creation without refresh token."""
    with SessionLocal() as db:
        # Create session without refresh token
        session = create_session(db, user_id="test-user-no-token")

        # Should have no refresh token hash
        assert session.refresh_token_hash is None

        # Verification should fail
        assert verify_refresh_token(db, session.id, "any-token") is False
