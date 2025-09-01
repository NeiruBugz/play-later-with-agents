from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, String, func
from sqlalchemy.orm import Session, Mapped, mapped_column

from app.db import SessionLocal
from app.db import Base as _Base


class Base(_Base):
    __abstract__ = True
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid4().hex
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


def _hash_token(token: str) -> str:
    """Generate salted SHA-256 hash of a token.

    Format: salt:hash where both salt and hash are hex-encoded.
    The salt is 32 bytes (64 hex chars) and hash is 32 bytes (64 hex chars).
    """
    # Generate a random 32-byte salt
    salt = secrets.token_bytes(32)
    # Create SHA-256 hash of salt + token
    hash_bytes = hashlib.sha256(salt + token.encode("utf-8")).digest()
    # Return as salt:hash (both hex-encoded)
    return f"{salt.hex()}:{hash_bytes.hex()}"


def _verify_token(token: str, stored_hash: str) -> bool:
    """Verify a token against a stored salted hash."""
    try:
        salt_hex, hash_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        stored_hash_bytes = bytes.fromhex(hash_hex)

        # Compute hash of salt + provided token
        computed_hash = hashlib.sha256(salt + token.encode("utf-8")).digest()

        # Constant-time comparison to prevent timing attacks
        return secrets.compare_digest(computed_hash, stored_hash_bytes)
    except (ValueError, TypeError):
        return False


class SessionRecord(Base):
    __tablename__ = "sessions"

    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


def create_session(
    db: Session, *, user_id: str, refresh_token: Optional[str] = None
) -> SessionRecord:
    """Create a new session record with hashed refresh token."""
    refresh_token_hash = _hash_token(refresh_token) if refresh_token else None
    rec = SessionRecord(user_id=user_id, refresh_token_hash=refresh_token_hash)
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def get_session(db: Session, session_id: str) -> Optional[SessionRecord]:
    """Get a session record by ID."""
    return db.get(SessionRecord, session_id)


def verify_refresh_token(db: Session, session_id: str, refresh_token: str) -> bool:
    """Verify a refresh token against the stored hash for a session."""
    rec = db.get(SessionRecord, session_id)
    if not rec or not rec.active or not rec.refresh_token_hash:
        return False
    return _verify_token(refresh_token, rec.refresh_token_hash)


def update_refresh_token(db: Session, session_id: str, new_refresh_token: str) -> bool:
    """Update the refresh token hash for a session."""
    rec = db.get(SessionRecord, session_id)
    if not rec:
        return False
    rec.refresh_token_hash = _hash_token(new_refresh_token)
    db.add(rec)
    db.commit()
    return True


def deactivate_session(db: Session, session_id: str) -> bool:
    """Deactivate a session by ID."""
    rec = db.get(SessionRecord, session_id)
    if not rec:
        return False
    rec.active = False
    db.add(rec)
    db.commit()
    return True
