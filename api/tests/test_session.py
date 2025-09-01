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
