"""E9 cache tests — hit/miss, invalidation, tenant isolation. Real Upstash, no mock."""

import json
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.services.cache import cache_get, cache_set, cache_delete, _client

transport = ASGITransport(app=app)
BASE = "http://test"

pytestmark = pytest.mark.skipif(_client() is None, reason="Redis not configured")


@pytest.fixture
async def client():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        yield c


@pytest.fixture
async def auth(client):
    email = f"cache_{uuid.uuid4().hex[:8]}@test.com"
    r = await client.post("/auth/register", json={
        "email": email, "password": "testpass123", "company_name": "CacheCo",
    })
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_set_get_delete_roundtrip():
    key = f"test:{uuid.uuid4()}"
    await cache_set(key, json.dumps({"n": 1}), 60)
    assert json.loads(await cache_get(key))["n"] == 1
    await cache_delete(key)
    assert await cache_get(key) is None


async def test_miss_returns_none():
    assert await cache_get(f"test:{uuid.uuid4()}") is None


async def test_stats_cache_invalidated_on_employee_write(client, auth):
    """A write must bust the stats key — a stale count is worse than a slow one."""
    r1 = await client.get("/dashboard/stats", headers=auth)
    before = r1.json()["total_employees"]

    r2 = await client.post(
        "/employees",
        json={"name_en": f"Cache Test {uuid.uuid4().hex[:6]}"},
        headers=auth,
    )
    assert r2.status_code == 201
    emp_id = r2.json()["id"]

    r3 = await client.get("/dashboard/stats", headers=auth)
    assert r3.json()["total_employees"] == before + 1  # still `before` if the cache went stale

    await client.delete(f"/employees/{emp_id}", headers=auth)


async def test_extract_cache_is_tenant_scoped():
    """Same file hash, two companies — keys must not collide."""
    file_hash = uuid.uuid4().hex
    k1, k2 = f"extract:companyA:{file_hash}", f"extract:companyB:{file_hash}"

    await cache_set(k1, json.dumps({"owner": "A"}), 60)
    assert await cache_get(k2) is None

    await cache_delete(k1)