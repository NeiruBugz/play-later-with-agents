from __future__ import annotations

import datetime as dt
import logging
import typing as t
import uuid

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()


def _get_request_id(request: Request) -> str:
    rid = getattr(getattr(request, "state", object()), "request_id", None)
    if not rid:
        rid = uuid.uuid4().hex
    return rid


def _format_response(
    request: Request,
    *,
    status_code: int,
    error: str,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    request_id = _get_request_id(request)
    body = ErrorResponse(
        error=error,
        message=message,
        details=details,
        timestamp=_now_iso(),
        request_id=request_id,
    ).model_dump()
    resp = JSONResponse(status_code=status_code, content=body)
    resp.headers["X-Request-Id"] = request_id
    return resp


async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:  # type: ignore[override]
    code = exc.status_code
    if code == 401:
        err = "authentication_required"
    elif code == 404:
        err = "not_found"
    elif code == 405:
        err = "method_not_allowed"
    else:
        err = "error"
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _format_response(request, status_code=code, error=err, message=message)


async def handle_starlette_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    # Delegate to the same handler logic
    return await handle_http_exception(request, exc)  # type: ignore[arg-type]


async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details: list[ErrorDetail] = []
    for e in exc.errors():
        loc = e.get("loc", [])
        # Drop the leading context like 'body'/'query' for readability
        filtered = [part for part in loc if part not in ("body", "query", "path")]
        field = ".".join(str(p) for p in filtered) or "request"
        details.append(ErrorDetail(field=field, message=e.get("msg", "Invalid value")))
    return _format_response(
        request,
        status_code=422,
        error="validation_error",
        message="Invalid request data",
        details=details or None,
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error: %s", exc)
    return _format_response(
        request,
        status_code=500,
        error="internal_error",
        message="An unexpected error occurred",
    )


def register_exception_handlers(app) -> None:
    app.add_exception_handler(HTTPException, handle_http_exception)
    app.add_exception_handler(StarletteHTTPException, handle_starlette_http_exception)
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)


async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    # Attach a request id if not present
    if not getattr(request.state, "request_id", None):
        request.state.request_id = uuid.uuid4().hex
    response = await call_next(request)
    response.headers.setdefault("X-Request-Id", request.state.request_id)
    return response
