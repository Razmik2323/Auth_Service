import uuid

from httpx import AsyncClient, Response

AUTH = "/api/v1/auth"
ME = "/api/v1/users/me"
PASSWORD = "Sup3r-Secret-Pass"
NEW_PASSWORD = "New-Sup3r-Secret-1"


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register(client: AsyncClient, email: str) -> Response:
    payload = {
        "first_name": "Ivan",
        "last_name": "Petrov",
        "middle_name": "Sergeevich",
        "email": email,
        "password": PASSWORD,
        "password_repeat": PASSWORD,
    }
    return await client.post(f"{AUTH}/register", json=payload)


async def _login(client: AsyncClient, email: str, password: str = PASSWORD) -> Response:
    return await client.post(f"{AUTH}/login", json={"email": email, "password": password})


async def test_update_profile(client: AsyncClient) -> None:
    """A user can update its own profile."""
    email = _email()
    await _register(client, email)
    token = (await _login(client, email)).json()["access_token"]

    updated = await client.patch(ME, json={"last_name": "Sidorov"}, headers=_auth_header(token))
    assert updated.status_code == 200
    assert updated.json()["last_name"] == "Sidorov"

    profile = await client.get(ME, headers=_auth_header(token))
    assert profile.json()["last_name"] == "Sidorov"


async def test_change_password_rotates_and_revokes(client: AsyncClient) -> None:
    """Changing the password revokes sessions and swaps the credential."""
    email = _email()
    await _register(client, email)
    login = await _login(client, email)
    token = login.json()["access_token"]
    old_refresh = login.json()["refresh_token"]

    changed = await client.post(
        f"{ME}/change-password",
        json={
            "current_password": PASSWORD,
            "new_password": NEW_PASSWORD,
            "new_password_repeat": NEW_PASSWORD,
        },
        headers=_auth_header(token),
    )
    assert changed.status_code == 204

    reused = await client.post(f"{AUTH}/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401
    assert (await _login(client, email, PASSWORD)).status_code == 401
    assert (await _login(client, email, NEW_PASSWORD)).status_code == 200


async def test_change_password_wrong_current_is_400(client: AsyncClient) -> None:
    """A wrong current password is rejected with 400."""
    email = _email()
    await _register(client, email)
    token = (await _login(client, email)).json()["access_token"]

    response = await client.post(
        f"{ME}/change-password",
        json={
            "current_password": "wrong-pass-123",
            "new_password": NEW_PASSWORD,
            "new_password_repeat": NEW_PASSWORD,
        },
        headers=_auth_header(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_current_password"


async def test_soft_delete_blocks_access_and_login(client: AsyncClient) -> None:
    """Soft-deleting the account blocks the token and future logins."""
    email = _email()
    await _register(client, email)
    token = (await _login(client, email)).json()["access_token"]

    deleted = await client.delete(ME, headers=_auth_header(token))
    assert deleted.status_code == 204

    profile = await client.get(ME, headers=_auth_header(token))
    assert profile.status_code == 401
    assert (await _login(client, email)).status_code == 401


async def test_update_requires_authentication(client: AsyncClient) -> None:
    """Profile update without a token returns 401."""
    response = await client.patch(ME, json={"last_name": "Nobody"})
    assert response.status_code == 401
