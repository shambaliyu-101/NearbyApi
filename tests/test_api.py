import uuid
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unauthorized_access_rejected():
    fake_region_id = uuid.uuid4()
    res1 = client.get("/regions")
    assert res1.status_code in (401, 403)

    res2 = client.get(f"/regions/{fake_region_id}/nearby?x=0&y=0")
    assert res2.status_code in (401, 403)


def test_user_registration_and_login_flow():
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "SuperSecretPassword123!"

    # 1. Register
    reg_res = client.post("/auth/register", json={"email": unique_email, "password": password})
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == unique_email

    # 2. Duplicate registration rejected
    dup_res = client.post("/auth/register", json={"email": unique_email, "password": password})
    assert dup_res.status_code == 400

    # 3. Login
    login_res = client.post("/auth/login", json={"email": unique_email, "password": password})
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens