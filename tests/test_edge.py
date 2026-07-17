import uuid
from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

AUTH = "/api/v1/auth"
PASSWORD = "Sup3r-Secret-Pass"


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def _payload(email: str) -> dict[str, object]:
    return {
        "first_name": "Ed",
        "last_name": "Case",
        "middle_name": None,
        "email": email,
        "password": PASSWORD,
        "password_repeat": PASSWORD,
    }


@pytest.fixture
async def expiring_client() -> AsyncIterator[AsyncClient]:
    """Yield a client whose refresh tokens expire immediately."""
    settings = Settings(rate_limit_enabled=False, refresh_token_ttl_seconds=0)
    app = create_app(settings)
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client


@pytest.fixture
async def redis_down_client() -> AsyncIterator[AsyncClient]:
    """Yield a client whose Redis dependency is unreachable."""
    settings = Settings(rate_limit_enabled=False, redis_url="redis://127.0.0.1:6399/0")
    app = create_app(settings)
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client


async def test_expired_refresh_token_is_rejected(expiring_client: AsyncClient) -> None:
    """A refresh token past its expiry is rejected with 401."""
    email = _email()
    await expiring_client.post(f"{AUTH}/register", json=_payload(email))
    login = await expiring_client.post(f"{AUTH}/login", json={"email": email, "password": PASSWORD})
    refresh = login.json()["refresh_token"]

    response = await expiring_client.post(f"{AUTH}/refresh", json={"refresh_token": refresh})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_token"


async def test_health_reports_redis_down(redis_down_client: AsyncClient) -> None:
    """Health degrades to report an unreachable Redis while the database is up."""
    response = await redis_down_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["db"] == "ok"
    assert body["redis"] == "down"
    assert body["status"] == "degraded"
