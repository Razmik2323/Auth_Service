import json

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.associations import role_permissions, user_roles
from app.models.permission import Permission
from app.models.user import User

CACHE_TTL_SECONDS = 30


async def user_can(
    redis: Redis, session: AsyncSession, user: User, resource: str, action: str
) -> bool:
    """Return True when the user may perform the action on the resource."""
    if user.is_superuser:
        return True
    pairs = await _permission_pairs(redis, session, user)
    return (resource, action) in pairs


async def _permission_pairs(
    redis: Redis, session: AsyncSession, user: User
) -> set[tuple[str, str]]:
    """Return the user's permissions as (resource, action), cached in Redis."""
    key = f"perms:{user.id}"
    cached = await redis.get(key)
    if cached is not None:
        return {(item[0], item[1]) for item in json.loads(cached)}
    result = await session.execute(
        select(Permission.resource, Permission.action)
        .join(role_permissions, role_permissions.c.permission_id == Permission.id)
        .join(user_roles, user_roles.c.role_id == role_permissions.c.role_id)
        .where(user_roles.c.user_id == user.id)
    )
    pairs = {(resource, action) for resource, action in result.all()}
    await redis.set(key, json.dumps(sorted(pairs)), ex=CACHE_TTL_SECONDS)
    return pairs


async def invalidate_user_permissions(redis: Redis, user_id: object) -> None:
    """Drop the cached permission set for a single user."""
    await redis.delete(f"perms:{user_id}")


async def invalidate_all_permissions(redis: Redis) -> None:
    """Drop every cached permission set after a role's permissions change."""
    async for key in redis.scan_iter(match="perms:*"):
        await redis.delete(key)
