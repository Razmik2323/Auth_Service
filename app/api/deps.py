from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.exceptions import ForbiddenError, InvalidTokenError
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.authz import user_can

_bearer = HTTPBearer(auto_error=False)


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a database session bound to the application session factory."""
    factory: async_sessionmaker[AsyncSession] = request.app.state.db_sessionmaker
    async with factory() as session:
        yield session


def provide_settings(request: Request) -> Settings:
    """Return the settings bound to the running application."""
    settings: Settings = request.app.state.settings
    return settings


def provide_redis(request: Request) -> Redis:
    """Return the Redis client bound to the running application."""
    redis: Redis = request.app.state.redis
    return redis


SessionDep = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(provide_settings)]
RedisDep = Annotated[Redis, Depends(provide_redis)]
CredentialsDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


async def get_current_user(
    credentials: CredentialsDep, session: SessionDep, settings: SettingsDep
) -> User:
    """Resolve and validate the authenticated user from a bearer access token."""
    if credentials is None:
        raise InvalidTokenError
    try:
        payload = decode_access_token(
            credentials.credentials,
            settings.secret_key.get_secret_value(),
            settings.jwt_algorithm,
        )
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise InvalidTokenError from exc
    user = await UserRepository(session).get_for_auth(user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise InvalidTokenError
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permission(resource: str, action: str) -> Callable[..., Awaitable[User]]:
    """Build a dependency that enforces a resource and action permission."""

    async def dependency(user: CurrentUser, session: SessionDep, redis: RedisDep) -> User:
        if not await user_can(redis, session, user, resource, action):
            raise ForbiddenError
        return user

    return dependency
