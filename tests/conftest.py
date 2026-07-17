from collections.abc import AsyncIterator

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.session import create_db_engine, create_session_factory
from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Yield an HTTP client with the application lifespan running."""
    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as http_client:
            yield http_client


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Yield a database session factory for direct test data setup."""
    settings = get_settings()
    engine = create_db_engine(settings)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()
