import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.v1 import health
from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging
from app.db.redis import create_redis
from app.db.session import create_db_engine, create_session_factory
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = logging.getLogger("app.lifespan")


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert a domain AppError into a structured JSON response."""
    if not isinstance(exc, AppError):
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "code": exc.code},
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown."""
    settings: Settings = app.state.settings
    engine = create_db_engine(settings)
    app.state.db_engine = engine
    app.state.db_sessionmaker = create_session_factory(engine)
    app.state.redis = create_redis(settings)
    logger.info("app.startup")
    try:
        yield
    finally:
        await app.state.redis.aclose()
        await engine.dispose()
        logger.info("app.shutdown")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings)
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.app_debug,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(AppError, _app_error_handler)
    app.include_router(health.router)
    app.include_router(api_router)
    return app


app = create_app()
