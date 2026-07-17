from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role


class RoleRepository:
    """Data access for role records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> Sequence[Role]:
        """Return all roles ordered by name."""
        result = await self._session.execute(select(Role).order_by(Role.name))
        return result.scalars().all()

    async def get_by_id(self, role_id: UUID) -> Role | None:
        """Return the role with the given id, if any."""
        result = await self._session.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Role | None:
        """Return the role with the given name, if any."""
        result = await self._session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def create(self, role: Role) -> Role:
        """Persist a new role and flush to assign its id."""
        self._session.add(role)
        await self._session.flush()
        return role
