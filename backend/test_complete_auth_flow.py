import os
import sys
import uuid

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_flow():
    # 1. Health check
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"

    uid = str(uuid.uuid4())[:6]
    email = f"user_{uid}@lifeos.io"
    password = "TestPassword123!"

    # 2. Register
    reg = client.post("/api/auth/register", json={
        "name": f"User {uid}",
        "email": email,
        "password": password,
        "confirmPassword": password
    })
    assert reg.status_code == 200, f"Register failed: {reg.text}"
    reg_data = reg.json()
    assert "token" in reg_data
    token = reg_data["token"]
    user = reg_data["user"]
    assert user["email"] == email

    # 3. GET /api/auth/me with Bearer token
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, f"Me check failed: {me.text}"
    assert me.json()["user"]["email"] == email

    # 4. Save some user data (e.g. task)
    task_res = client.post("/api/tasks", json={
        "title": f"Study Task for {email}",
        "priority": "high"
    }, headers={"Authorization": f"Bearer {token}"})
    assert task_res.status_code == 200

    # 5. Fetch data
    data_res = client.get("/api/data", headers={"Authorization": f"Bearer {token}"})
    assert data_res.status_code == 200
    tasks = data_res.json().get("tasks", [])
    assert any(t["title"] == f"Study Task for {email}" for t in tasks)

    # 6. Logout
    logout_res = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200

    # 7. Check /me with logged out token -> MUST FAIL 401
    me_after = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.status_code == 401

    # 8. Login again with correct credentials
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    new_token = login_res.json()["token"]
    assert new_token != ""

    # 9. Verify user tasks still intact!
    data_res_2 = client.get("/api/data", headers={"Authorization": f"Bearer {new_token}"})
    assert data_res_2.status_code == 200
    tasks_2 = data_res_2.json().get("tasks", [])
    assert any(t["title"] == f"Study Task for {email}" for t in tasks_2), "User data was not preserved!"

    # 10. Login with wrong password -> MUST FAIL 401
    bad_login = client.post("/api/auth/login", json={
        "email": email,
        "password": "WrongPassword123"
    })
    assert bad_login.status_code == 401

    print("ALL LOGIN FLOW TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_login_flow()
