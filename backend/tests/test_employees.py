import pytest
from httpx import ASGITransport, AsyncClient
from main import app


@pytest.mark.asyncio
async def test_list_no_filter_returns_all():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/employees")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_valid_filter():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/employees", params={"status": "expiring_30d"})
    assert r.status_code == 200
    assert all(e["status"] == "expiring_30d" for e in r.json())


@pytest.mark.asyncio
async def test_list_invalid_status_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/employees", params={"status": "bogus"})
    assert r.status_code == 400
    assert "status must be one of" in r.json()["detail"]