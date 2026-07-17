from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.seed import DEFAULT_PASSWORD, seed

AUTH = "/api/v1/auth"
ADMIN = "/api/v1/admin"
DOCUMENTS = "/api/v1/documents"
REPORTS = "/api/v1/reports"


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _login(client: AsyncClient, email: str) -> str:
    response = await client.post(
        f"{AUTH}/login", json={"email": email, "password": DEFAULT_PASSWORD}
    )
    return str(response.json()["access_token"])


async def test_seed_is_idempotent(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Running the seed twice does not raise."""
    async with session_factory() as session:
        await seed(session)
    async with session_factory() as session:
        await seed(session)


async def test_seeded_admin_has_full_access(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """The seeded admin can reach the admin API and business resources."""
    async with session_factory() as session:
        await seed(session)

    token = await _login(client, "admin@example.com")
    assert (await client.get(f"{ADMIN}/roles", headers=_auth_header(token))).status_code == 200
    assert (await client.get(DOCUMENTS, headers=_auth_header(token))).status_code == 200


async def test_seeded_user_has_scoped_access(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """The seeded user can read documents but not manage RBAC or read reports."""
    async with session_factory() as session:
        await seed(session)

    token = await _login(client, "user@example.com")
    headers = _auth_header(token)
    assert (await client.get(DOCUMENTS, headers=headers)).status_code == 200
    assert (await client.get(f"{ADMIN}/roles", headers=headers)).status_code == 403
    assert (await client.get(REPORTS, headers=headers)).status_code == 403
