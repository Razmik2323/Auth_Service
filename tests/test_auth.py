import uuid

from httpx import AsyncClient

BASE = "/api/v1/auth"
PASSWORD = "Sup3r-Secret-Pass"


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def _register_payload(email: str) -> dict[str, str]:
    return {
        "first_name": "Ivan",
        "last_name": "Petrov",
        "middle_name": "Sergeevich",
        "email": email,
        "password": PASSWORD,
        "password_repeat": PASSWORD,
    }


async def test_register_login_refresh_logout(client: AsyncClient) -> None:
    """A user can register, log in, refresh, and log out."""
    email = _email()
    registered = await client.post(f"{BASE}/register", json=_register_payload(email))
    assert registered.status_code == 201
    body = registered.json()
    assert body["email"] == email
    assert "password" not in body
    assert "password_hash" not in body

    logged_in = await client.post(f"{BASE}/login", json={"email": email, "password": PASSWORD})
    assert logged_in.status_code == 200
    tokens = logged_in.json()
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    refreshed = await client.post(
        f"{BASE}/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != tokens["refresh_token"]

    logged_out = await client.post(
        f"{BASE}/logout", json={"refresh_token": refreshed.json()["refresh_token"]}
    )
    assert logged_out.status_code == 204


async def test_duplicate_email_conflict(client: AsyncClient) -> None:
    """Registering an existing email returns 409."""
    email = _email()
    first = await client.post(f"{BASE}/register", json=_register_payload(email))
    assert first.status_code == 201
    second = await client.post(f"{BASE}/register", json=_register_payload(email))
    assert second.status_code == 409
    assert second.json()["code"] == "email_already_exists"


async def test_login_wrong_password_is_generic_401(client: AsyncClient) -> None:
    """A wrong password returns a generic 401."""
    email = _email()
    await client.post(f"{BASE}/register", json=_register_payload(email))
    response = await client.post(
        f"{BASE}/login", json={"email": email, "password": "wrong-pass-123"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


async def test_login_unknown_email_is_generic_401(client: AsyncClient) -> None:
    """An unknown email returns the same generic 401."""
    response = await client.post(f"{BASE}/login", json={"email": _email(), "password": PASSWORD})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"


async def test_refresh_reuse_revokes_family(client: AsyncClient) -> None:
    """Reusing a rotated refresh token revokes the whole family."""
    email = _email()
    await client.post(f"{BASE}/register", json=_register_payload(email))
    logged_in = await client.post(f"{BASE}/login", json={"email": email, "password": PASSWORD})
    old_refresh = logged_in.json()["refresh_token"]

    rotated = await client.post(f"{BASE}/refresh", json={"refresh_token": old_refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["refresh_token"]

    reused = await client.post(f"{BASE}/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401

    after_reuse = await client.post(f"{BASE}/refresh", json={"refresh_token": new_refresh})
    assert after_reuse.status_code == 401


async def test_password_mismatch_is_422(client: AsyncClient) -> None:
    """A mismatched password confirmation fails validation."""
    payload = _register_payload(_email())
    payload["password_repeat"] = "different-pass-123"
    response = await client.post(f"{BASE}/register", json=payload)
    assert response.status_code == 422


async def test_unknown_refresh_token_is_401(client: AsyncClient) -> None:
    """An unknown refresh token is rejected."""
    response = await client.post(f"{BASE}/refresh", json={"refresh_token": "does-not-exist"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


async def test_logout_is_idempotent(client: AsyncClient) -> None:
    """Logging out twice with the same token stays successful."""
    email = _email()
    await client.post(f"{BASE}/register", json=_register_payload(email))
    login = await client.post(f"{BASE}/login", json={"email": email, "password": PASSWORD})
    refresh = login.json()["refresh_token"]

    first = await client.post(f"{BASE}/logout", json={"refresh_token": refresh})
    assert first.status_code == 204
    second = await client.post(f"{BASE}/logout", json={"refresh_token": refresh})
    assert second.status_code == 204


async def test_repeated_failed_logins_lock_the_account(client: AsyncClient) -> None:
    """Five failed logins lock the account so the correct password also fails."""
    email = _email()
    await client.post(f"{BASE}/register", json=_register_payload(email))
    for _ in range(5):
        bad = await client.post(
            f"{BASE}/login", json={"email": email, "password": "wrong-pass-000"}
        )
        assert bad.status_code == 401
    locked = await client.post(f"{BASE}/login", json={"email": email, "password": PASSWORD})
    assert locked.status_code == 401
