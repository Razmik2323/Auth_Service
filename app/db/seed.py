import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import create_db_engine, create_session_factory
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

logger = logging.getLogger("app.seed")

DEFAULT_PASSWORD = "ChangeMe-Please-1"

PERMISSIONS: list[tuple[str, str, str]] = [
    ("documents", "read", "Read documents"),
    ("documents", "create", "Create documents"),
    ("documents", "update", "Update documents"),
    ("documents", "delete", "Delete documents"),
    ("reports", "read", "Read reports"),
    ("reports", "create", "Create reports"),
    ("projects", "read", "Read projects"),
    ("rbac", "manage", "Manage roles and permissions"),
]

ROLES: dict[str, list[tuple[str, str]]] = {
    "admin": [
        ("documents", "read"),
        ("documents", "create"),
        ("documents", "update"),
        ("documents", "delete"),
        ("reports", "read"),
        ("reports", "create"),
        ("projects", "read"),
        ("rbac", "manage"),
    ],
    "manager": [
        ("documents", "read"),
        ("documents", "create"),
        ("reports", "read"),
    ],
    "user": [
        ("documents", "read"),
    ],
}

USERS: list[tuple[str, str, str, str]] = [
    ("admin@example.com", "Admin", "Root", "admin"),
    ("manager@example.com", "Manager", "Lead", "manager"),
    ("user@example.com", "Regular", "User", "user"),
]


async def seed(session: AsyncSession) -> None:
    """Populate the database with demonstration roles, permissions, and users."""
    permissions = await _seed_permissions(session)
    roles = await _seed_roles(session, permissions)
    await _seed_users(session, roles)
    await session.commit()
    logger.info("seed.completed")


async def _seed_permissions(session: AsyncSession) -> dict[tuple[str, str], Permission]:
    """Create the permission catalog, returning it keyed by resource and action."""
    catalog: dict[tuple[str, str], Permission] = {}
    for resource, action, description in PERMISSIONS:
        result = await session.execute(
            select(Permission).where(Permission.resource == resource, Permission.action == action)
        )
        permission = result.scalar_one_or_none()
        if permission is None:
            permission = Permission(resource=resource, action=action, description=description)
            session.add(permission)
        catalog[(resource, action)] = permission
    await session.flush()
    return catalog


async def _seed_roles(
    session: AsyncSession, permissions: dict[tuple[str, str], Permission]
) -> dict[str, Role]:
    """Create roles and attach their permissions, returning them keyed by name."""
    roles: dict[str, Role] = {}
    for name, permission_keys in ROLES.items():
        result = await session.execute(select(Role).where(Role.name == name))
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(name=name, description=f"Seeded {name} role", permissions=[])
            session.add(role)
            await session.flush()
        existing_ids = {permission.id for permission in role.permissions}
        for key in permission_keys:
            permission = permissions[key]
            if permission.id not in existing_ids:
                role.permissions.append(permission)
        roles[name] = role
    await session.flush()
    return roles


async def _seed_users(session: AsyncSession, roles: dict[str, Role]) -> None:
    """Create demonstration users and assign their roles."""
    password_hash = hash_password(DEFAULT_PASSWORD)
    for email, first_name, last_name, role_name in USERS:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                first_name=first_name,
                last_name=last_name,
                middle_name=None,
                email=email,
                password_hash=password_hash,
                roles=[],
            )
            session.add(user)
            await session.flush()
        role = roles[role_name]
        if all(assigned.id != role.id for assigned in user.roles):
            user.roles.append(role)


async def run() -> None:
    """Connect using application settings and seed the database."""
    settings = get_settings()
    engine = create_db_engine(settings)
    factory = create_session_factory(engine)
    try:
        async with factory() as session:
            await seed(session)
    finally:
        await engine.dispose()


def main() -> None:
    """Console entry point for seeding."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
