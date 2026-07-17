from fastapi import APIRouter, Request, Response, status

from app.api.deps import SessionDep, SettingsDep
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserRead
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    """Return the peer IP address of the request, if available."""
    return request.client.host if request.client else None


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, session: SessionDep, settings: SettingsDep
) -> UserRead:
    """Register a new user account."""
    service = AuthService(session, settings)
    user = await service.register(
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
        email=payload.email,
        password=payload.password,
    )
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, request: Request, session: SessionDep, settings: SettingsDep
) -> TokenResponse:
    """Authenticate and receive an access and refresh token pair."""
    service = AuthService(session, settings)
    return await service.login(
        email=payload.email,
        password=payload.password,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest, session: SessionDep, settings: SettingsDep
) -> TokenResponse:
    """Rotate the refresh token and issue a new token pair."""
    service = AuthService(session, settings)
    return await service.refresh(refresh_token=payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, session: SessionDep, settings: SettingsDep) -> Response:
    """Revoke the refresh token family."""
    service = AuthService(session, settings)
    await service.logout(refresh_token=payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
