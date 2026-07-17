from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.schemas.user import ChangePasswordRequest, UserRead, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_me(user: CurrentUser) -> UserRead:
    """Return the authenticated user's profile."""
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate, user: CurrentUser, session: SessionDep, settings: SettingsDep
) -> UserRead:
    """Update the authenticated user's profile."""
    service = UserService(session, settings)
    updated = await service.update_profile(user, payload.model_dump(exclude_unset=True))
    return UserRead.model_validate(updated)


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest, user: CurrentUser, session: SessionDep, settings: SettingsDep
) -> Response:
    """Change the authenticated user's password and revoke all sessions."""
    service = UserService(session, settings)
    await service.change_password(user, payload.current_password, payload.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(user: CurrentUser, session: SessionDep, settings: SettingsDep) -> Response:
    """Soft-delete the authenticated user's account and revoke all sessions."""
    service = UserService(session, settings)
    await service.soft_delete(user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
