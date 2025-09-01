from typing import Any
import asyncio

from fastapi.testclient import TestClient
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from app.exception_handlers import handle_request_validation_error


def test_404_error_shape(client: TestClient) -> None:
    resp = client.get("/this/route/does/not/exist")
    assert resp.status_code == 404
    data = resp.json()
    assert data["error"] == "not_found"
    assert isinstance(data["message"], str) and data["message"]
    assert "timestamp" in data and isinstance(data["timestamp"], str)
    assert "request_id" in data and isinstance(data["request_id"], str)
    # Request id header must match body
    assert resp.headers.get("X-Request-Id") == data["request_id"]


def test_validation_error_handler_formats_details() -> None:
    scope: dict[str, Any] = {"type": "http", "method": "GET", "path": "/"}
    request = Request(scope)  # type: ignore[arg-type]
    exc = RequestValidationError([
        {
            "type": "missing",
            "loc": ("body", "title"),
            "msg": "Field required",
            "input": None,
        }
    ])

    resp = asyncio.run(handle_request_validation_error(request, exc))
    assert resp.status_code == 422
    data = resp.body.decode()
    assert "validation_error" in data
    assert "title" in data
    assert "Field required" in data
