from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.user import User


class UserRepository:
    """Data access for user records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> User | None:
        """Return the user with the given email, if any."""
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return the user with the given id, eagerly loading roles."""
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_for_auth(self, user_id: UUID) -> User | None:
        """Return the user for authentication without loading roles."""
        result = await self._session.execute(
            select(User).where(User.id == user_id).options(noload(User.roles))
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        """Persist a new user and flush to assign its id."""
        self._session.add(user)
        await self._session.flush()
        return user
