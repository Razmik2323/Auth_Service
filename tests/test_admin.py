import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User

AUTH = "/api/v1/auth"
ADMIN = "/api/v1/admin"
PASSWORD = "Sup3r-Secret-Pass"


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register_login(client: AsyncClient, email: str) -> str:
    payload = {
        "first_name": "Ad",
        "last_name": "Min",
        "middle_name": None,
        "email": email,
        "password": PASSWORD,
        "password_repeat": PASSWORD,
    }
    await client.post(f"{AUTH}/register", json=payload)
    login = await client.post(f"{AUTH}/login", json={"email": email, "password": PASSWORD})
    return str(login.json()["access_token"])


async def _promote_superuser(factory: async_sessionmaker[AsyncSession], email: str) -> None:
    async with factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_superuser = True
        await session.commit()


async def _user_id(factory: async_sessionmaker[AsyncSession], email: str) -> str:
    async with factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        return str(result.scalar_one().id)


async def test_admin_requires_authentication(client: AsyncClient) -> None:
    """Admin endpoints reject unauthenticated requests with 401."""
    response = await client.get(f"{ADMIN}/roles")
    assert response.status_code == 401


async def test_admin_forbidden_for_regular_user(client: AsyncClient) -> None:
    """A regular user without the manage permission gets 403."""
    token = await _register_login(client, _email())
    response = await client.get(f"{ADMIN}/roles", headers=_auth_header(token))
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_superuser_can_manage_roles_and_permissions(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """A superuser can create and read roles and permissions."""
    email = _email()
    token = await _register_login(client, email)
    await _promote_superuser(session_factory, email)

    created_perm = await client.post(
        f"{ADMIN}/permissions",
        json={"resource": "documents", "action": "read", "description": "Read documents"},
        headers=_auth_header(token),
    )
    assert created_perm.status_code == 201

    created_role = await client.post(
        f"{ADMIN}/roles",
        json={"name": f"role-{uuid.uuid4().hex[:8]}", "description": "Test"},
        headers=_auth_header(token),
    )
    assert created_role.status_code == 201
    role_id = created_role.json()["id"]
    assert created_role.json()["permissions"] == []

    roles = await client.get(f"{ADMIN}/roles", headers=_auth_header(token))
    assert roles.status_code == 200
    assert any(item["id"] == role_id for item in roles.json())

    single = await client.get(f"{ADMIN}/roles/{role_id}", headers=_auth_header(token))
    assert single.status_code == 200


async def test_duplicate_permission_conflict(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Creating the same permission twice returns 409."""
    email = _email()
    token = await _register_login(client, email)
    await _promote_superuser(session_factory, email)

    body = {"resource": f"res-{uuid.uuid4().hex[:8]}", "action": "read"}
    first = await client.post(f"{ADMIN}/permissions", json=body, headers=_auth_header(token))
    assert first.status_code == 201
    second = await client.post(f"{ADMIN}/permissions", json=body, headers=_auth_header(token))
    assert second.status_code == 409


async def test_missing_role_returns_404(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Requesting a non-existent role returns 404."""
    email = _email()
    token = await _register_login(client, email)
    await _promote_superuser(session_factory, email)

    missing = await client.get(f"{ADMIN}/roles/{uuid.uuid4()}", headers=_auth_header(token))
    assert missing.status_code == 404


async def test_assign_permission_to_role_and_detach(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """A permission can be attached to and detached from a role."""
    email = _email()
    token = await _register_login(client, email)
    await _promote_superuser(session_factory, email)
    headers = _auth_header(token)

    perm = await client.post(
        f"{ADMIN}/permissions",
        json={"resource": f"res-{uuid.uuid4().hex[:8]}", "action": "read"},
        headers=headers,
    )
    perm_id = perm.json()["id"]
    role = await client.post(
        f"{ADMIN}/roles", json={"name": f"role-{uuid.uuid4().hex[:8]}"}, headers=headers
    )
    role_id = role.json()["id"]

    attached = await client.post(
        f"{ADMIN}/roles/{role_id}/permissions", json={"permission_id": perm_id}, headers=headers
    )
    assert attached.status_code == 200
    assert any(item["id"] == perm_id for item in attached.json()["permissions"])

    detached = await client.delete(
        f"{ADMIN}/roles/{role_id}/permissions/{perm_id}", headers=headers
    )
    assert detached.status_code == 200
    assert all(item["id"] != perm_id for item in detached.json()["permissions"])


async def test_assign_role_to_user_and_detach(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """A role can be assigned to and removed from a user."""
    admin_email = _email()
    token = await _register_login(client, admin_email)
    await _promote_superuser(session_factory, admin_email)
    headers = _auth_header(token)

    target_email = _email()
    await _register_login(client, target_email)
    target_id = await _user_id(session_factory, target_email)

    role = await client.post(
        f"{ADMIN}/roles", json={"name": f"role-{uuid.uuid4().hex[:8]}"}, headers=headers
    )
    role_id = role.json()["id"]

    attached = await client.post(
        f"{ADMIN}/users/{target_id}/roles", json={"role_id": role_id}, headers=headers
    )
    assert attached.status_code == 200
    assert any(item["id"] == role_id for item in attached.json())

    detached = await client.delete(f"{ADMIN}/users/{target_id}/roles/{role_id}", headers=headers)
    assert detached.status_code == 200
    assert all(item["id"] != role_id for item in detached.json())


async def test_granting_rbac_manage_enables_admin_access(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """A non-superuser granted rbac:manage gains admin access; removal revokes it."""
    admin_email = _email()
    su_token = await _register_login(client, admin_email)
    await _promote_superuser(session_factory, admin_email)
    headers = _auth_header(su_token)

    created = await client.post(
        f"{ADMIN}/permissions", json={"resource": "rbac", "action": "manage"}, headers=headers
    )
    if created.status_code == 201:
        perm_id = created.json()["id"]
    else:
        listing = await client.get(f"{ADMIN}/permissions", headers=headers)
        perm_id = next(
            item["id"]
            for item in listing.json()
            if item["resource"] == "rbac" and item["action"] == "manage"
        )

    role = await client.post(
        f"{ADMIN}/roles", json={"name": f"admins-{uuid.uuid4().hex[:8]}"}, headers=headers
    )
    role_id = role.json()["id"]
    await client.post(
        f"{ADMIN}/roles/{role_id}/permissions", json={"permission_id": perm_id}, headers=headers
    )

    user_email = _email()
    user_token = await _register_login(client, user_email)
    user_headers = _auth_header(user_token)
    assert (await client.get(f"{ADMIN}/roles", headers=user_headers)).status_code == 403

    user_id = await _user_id(session_factory, user_email)
    await client.post(f"{ADMIN}/users/{user_id}/roles", json={"role_id": role_id}, headers=headers)
    assert (await client.get(f"{ADMIN}/roles", headers=user_headers)).status_code == 200

    await client.delete(f"{ADMIN}/users/{user_id}/roles/{role_id}", headers=headers)
    assert (await client.get(f"{ADMIN}/roles", headers=user_headers)).status_code == 403


async def test_attach_permission_to_missing_role_404(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Attaching a permission to a non-existent role returns 404."""
    email = _email()
    token = await _register_login(client, email)
    await _promote_superuser(session_factory, email)
    response = await client.post(
        f"{ADMIN}/roles/{uuid.uuid4()}/permissions",
        json={"permission_id": str(uuid.uuid4())},
        headers=_auth_header(token),
    )
    assert response.status_code == 404
