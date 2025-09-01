from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import Cookie, Header, HTTPException


@dataclass(frozen=True)
class CurrentUser:
    id: str


def get_current_user(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    session_user: Optional[str] = Cookie(default=None, alias="session_user"),
) -> CurrentUser:
    """Auth stub: read user id from header or cookie.

    - Prefer `X-User-Id` header for tests/tools.
    - Fallback to `session_user` cookie to mimic HTTP-only session.
    - Raise 401 if neither provided.
    """
    user_id = x_user_id or session_user
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return CurrentUser(id=user_id)

