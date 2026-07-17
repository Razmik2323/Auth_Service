from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


class SessionRepository:
    """Data access for refresh-token sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, record: Session) -> Session:
        """Persist a new session and flush to assign its id."""
        self._session.add(record)
        await self._session.flush()
        return record

    async def get_by_token_hash(self, token_hash: str) -> Session | None:
        """Return the session matching a refresh-token hash, if any."""
        result = await self._session.execute(
            select(Session).where(Session.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_family(self, family_id: UUID, moment: datetime) -> None:
        """Revoke every active session sharing the given family id."""
        await self._session.execute(
            update(Session)
            .where(Session.family_id == family_id, Session.revoked_at.is_(None))
            .values(revoked_at=moment)
        )

    async def revoke_all_for_user(self, user_id: UUID, moment: datetime) -> None:
        """Revoke every active session belonging to the user."""
        await self._session.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=moment)
        )
