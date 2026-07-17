from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.permission import Permission


class PermissionRepository:
    """Data access for permission records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> Sequence[Permission]:
        """Return all permissions ordered by resource and action."""
        result = await self._session.execute(
            select(Permission).order_by(Permission.resource, Permission.action)
        )
        return result.scalars().all()

    async def get_by_id(self, permission_id: UUID) -> Permission | None:
        """Return the permission with the given id, if any."""
        result = await self._session.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        return result.scalar_one_or_none()

    async def get_by_resource_action(self, resource: str, action: str) -> Permission | None:
        """Return the permission matching a resource and action, if any."""
        result = await self._session.execute(
            select(Permission).where(Permission.resource == resource, Permission.action == action)
        )
        return result.scalar_one_or_none()

    async def create(self, permission: Permission) -> Permission:
        """Persist a new permission and flush to assign its id."""
        self._session.add(permission)
        await self._session.flush()
        return permission
