import uuid

from httpx import AsyncClient

AUTH = "/api/v1/auth"
ME = "/api/v1/users/me"
PASSWORD = "Sup3r-Secret-Pass"


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


async def _register_and_login(client: AsyncClient) -> str:
    email = _email()
    payload = {
        "first_name": "Ann",
        "last_name": "Smith",
        "middle_name": None,
        "email": email,
        "password": PASSWORD,
        "password_repeat": PASSWORD,
    }
    await client.post(f"{AUTH}/register", json=payload)
    login = await client.post(f"{AUTH}/login", json={"email": email, "password": PASSWORD})
    return str(login.json()["access_token"])


async def test_me_requires_authentication(client: AsyncClient) -> None:
    """Accessing the profile without a token returns 401."""
    response = await client.get(ME)
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


async def test_me_rejects_invalid_token(client: AsyncClient) -> None:
    """A malformed bearer token returns 401."""
    response = await client.get(ME, headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


async def test_me_returns_profile_with_token(client: AsyncClient) -> None:
    """A valid token returns the authenticated user's profile."""
    token = await _register_and_login(client)
    response = await client.get(ME, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "email" in response.json()
