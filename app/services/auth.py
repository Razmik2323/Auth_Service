import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from anyio import to_thread
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.session import Session
from app.models.user import User
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.schemas.auth import TokenResponse

logger = logging.getLogger("app.auth")

MAX_FAILED_LOGINS = 5
LOCKOUT_DURATION = timedelta(minutes=15)


class AuthService:
    """Authentication and session lifecycle operations."""

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._users = UserRepository(session)
        self._sessions = SessionRepository(session)

    async def register(
        self,
        *,
        first_name: str,
        last_name: str,
        middle_name: str | None,
        email: str,
        password: str,
    ) -> User:
        """Create a new user account."""
        if await self._users.get_by_email(email) is not None:
            raise EmailAlreadyExistsError
        password_hash = await to_thread.run_sync(hash_password, password)
        user = User(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            email=email,
            password_hash=password_hash,
        )
        try:
            await self._users.create(user)
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise EmailAlreadyExistsError from exc
        logger.info("user.registered", extra={"user_id": str(user.id)})
        return user

    async def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenResponse:
        """Authenticate a user and issue an access and refresh token pair."""
        now = datetime.now(tz=UTC)
        user = await self._users.get_by_email(email)
        if user is None:
            await to_thread.run_sync(hash_password, password)
            raise InvalidCredentialsError
        if not user.is_active or user.deleted_at is not None:
            raise InvalidCredentialsError
        if user.locked_until is not None and user.locked_until > now:
            raise InvalidCredentialsError
        valid = await to_thread.run_sync(verify_password, password, user.password_hash)
        if not valid:
            await self._register_failed_login(user, now)
            raise InvalidCredentialsError
        user.failed_login_count = 0
        user.locked_until = None
        tokens = await self._issue_session(user, uuid4(), None, user_agent, ip_address, now)
        await self._session.commit()
        logger.info("login.success", extra={"user_id": str(user.id)})
        return tokens

    async def refresh(self, *, refresh_token: str) -> TokenResponse:
        """Rotate a refresh token, revoking the family on reuse."""
        now = datetime.now(tz=UTC)
        record = await self._sessions.get_by_token_hash(hash_token(refresh_token))
        if record is None:
            raise InvalidTokenError
        if record.revoked_at is not None:
            await self._sessions.revoke_family(record.family_id, now)
            await self._session.commit()
            logger.warning("refresh.reuse_detected", extra={"family_id": str(record.family_id)})
            raise InvalidTokenError
        if record.expires_at <= now:
            raise InvalidTokenError
        user = await self._users.get_by_id(record.user_id)
        if user is None or not user.is_active or user.deleted_at is not None:
            raise InvalidTokenError
        record.revoked_at = now
        tokens = await self._issue_session(
            user, record.family_id, record.id, record.user_agent, record.ip_address, now
        )
        await self._session.commit()
        return tokens

    async def logout(self, *, refresh_token: str) -> None:
        """Revoke the whole session family for a refresh token."""
        record = await self._sessions.get_by_token_hash(hash_token(refresh_token))
        if record is not None:
            await self._sessions.revoke_family(record.family_id, datetime.now(tz=UTC))
            await self._session.commit()
            logger.info("logout", extra={"user_id": str(record.user_id)})

    async def _register_failed_login(self, user: User, now: datetime) -> None:
        """Increment the failure counter and lock the account past the threshold."""
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGINS:
            user.locked_until = now + LOCKOUT_DURATION
            user.failed_login_count = 0
        await self._session.commit()

    async def _issue_session(
        self,
        user: User,
        family_id: UUID,
        parent_id: UUID | None,
        user_agent: str | None,
        ip_address: str | None,
        now: datetime,
    ) -> TokenResponse:
        """Create a session row and return freshly signed tokens."""
        raw_refresh, refresh_hash = generate_refresh_token()
        record = Session(
            user_id=user.id,
            family_id=family_id,
            token_hash=refresh_hash,
            parent_id=parent_id,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=now + timedelta(seconds=self._settings.refresh_token_ttl_seconds),
        )
        await self._sessions.create(record)
        access = create_access_token(
            str(user.id),
            self._settings.secret_key.get_secret_value(),
            self._settings.jwt_algorithm,
            self._settings.access_token_ttl_seconds,
        )
        return TokenResponse(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=self._settings.access_token_ttl_seconds,
        )
