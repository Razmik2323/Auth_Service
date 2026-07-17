from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.deps import RedisDep, SessionDep, require_permission
from app.core.exceptions import ConflictError, NotFoundError
from app.models.permission import Permission
from app.models.role import Role
from app.repositories.permission import PermissionRepository
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository
from app.schemas.rbac import (
    AssignPermissionRequest,
    AssignRoleRequest,
    PermissionCreate,
    PermissionRead,
    RoleCreate,
    RoleRead,
)
from app.services.authz import invalidate_all_permissions, invalidate_user_permissions

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_permission("rbac", "manage"))],
)


@router.get("/permissions", response_model=list[PermissionRead])
async def list_permissions(session: SessionDep) -> Sequence[Permission]:
    """List all permissions."""
    return await PermissionRepository(session).list_all()


@router.post("/permissions", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
async def create_permission(payload: PermissionCreate, session: SessionDep) -> Permission:
    """Create a new permission."""
    repo = PermissionRepository(session)
    if await repo.get_by_resource_action(payload.resource, payload.action) is not None:
        raise ConflictError
    permission = Permission(
        resource=payload.resource, action=payload.action, description=payload.description
    )
    await repo.create(permission)
    await session.commit()
    return permission


@router.get("/roles", response_model=list[RoleRead])
async def list_roles(session: SessionDep) -> Sequence[Role]:
    """List all roles with their permissions."""
    return await RoleRepository(session).list_all()


@router.post("/roles", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(payload: RoleCreate, session: SessionDep) -> Role:
    """Create a new role."""
    repo = RoleRepository(session)
    if await repo.get_by_name(payload.name) is not None:
        raise ConflictError
    role = Role(name=payload.name, description=payload.description, permissions=[])
    await repo.create(role)
    await session.commit()
    return role


@router.get("/roles/{role_id}", response_model=RoleRead)
async def get_role(role_id: UUID, session: SessionDep) -> Role:
    """Return a single role with its permissions."""
    role = await RoleRepository(session).get_by_id(role_id)
    if role is None:
        raise NotFoundError
    return role


@router.post("/roles/{role_id}/permissions", response_model=RoleRead)
async def attach_permission(
    role_id: UUID, payload: AssignPermissionRequest, session: SessionDep, redis: RedisDep
) -> Role:
    """Grant a permission to a role."""
    role = await RoleRepository(session).get_by_id(role_id)
    if role is None:
        raise NotFoundError
    permission = await PermissionRepository(session).get_by_id(payload.permission_id)
    if permission is None:
        raise NotFoundError
    if all(item.id != permission.id for item in role.permissions):
        role.permissions.append(permission)
        await session.commit()
        await invalidate_all_permissions(redis)
    return role


@router.delete("/roles/{role_id}/permissions/{permission_id}", response_model=RoleRead)
async def detach_permission(
    role_id: UUID, permission_id: UUID, session: SessionDep, redis: RedisDep
) -> Role:
    """Revoke a permission from a role."""
    role = await RoleRepository(session).get_by_id(role_id)
    if role is None:
        raise NotFoundError
    role.permissions = [item for item in role.permissions if item.id != permission_id]
    await session.commit()
    await invalidate_all_permissions(redis)
    return role


@router.post("/users/{user_id}/roles", response_model=list[RoleRead])
async def attach_role(
    user_id: UUID, payload: AssignRoleRequest, session: SessionDep, redis: RedisDep
) -> Sequence[Role]:
    """Assign a role to a user."""
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise NotFoundError
    role = await RoleRepository(session).get_by_id(payload.role_id)
    if role is None:
        raise NotFoundError
    if all(item.id != role.id for item in user.roles):
        user.roles.append(role)
        await session.commit()
        await invalidate_user_permissions(redis, user_id)
    return user.roles


@router.delete("/users/{user_id}/roles/{role_id}", response_model=list[RoleRead])
async def detach_role(
    user_id: UUID, role_id: UUID, session: SessionDep, redis: RedisDep
) -> Sequence[Role]:
    """Remove a role from a user."""
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise NotFoundError
    user.roles = [item for item in user.roles if item.id != role_id]
    await session.commit()
    await invalidate_user_permissions(redis, user_id)
    return user.roles
