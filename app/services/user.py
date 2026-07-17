from datetime import UTC, datetime
from typing import Any

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import InvalidCurrentPasswordError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.session import SessionRepository

_EDITABLE_FIELDS = ("first_name", "last_name", "middle_name")
_REQUIRED_FIELDS = ("first_name", "last_name")


class UserService:
    """Self-service operations for the authenticated user."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._sessions = SessionRepository(session)

    async def update_profile(self, user: User, updates: dict[str, Any]) -> User:
        """Apply a partial profile update, ignoring nulls for required fields."""
        for field in _EDITABLE_FIELDS:
            if field not in updates:
                continue
            value = updates[field]
            if value is None and field in _REQUIRED_FIELDS:
                continue
            setattr(user, field, value)
        await self._session.commit()
        return user

    async def change_password(self, user: User, current_password: str, new_password: str) -> None:
        """Verify the current password, set a new one, and revoke all sessions."""
        valid = await to_thread.run_sync(verify_password, current_password, user.password_hash)
        if not valid:
            raise InvalidCurrentPasswordError
        user.password_hash = await to_thread.run_sync(hash_password, new_password)
        await self._sessions.revoke_all_for_user(user.id, datetime.now(tz=UTC))
        await self._session.commit()

    async def soft_delete(self, user: User) -> None:
        """Deactivate the account, mark it deleted, and revoke all sessions."""
        now = datetime.now(tz=UTC)
        user.is_active = False
        user.deleted_at = now
        await self._sessions.revoke_all_for_user(user.id, now)
        await self._session.commit()
