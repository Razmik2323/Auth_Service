import logging

from fastapi import APIRouter, Request
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])
logger = logging.getLogger("app.health")


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Return service health including database and cache status."""
    settings = get_settings()
    db_ok = await _check_db(request.app.state.db_sessionmaker)
    redis_ok = await _check_redis(request.app.state.redis)
    status = "ok" if db_ok and redis_ok else "degraded"
    return HealthResponse(
        status=status,
        env=settings.app_env,
        version=settings.app_version,
        db="ok" if db_ok else "down",
        redis="ok" if redis_ok else "down",
    )


async def _check_db(session_factory: async_sessionmaker[AsyncSession]) -> bool:
    """Return True when the database answers a trivial query."""
    try:
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        logger.warning("health.db_unavailable", exc_info=True)
        return False
    return True


async def _check_redis(client: Redis) -> bool:
    """Return True when Redis answers a ping."""
    try:
        await client.ping()
    except Exception:
        logger.warning("health.redis_unavailable", exc_info=True)
        return False
    return True
