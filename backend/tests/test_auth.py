import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from backend.main import app

BASE = "/auth"
TEST_PASS = "pass1234"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def registered(client):
    email = f"auth_{uuid.uuid4().hex[:8]}@docfalcon.com"
    res = await client.post(f"{BASE}/register", json={
        "email": email,
        "password": TEST_PASS,
        "company_name": "Auth Co",
    })
    data = res.json()
    data["email"] = email
    return data


async def test_register_success(client):
    res = await client.post(f"{BASE}/register", json={
        "email": f"new_{uuid.uuid4().hex[:8]}@docfalcon.com",
        "password": TEST_PASS,
        "company_name": "New Co",
    })
    assert res.status_code == 201
    assert "access_token" in res.json()


async def test_register_duplicate_email(client, registered):
    res = await client.post(f"{BASE}/register", json={
        "email": registered["email"],
        "password": TEST_PASS,
        "company_name": "Auth Co",
    })
    assert res.status_code == 400


async def test_login_success(client, registered):
    res = await client.post(f"{BASE}/login", json={
        "email": registered["email"],
        "password": TEST_PASS,
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


async def test_login_wrong_password(client, registered):
    res = await client.post(f"{BASE}/login", json={
        "email": registered["email"],
        "password": "wrongpass",
    })
    assert res.status_code == 401


async def test_protected_route_with_token(client, registered):
    res = await client.get("/employees", headers={"Authorization": f"Bearer {registered['access_token']}"})
    assert res.status_code == 200


async def test_protected_route_no_token(client):
    res = await client.get("/employees")
    assert res.status_code == 401


async def test_refresh(client, registered):
    login = await client.post(f"{BASE}/login", json={
        "email": registered["email"],
        "password": TEST_PASS,
    })
    assert login.status_code == 200
    res = await client.post(f"{BASE}/refresh")
    assert res.status_code == 200
    assert "access_token" in res.json()