import uuid
from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app

ME = "/api/v1/users/me"


@pytest.fixture
async def limited_client() -> AsyncIterator[AsyncClient]:
    """Yield a client whose app enforces a low default rate limit."""
    settings = Settings(
        rate_limit_enabled=True,
        rate_limit_default_max=3,
        rate_limit_default_window_seconds=60,
    )
    app = create_app(settings)
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client


async def test_rate_limit_returns_429_after_threshold(limited_client: AsyncClient) -> None:
    """Requests beyond the window limit are rejected with 429 and Retry-After."""
    headers = {"X-Real-IP": f"198.51.100.{uuid.uuid4().int % 250}"}
    for _ in range(3):
        allowed = await limited_client.get(ME, headers=headers)
        assert allowed.status_code == 401
    blocked = await limited_client.get(ME, headers=headers)
    assert blocked.status_code == 429
    assert "retry-after" in {key.lower() for key in blocked.headers}


async def test_rate_limit_is_isolated_per_ip(limited_client: AsyncClient) -> None:
    """Exhausting one IP's budget does not affect another IP."""
    ip_a = {"X-Real-IP": "203.0.113.10"}
    ip_b = {"X-Real-IP": "203.0.113.11"}
    for _ in range(4):
        await limited_client.get(ME, headers=ip_a)
    assert (await limited_client.get(ME, headers=ip_a)).status_code == 429
    assert (await limited_client.get(ME, headers=ip_b)).status_code == 401


async def test_security_headers_present(client: AsyncClient) -> None:
    """Every response carries the hardening headers."""
    response = await client.get("/health")
    headers = {key.lower() for key in response.headers}
    assert "x-content-type-options" in headers
    assert "x-frame-options" in headers
    assert "referrer-policy" in headers
