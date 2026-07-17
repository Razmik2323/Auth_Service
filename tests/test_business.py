import uuid

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User

BASE = "/api/v1"
AUTH = f"{BASE}/auth"
ADMIN = f"{BASE}/admin"
DOCUMENTS = f"{BASE}/documents"
REPORTS = f"{BASE}/reports"
PASSWORD = "Sup3r-Secret-Pass"


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _register_login(client: AsyncClient, email: str) -> str:
    payload = {
        "first_name": "Test",
        "last_name": "User",
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
        result.scalar_one().is_superuser = True
        await session.commit()


async def _user_id(factory: async_sessionmaker[AsyncSession], email: str) -> str:
    async with factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        return str(result.scalar_one().id)


async def _token_with_permission(
    client: AsyncClient,
    factory: async_sessionmaker[AsyncSession],
    resource: str,
    action: str,
) -> str:
    su_email = _email()
    su_token = await _register_login(client, su_email)
    await _promote_superuser(factory, su_email)
    headers = _auth_header(su_token)

    created = await client.post(
        f"{ADMIN}/permissions",
        json={"resource": resource, "action": action},
        headers=headers,
    )
    if created.status_code == 201:
        perm_id = created.json()["id"]
    else:
        listing = await client.get(f"{ADMIN}/permissions", headers=headers)
        perm_id = next(
            item["id"]
            for item in listing.json()
            if item["resource"] == resource and item["action"] == action
        )

    role = await client.post(
        f"{ADMIN}/roles", json={"name": f"role-{uuid.uuid4().hex[:8]}"}, headers=headers
    )
    role_id = role.json()["id"]
    await client.post(
        f"{ADMIN}/roles/{role_id}/permissions", json={"permission_id": perm_id}, headers=headers
    )

    user_email = _email()
    user_token = await _register_login(client, user_email)
    user_id = await _user_id(factory, user_email)
    await client.post(f"{ADMIN}/users/{user_id}/roles", json={"role_id": role_id}, headers=headers)
    return user_token


async def test_documents_requires_authentication(client: AsyncClient) -> None:
    """Listing documents without a token returns 401."""
    response = await client.get(DOCUMENTS)
    assert response.status_code == 401


async def test_documents_forbidden_without_permission(client: AsyncClient) -> None:
    """A user lacking documents:read gets 403."""
    token = await _register_login(client, _email())
    response = await client.get(DOCUMENTS, headers=_auth_header(token))
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_documents_allowed_with_permission(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """A user with documents:read receives the document list."""
    token = await _token_with_permission(client, session_factory, "documents", "read")
    response = await client.get(DOCUMENTS, headers=_auth_header(token))
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_permission_is_scoped_to_resource(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """documents:read does not grant access to reports."""
    token = await _token_with_permission(client, session_factory, "documents", "read")
    response = await client.get(REPORTS, headers=_auth_header(token))
    assert response.status_code == 403
