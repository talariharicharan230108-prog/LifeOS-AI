import sys
import os
import uuid

# Ensure backend directory is in path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from fastapi.testclient import TestClient
from app.main import app
from app import storage

client = TestClient(app)

def test_full_auth_and_isolation():
    print("Testing /api/health...")
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("Health OK:", r.json())

    # Generate unique emails for test run
    uid_a = str(uuid.uuid4())[:6]
    uid_b = str(uuid.uuid4())[:6]
    email_a = f"user_a_{uid_a}@test.com"
    email_b = f"user_b_{uid_b}@test.com"

    # ==========================================
    # 1. Register User A
    # ==========================================
    print(f"\n--- Registering User A ({email_a}) ---")
    reg_a = client.post("/api/auth/register", json={
        "name": "User A",
        "email": email_a,
        "password": "Password123",
        "confirmPassword": "Password123"
    })
    assert reg_a.status_code == 200, f"Register A failed: {reg_a.text}"
    data_a = reg_a.json()
    token_a = data_a["token"]
    user_a = data_a["user"]
    id_a = user_a["id"]
    print("User A registered with ID:", id_a)

    # User A creates items across all 5 domains:
    # 1. tasks
    t_a = client.post("/api/tasks", json={
        "title": "Task A for User A",
        "priority": "high",
        "deadline": "2026-10-10"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert t_a.status_code == 200
    assert t_a.json()["task"]["user_id"] == id_a

    # 2. calendar (events)
    e_a = client.post("/api/events", json={
        "title": "Study Event A",
        "date": "2026-10-10",
        "startTime": "18:00",
        "endTime": "19:00"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert e_a.status_code == 200
    assert e_a.json()["event"]["user_id"] == id_a

    # 3. goals
    g_a = client.post("/api/goals", json={
        "title": "Goal A for User A",
        "deadline": "2026-11-01"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert g_a.status_code == 200
    assert g_a.json()["goal"]["user_id"] == id_a

    # 4. academic (subjects)
    s_a = client.post("/api/subjects", json={
        "name": "Subject A for User A",
        "credits": 4,
        "examDate": "2026-10-20"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert s_a.status_code == 200
    assert s_a.json()["subject"]["user_id"] == id_a

    # 5. documents
    dummy_file_path = os.path.join(backend_dir, "test_doc_a.txt")
    with open(dummy_file_path, "w", encoding="utf-8") as f:
        f.write("User A document content.")
    with open(dummy_file_path, "rb") as f:
        d_a = client.post("/api/documents/upload", files={"file": ("test_doc_a.txt", f, "text/plain")}, headers={"Authorization": f"Bearer {token_a}"})
    if os.path.exists(dummy_file_path):
        os.remove(dummy_file_path)
    assert d_a.status_code == 200
    assert d_a.json()["document"]["user_id"] == id_a

    # ==========================================
    # 2. Register User B
    # ==========================================
    print(f"\n--- Registering User B ({email_b}) ---")
    reg_b = client.post("/api/auth/register", json={
        "name": "User B",
        "email": email_b,
        "password": "Password456",
        "confirmPassword": "Password456"
    })
    assert reg_b.status_code == 200, f"Register B failed: {reg_b.text}"
    data_b = reg_b.json()
    token_b = data_b["token"]
    user_b = data_b["user"]
    id_b = user_b["id"]
    print("User B registered with ID:", id_b)

    # ==========================================
    # 3. VERIFY STRICT ISOLATION FOR USER B:
    # user_id = B -> all 5 domains MUST be empty for B (no leak of User A data)
    # ==========================================
    # tasks where user_id = B
    tasks_b = client.get("/api/tasks", headers={"Authorization": f"Bearer {token_b}"}).json()["tasks"]
    assert len(tasks_b) == 0, f"Tasks isolation failure! Found: {tasks_b}"

    # calendar where user_id = B
    events_b = client.get("/api/events", headers={"Authorization": f"Bearer {token_b}"}).json()["events"]
    assert len(events_b) == 0, f"Calendar isolation failure! Found: {events_b}"

    # goals where user_id = B
    goals_b = client.get("/api/goals", headers={"Authorization": f"Bearer {token_b}"}).json()["goals"]
    assert len(goals_b) == 0, f"Goals isolation failure! Found: {goals_b}"

    # academic where user_id = B
    academic_b = client.get("/api/academic", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert len(academic_b["subjects"]) == 0, f"Academic isolation failure! Found: {academic_b}"

    # documents where user_id = B
    docs_b = client.get("/api/documents", headers={"Authorization": f"Bearer {token_b}"}).json()["documents"]
    assert len(docs_b) == 0, f"Documents isolation failure! Found: {docs_b}"

    print("[PASS] User B initially sees 0 items across all 5 domains (zero data leak from User A).")

    # ==========================================
    # 4. User B populates their own items (user_id = B)
    # ==========================================
    # tasks where user_id = B
    client.post("/api/tasks", json={"title": "Task B for User B", "priority": "low"}, headers={"Authorization": f"Bearer {token_b}"})
    # calendar where user_id = B
    client.post("/api/events", json={"title": "Event B", "date": "2026-10-15"}, headers={"Authorization": f"Bearer {token_b}"})
    # goals where user_id = B
    client.post("/api/goals", json={"title": "Goal B"}, headers={"Authorization": f"Bearer {token_b}"})
    # academic where user_id = B
    client.post("/api/subjects", json={"name": "Subject B", "credits": 3}, headers={"Authorization": f"Bearer {token_b}"})
    # documents where user_id = B
    dummy_b_path = os.path.join(backend_dir, "test_doc_b.txt")
    with open(dummy_b_path, "w", encoding="utf-8") as f:
        f.write("User B document content.")
    with open(dummy_b_path, "rb") as f:
        client.post("/api/documents/upload", files={"file": ("test_doc_b.txt", f, "text/plain")}, headers={"Authorization": f"Bearer {token_b}"})
    if os.path.exists(dummy_b_path):
        os.remove(dummy_b_path)

    # ==========================================
    # 5. VERIFY USER B ITEMS STRICTLY HAVE user_id = B
    # ==========================================
    tasks_b_new = client.get("/api/tasks", headers={"Authorization": f"Bearer {token_b}"}).json()["tasks"]
    assert len(tasks_b_new) == 1
    assert tasks_b_new[0]["user_id"] == id_b
    assert tasks_b_new[0]["title"] == "Task B for User B"

    events_b_new = client.get("/api/events", headers={"Authorization": f"Bearer {token_b}"}).json()["events"]
    assert len(events_b_new) == 1
    assert events_b_new[0]["user_id"] == id_b

    goals_b_new = client.get("/api/goals", headers={"Authorization": f"Bearer {token_b}"}).json()["goals"]
    assert len(goals_b_new) == 1
    assert goals_b_new[0]["user_id"] == id_b

    academic_b_new = client.get("/api/academic", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert len(academic_b_new["subjects"]) == 1
    assert academic_b_new["subjects"][0]["user_id"] == id_b

    docs_b_new = client.get("/api/documents", headers={"Authorization": f"Bearer {token_b}"}).json()["documents"]
    assert len(docs_b_new) == 1
    assert docs_b_new[0]["user_id"] == id_b

    print("[PASS] User B queries strictly return only items where user_id = B.")

    # ==========================================
    # 6. VERIFY USER A ITEMS UNAFFECTED AND UNTAINTED
    # ==========================================
    tasks_a_check = client.get("/api/tasks", headers={"Authorization": f"Bearer {token_a}"}).json()["tasks"]
    assert len(tasks_a_check) == 1
    assert tasks_a_check[0]["user_id"] == id_a
    assert tasks_a_check[0]["title"] == "Task A for User A"

    events_a_check = client.get("/api/events", headers={"Authorization": f"Bearer {token_a}"}).json()["events"]
    assert len(events_a_check) == 1
    assert events_a_check[0]["user_id"] == id_a

    goals_a_check = client.get("/api/goals", headers={"Authorization": f"Bearer {token_a}"}).json()["goals"]
    assert len(goals_a_check) == 1
    assert goals_a_check[0]["user_id"] == id_a

    academic_a_check = client.get("/api/academic", headers={"Authorization": f"Bearer {token_a}"}).json()
    assert len(academic_a_check["subjects"]) == 1
    assert academic_a_check["subjects"][0]["user_id"] == id_a

    docs_a_check = client.get("/api/documents", headers={"Authorization": f"Bearer {token_a}"}).json()["documents"]
    assert len(docs_a_check) == 1
    assert docs_a_check[0]["user_id"] == id_a

    print("[PASS] User A queries strictly return only items where user_id = A.")

    # ==========================================
    # 7. AI AGENT ISOLATION FOR USER B
    # ==========================================
    # User B asks agent to schedule an event
    agent_res = client.post(
        "/api/agent",
        json={"message": "Schedule DBMS preparation tomorrow from 6 PM to 7 PM"},
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert agent_res.status_code == 200
    # Event should be added to User B's calendar, NOT User A's
    events_b_after = client.get("/api/events", headers={"Authorization": f"Bearer {token_b}"}).json()["events"]
    assert any("dbms" in e["title"].lower() for e in events_b_after)
    events_a_after = client.get("/api/events", headers={"Authorization": f"Bearer {token_a}"}).json()["events"]
    assert not any("dbms" in e["title"].lower() for e in events_a_after), "AI Agent scheduled into User A instead of User B!"

    print("[PASS] AI Agent operates with strict user_id = B isolation.")

    # Password change and logout verification for User A
    cp_res = client.post("/api/auth/change-password", json={
        "currentPassword": "Password123",
        "newPassword": "NewPassword123",
        "confirmNewPassword": "NewPassword123"
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert cp_res.status_code == 200

    client.post("/api/auth/logout", headers={"Authorization": f"Bearer {token_a}"})
    login_old = client.post("/api/auth/login", json={"email": email_a, "password": "Password123"})
    assert login_old.status_code == 401

    login_new = client.post("/api/auth/login", json={"email": email_a, "password": "NewPassword123"})
    assert login_new.status_code == 200

    print("\nALL MULTI-USER ISOLATION TESTS PASSED (user_id = B strictly enforced across tasks, calendar, goals, academic, documents, and agent)!")

if __name__ == "__main__":
    test_full_auth_and_isolation()
