from fastapi import Depends
from fastapi.testclient import TestClient

from app.main import app
from app.auth import CurrentUser, get_current_user


@app.get("/api/v1/_auth-check", include_in_schema=False)
def auth_check(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
    return {"user_id": user.id}


def test_auth_required_returns_401(client: TestClient) -> None:
    resp = client.get("/api/v1/_auth-check")
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"] == "authentication_required"
    assert body["message"]
    assert body.get("request_id")


def test_auth_header_allows_access(client: TestClient) -> None:
    resp = client.get("/api/v1/_auth-check", headers={"X-User-Id": "user-123"})
    assert resp.status_code == 200
    assert resp.json() == {"user_id": "user-123"}


def test_auth_cookie_allows_access(client: TestClient) -> None:
    client.cookies.set("session_user", "cookie-user")
    resp = client.get("/api/v1/_auth-check")
    assert resp.status_code == 200
    assert resp.json() == {"user_id": "cookie-user"}
