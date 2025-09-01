from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db import get_db


# Register a temporary route for exercising the DB dependency
@app.get("/api/v1/_db-check")
def db_check(db: Session = Depends(get_db)) -> dict[str, bool]:
    # We don't run queries yet; just ensure we can acquire a session
    assert isinstance(db, Session)
    return {"ok": True}


def test_db_dependency(client: TestClient) -> None:
    resp = client.get("/api/v1/_db-check")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
