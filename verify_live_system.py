import urllib.request
import json
import time

VITE_BASE = "http://127.0.0.1:5173"
BACKEND_BASE = "http://127.0.0.1:8000"

def request(url, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data_bytes = json.dumps(data).encode("utf-8")
    else:
        data_bytes = None

    req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(content)
        except Exception:
            return e.code, {"raw": content}

def run_e2e_verification():
    ts = int(time.time())
    email_a = f"testuser_{ts}@example.com"
    email_b = f"studentb_{ts}@example.com"

    print("=" * 60)
    print("E2E LIVE VERIFICATION VIA VITE PROXY (http://127.0.0.1:5173)")
    print("=" * 60)

    # 1. Verify Frontend is serving index.html
    print("\n[1] Checking Frontend index.html...")
    with urllib.request.urlopen(VITE_BASE) as resp:
        html = resp.read().decode("utf-8")
        assert "LifeOS" in html or "<div id=\"root\">" in html
        print(f"Frontend is online and serving React app (status {resp.status}).")

    # 2. Verify Vite proxy forwards /api to FastAPI backend
    print("\n[2] Checking Vite Proxy to Backend (/api/health)...")
    status, health = request(f"{VITE_BASE}/api/health")
    assert status == 200, f"Health check failed through Vite proxy: {status}, {health}"
    print("Vite proxy is functioning! Health response:", health)

    # 3. Test Registration via Vite proxy
    print(f"\n[3] Testing Registration (User: Test User, Email: {email_a})...")
    status, reg_res = request(f"{VITE_BASE}/api/auth/register", method="POST", data={
        "name": "Test User",
        "email": email_a,
        "password": "Password123",
        "confirmPassword": "Password123"
    })
    print(f"Register status: {status}, response: {reg_res}")
    assert status == 200
    token = reg_res["token"]
    user = reg_res["user"]
    assert user["name"] == "Test User"
    assert user["email"] == email_a
    assert "password" not in user
    assert "password_hash" not in user
    auth_header = {"Authorization": f"Bearer {token}"}

    # 4. Verify new user data starts with 0 dummy items (Requirement Part 7)
    print("\n[4] Verifying clean initial state (0 dummy subjects, 0 tasks, 0 events)...")
    status, user_data = request(f"{VITE_BASE}/api/data", headers=auth_header)
    assert status == 200
    print("Subjects count:", len(user_data.get("subjects", [])))
    print("Tasks count:", len(user_data.get("tasks", [])))
    print("Events count:", len(user_data.get("events", [])))
    print("Goals count:", len(user_data.get("goals", [])))
    print("Documents count:", len(user_data.get("documents", [])))
    assert len(user_data.get("subjects", [])) == 0, "Dummy subjects found!"
    assert len(user_data.get("tasks", [])) == 0, "Dummy tasks found!"
    assert len(user_data.get("events", [])) == 0, "Dummy events found!"

    # 5. Test AI Agent endpoint (Fixing Part 1 - NO 404!)
    print("\n[5] Testing AI Agent Endpoint (POST /api/agent) with 'hello'...")
    status, agent_res = request(f"{VITE_BASE}/api/agent", method="POST", data={"message": "hello"}, headers=auth_header)
    assert status == 200, f"Agent returned status {status}: {agent_res}"
    print("Agent reply:", agent_res.get("response")[:80], "...")
    assert "action" in agent_res
    assert "response" in agent_res
    print(" AI Agent 404 issue is completely resolved!")

    # Test "Show my upcoming deadlines"
    print("\n[6] Testing AI Agent with 'Show my upcoming deadlines'...")
    status, deadlines_res = request(f"{VITE_BASE}/api/agent", method="POST", data={"message": "Show my upcoming deadlines"}, headers=auth_header)
    assert status == 200
    print("Deadlines response:", deadlines_res.get("response"))
    assert deadlines_res.get("action") == "none", "Informational query should not create events!"

    # 6. Test Calendar AI Generation (Fixing Part 2 - NO Failure!)
    print("\n[7] Testing Calendar AI Generation (POST /api/calendar/generate) for '2026-10-03'...")
    status, cal_res = request(f"{VITE_BASE}/api/calendar/generate", method="POST", data={"date": "2026-10-03"}, headers=auth_header)
    assert status == 200, f"Calendar generation returned {status}: {cal_res}"
    print(f"Calendar generate result: status={cal_res.get('status')}, message={cal_res.get('message')}")
    events = cal_res.get("events", [])
    print(f"Generated {len(events)} events strictly on 2026-10-03:")
    for ev in events:
        print(f" - [{ev.get('startTime')}-{ev.get('endTime')}] {ev.get('title')} (Date: {ev.get('date')})")
        assert ev.get("date") == "2026-10-03", f"Date mismatch: event date {ev.get('date')} != requested 2026-10-03"
    print(" Calendar AI Generation is working and strict date rule enforced!")

    # 7. Test AI Status & AI Test (Parts 4 & 5)
    print("\n[8] Testing /api/ai/status and /api/ai/test...")
    status, ai_status = request(f"{VITE_BASE}/api/ai/status")
    assert status == 200
    print("AI Status:", ai_status)
    assert "connected" in ai_status
    assert "api_key" not in ai_status

    status, ai_test = request(f"{VITE_BASE}/api/ai/test", method="POST")
    assert status == 200
    print("AI Test Result:", ai_test)
    assert ai_test.get("message") in ["AI connection successful.", "AI connection failed."]

    # 8. Test Multi-User Data Isolation (Part 8 & 20)
    print("\n[9] Testing Multi-User Data Isolation...")
    # User A adds a task
    status, task_res = request(f"{VITE_BASE}/api/tasks", method="POST", data={"title": "User A Private Task", "priority": "high"}, headers=auth_header)
    assert status == 200

    # Register User B
    status, reg_b = request(f"{VITE_BASE}/api/auth/register", method="POST", data={
        "name": "Student B",
        "email": email_b,
        "password": "Password456",
        "confirmPassword": "Password456"
    })
    assert status == 200
    token_b = reg_b["token"]
    header_b = {"Authorization": f"Bearer {token_b}"}

    # Verify Student B CANNOT see User A's task
    status, b_tasks = request(f"{VITE_BASE}/api/tasks", headers=header_b)
    assert status == 200
    print(f"Student B task count: {len(b_tasks['tasks'])}")
    assert len(b_tasks["tasks"]) == 0, "Data isolation failed! User B saw User A's tasks."

    # Student B adds their own task
    status, _ = request(f"{VITE_BASE}/api/tasks", method="POST", data={"title": "Student B's Task", "priority": "low"}, headers=header_b)
    assert status == 200

    # User A checks their tasks
    status, a_tasks = request(f"{VITE_BASE}/api/tasks", headers=auth_header)
    assert status == 200
    print(f"User A task count: {len(a_tasks['tasks'])}")
    assert len(a_tasks["tasks"]) == 1
    assert a_tasks["tasks"][0]["title"] == "User A Private Task"
    print(" Multi-user data isolation verified!")

    # 9. Test Change Password, Logout, and Relogin (Parts 6 & 19)
    print("\n[10] Testing Change Password and Relogin...")
    status, cp_res = request(f"{VITE_BASE}/api/auth/change-password", method="POST", data={
        "currentPassword": "Password123",
        "newPassword": "NewPassword123",
        "confirmNewPassword": "NewPassword123"
    }, headers=auth_header)
    assert status == 200
    print("Change password result:", cp_res)

    # Logout
    status, _ = request(f"{VITE_BASE}/api/auth/logout", method="POST", headers=auth_header)
    assert status == 200
    print("Logged out successfully.")

    # Login with old password (MUST FAIL)
    status, fail_res = request(f"{VITE_BASE}/api/auth/login", method="POST", data={
        "email": email_a,
        "password": "Password123"
    })
    print(f"Login with old password status: {status} (Expected 401)")
    assert status == 401

    # Login with new password (MUST SUCCEED)
    status, ok_res = request(f"{VITE_BASE}/api/auth/login", method="POST", data={
        "email": email_a,
        "password": "NewPassword123"
    })
    print(f"Login with new password status: {status} (Expected 200)")
    assert status == 200
    assert "token" in ok_res

    print("\n" + "=" * 60)
    print(" ALL 10 E2E SYSTEM TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_e2e_verification()
