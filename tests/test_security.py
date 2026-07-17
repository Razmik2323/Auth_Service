import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)

SECRET = "unit-test-secret-key-0123456789ab"
ALGORITHM = "HS256"


def test_password_hash_roundtrip() -> None:
    """A hashed password verifies against the original."""
    hashed = hash_password("S3cur3-pass")
    assert hashed != "S3cur3-pass"
    assert verify_password("S3cur3-pass", hashed)


def test_password_wrong_rejected() -> None:
    """A wrong password fails verification."""
    hashed = hash_password("correct-horse")
    assert not verify_password("wrong-horse", hashed)


def test_needs_rehash_false_for_current_params() -> None:
    """A freshly created hash does not require rehashing."""
    hashed = hash_password("whatever-123")
    assert needs_rehash(hashed) is False


def test_access_token_roundtrip() -> None:
    """A valid access token decodes back to its subject."""
    token = create_access_token("user-1", SECRET, ALGORITHM, 900)
    payload = decode_access_token(token, SECRET, ALGORITHM)
    assert payload["sub"] == "user-1"
    assert payload["type"] == "access"
    assert "jti" in payload


def test_expired_token_rejected() -> None:
    """An expired access token is rejected."""
    token = create_access_token("user-1", SECRET, ALGORITHM, -1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(token, SECRET, ALGORITHM)


def test_tampered_token_rejected() -> None:
    """A token signed with another key is rejected."""
    token = create_access_token("user-1", SECRET, ALGORITHM, 900)
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, "other-wrong-secret-key-0123456789", ALGORITHM)


def test_wrong_token_type_rejected() -> None:
    """A token whose type is not access is rejected."""
    token = jwt.encode(
        {"sub": "u", "jti": "j", "iat": 1, "exp": 9999999999, "type": "refresh"},
        SECRET,
        algorithm=ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, SECRET, ALGORITHM)


def test_refresh_token_hash_matches() -> None:
    """A generated refresh token hashes to the returned digest."""
    raw, digest = generate_refresh_token()
    assert hash_token(raw) == digest
    assert raw != digest
