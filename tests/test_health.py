from httpx import AsyncClient


async def test_health_reports_dependencies(client: AsyncClient) -> None:
    """The health endpoint reports ok status with dependency states."""
    response = await client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["redis"] == "ok"
