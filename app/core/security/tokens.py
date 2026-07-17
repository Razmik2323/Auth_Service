import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt

ACCESS_TOKEN_TYPE = "access"


def create_access_token(subject: str, secret_key: str, algorithm: str, ttl_seconds: int) -> str:
    """Create a signed JWT access token for the subject."""
    now = datetime.now(tz=UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "jti": str(uuid4()),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "type": ACCESS_TOKEN_TYPE,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(token: str, secret_key: str, algorithm: str) -> dict[str, Any]:
    """Decode and validate a JWT access token, raising on any problem."""
    payload: dict[str, Any] = jwt.decode(
        token,
        secret_key,
        algorithms=[algorithm],
        options={"require": ["exp", "iat", "sub", "jti"]},
    )
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise jwt.InvalidTokenError("unexpected token type")
    return payload


def generate_refresh_token() -> tuple[str, str]:
    """Return a new opaque refresh token and its SHA-256 hash."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    """Return the SHA-256 hex digest of an opaque token."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
