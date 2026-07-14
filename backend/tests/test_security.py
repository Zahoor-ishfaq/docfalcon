"""E8 smoke tests — headers, magic bytes, NoSQL injection, enum validation, token rotation."""

import io
import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.core.database import get_db

transport = ASGITransport(app=app)
BASE = "http://test"


async def _register(client) -> str:
    email = f"sec_{uuid.uuid4().hex[:8]}@test.com"
    r = await client.post("/auth/register", json={
        "email": email, "password": "testpass123", "company_name": "SecCo",
    })
    assert r.status_code == 201
    return r.json()["access_token"]


@pytest.fixture
async def client():
    async with AsyncClient(transport=transport, base_url=BASE) as c:
        yield c


@pytest.fixture
async def auth(client):
    token = await _register(client)
    return {"Authorization": f"Bearer {token}"}


async def test_security_headers_present(client):
    r = await client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert "content-security-policy" in r.headers
    assert r.headers["referrer-policy"] == "no-referrer"


async def test_magic_bytes_reject_disguised_file(client, auth):
    # Declared as PNG, actually an ELF binary.
    fake = io.BytesIO(b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 64)
    r = await client.post(
        "/extract?doc_type=iqama",
        files={"file": ("evil.png", fake, "image/png")},
        headers=auth,
    )
    assert r.status_code == 400


async def test_nosql_operator_in_name_rejected(client, auth):
    r = await client.post(
        "/employees",
        json={"name_en": "$ne", "nationality": "$gt"},
        headers=auth,
    )
    assert r.status_code == 422


async def test_unknown_status_filter_rejected(client, auth):
    r = await client.get("/employees?status=DROP_TABLE", headers=auth)
    assert r.status_code == 422


async def test_protected_route_requires_token(client):
    r = await client.get("/employees")
    assert r.status_code == 401


async def test_refresh_token_is_single_use(client):
    email = f"rot_{uuid.uuid4().hex[:8]}@test.com"
    await client.post("/auth/register", json={
        "email": email, "password": "testpass123", "company_name": "RotCo",
    })
    stale = client.cookies.get("refresh_token")

    first = await client.post("/auth/refresh")
    assert first.status_code == 200

    # Replaying the consumed token must fail even though its signature is still valid.
    client.cookies.set("refresh_token", stale)
    replay = await client.post("/auth/refresh")
    assert replay.status_code == 401


async def test_logout_revokes_refresh_token(client):
    email = f"out_{uuid.uuid4().hex[:8]}@test.com"
    await client.post("/auth/register", json={
        "email": email, "password": "testpass123", "company_name": "OutCo",
    })
    await client.post("/auth/logout")
    r = await client.post("/auth/refresh")
    assert r.status_code == 401