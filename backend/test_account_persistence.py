import sys
import requests
import json
import uuid
import time
import os

BASE_URL = "http://127.0.0.1:8000"

def test_complete_persistence_flow():
    print("==================================================")
    print("STARTING COMPLETE ACCOUNT DATA PERSISTENCE TEST")
    print("==================================================")

    # 1. Register User A
    rand_suffix = str(uuid.uuid4())[:6]
    user_a_email = f"user_a_{rand_suffix}@student.edu"
    user_a_pw = "Password123!"

    print(f"\n[STEP 1] Registering User A: {user_a_email}")
    res = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": "User A Initial",
        "email": user_a_email,
        "password": user_a_pw,
        "confirmPassword": user_a_pw
    })
    assert res.status_code == 200, f"Register failed: {res.text}"
    data_a = res.json()
    token_a = data_a.get("token") or data_a.get("access_token")
    assert token_a, "No token returned for User A"
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Check initial data for User A: should not be onboarded yet
    res = requests.get(f"{BASE_URL}/api/data", headers=headers_a)
    assert res.status_code == 200, f"Initial GET /api/data failed: {res.text}"
    init_data_a = res.json()
    print(f"User A initial onboarded status: {init_data_a.get('user', {}).get('onboarded')}")

    # 3. User A Completes Onboarding / Profile Save
    print("\n[STEP 2] User A saves Onboarding details...")
    onboarding_payload = {
        "user": {
            "name": "Varun",
            "college": "My University",
            "course": "B.Tech AI",
            "onboarded": True
        },
        "routine": {
            "wakeTime": "06:30",
            "sleepTime": "23:30",
            "collegeStart": "08:30",
            "collegeEnd": "15:30",
            "studyHours": 4.0,
            "breakPreference": "15 mins per 45 mins",
            "preferredSubjects": ["Deep Learning", "Knowledge Representation"]
        },
        "subjects": [
            {
                "name": "Deep Learning",
                "teacher": "Prof. Smith",
                "credits": 4,
                "progress": 75.0
            }
        ]
    }
    res = requests.post(f"{BASE_URL}/api/data", json=onboarding_payload, headers=headers_a)
    assert res.status_code == 200, f"POST /api/data failed: {res.text}"
    saved_data = res.json()
    assert saved_data.get("user", {}).get("name") == "Varun", f"Name not updated: {saved_data}"
    assert saved_data.get("user", {}).get("college") == "My University", f"College not updated: {saved_data}"
    assert saved_data.get("user", {}).get("course") == "B.Tech AI", f"Course not updated: {saved_data}"
    assert saved_data.get("user", {}).get("onboarded") is True, f"Onboarded flag not true: {saved_data}"
    print("User A Onboarding successfully saved to backend!")

    # 4. User A Adds 1 Task
    print("\n[STEP 3] User A adds 1 task...")
    res = requests.post(f"{BASE_URL}/api/tasks", json={
        "title": "Complete AI Assignment",
        "description": "Lab report and code",
        "priority": "HIGH",
        "category": "ACADEMIC",
        "deadline": "2026-10-15T23:59:00"
    }, headers=headers_a)
    assert res.status_code == 200, f"Add task failed: {res.text}"
    task_res = res.json()
    task_id = task_res.get("id") or (task_res.get("task") or {}).get("id")
    print(f"Task created with ID: {task_id}")

    # 5. User A Adds 1 Goal
    print("\n[STEP 4] User A adds 1 goal...")
    res = requests.post(f"{BASE_URL}/api/goals", json={
        "title": "Maintain 9.5 GPA",
        "description": "Academic excellence goal",
        "category": "ACADEMIC",
        "progress": 60,
        "deadline": "2026-12-31"
    }, headers=headers_a)
    assert res.status_code == 200, f"Add goal failed: {res.text}"
    goal_res = res.json()
    goal_id = goal_res.get("id") or (goal_res.get("goal") or {}).get("id")
    print(f"Goal created with ID: {goal_id}")

    # 6. User A Adds 1 Calendar Event
    print("\n[STEP 5] User A adds 1 calendar event...")
    res = requests.post(f"{BASE_URL}/api/events", json={
        "title": "AI Lecture",
        "date": "2026-10-10",
        "startTime": "10:00",
        "endTime": "11:30",
        "type": "class",
        "description": "Room 304 Lecture Hall"
    }, headers=headers_a)
    assert res.status_code == 200, f"Add event failed: {res.text}"
    event_res = res.json()
    print(f"Event created: {event_res.get('event', {}).get('title')}")

    # 7. User A Adds 1 Academic Subject
    print("\n[STEP 6] User A adds 1 academic subject...")
    res = requests.post(f"{BASE_URL}/api/subjects", json={
        "name": "Knowledge Representation",
        "teacher": "Dr. Davis",
        "credits": 3,
        "progress": 80.0
    }, headers=headers_a)
    assert res.status_code == 200, f"Add subject failed: {res.text}"
    sub_res = res.json()
    print(f"Subject created: {sub_res.get('subject', {}).get('name')}")

    # 8. User A Uploads 1 Document
    print("\n[STEP 7] User A uploads 1 document...")
    sample_doc_content = b"LifeOS Lecture Notes on Artificial Intelligence and State Persistence."
    res = requests.post(
        f"{BASE_URL}/api/documents/upload",
        files={"file": ("AI_Notes_Varun.txt", sample_doc_content, "text/plain")},
        headers=headers_a
    )
    assert res.status_code == 200, f"Upload document failed: {res.text}"
    doc_res = res.json()
    print(f"Document uploaded: {doc_res.get('filename') or doc_res.get('document', {}).get('filename')}")

    # 9. SIMULATE BROWSER RELOAD FOR USER A
    print("\n[STEP 8] Simulating Browser Page Reload for User A...")
    # App startup makes GET /api/auth/me to restore session
    res = requests.get(f"{BASE_URL}/api/auth/me", headers=headers_a)
    assert res.status_code == 200, f"Session restore failed: {res.text}"
    me_a = res.json()
    print(f"Restored auth session for: {me_a.get('name') or me_a.get('user', {}).get('name')}")

    # AppContext makes GET /api/data to load all persistent state
    res = requests.get(f"{BASE_URL}/api/data", headers=headers_a)
    assert res.status_code == 200, f"Fetch data on reload failed: {res.text}"
    reloaded_data_a = res.json()

    print("\n--- VERIFYING USER A RELOADED DATA ---")
    u_a = reloaded_data_a.get("user", {})
    print(f"User Name: {u_a.get('name')} (Expected: Varun)")
    print(f"College: {u_a.get('college')} (Expected: My University)")
    print(f"Course: {u_a.get('course')} (Expected: B.Tech AI)")
    print(f"Onboarded: {u_a.get('onboarded')} (Expected: True)")
    assert u_a.get("name") == "Varun"
    assert u_a.get("college") == "My University"
    assert u_a.get("course") == "B.Tech AI"
    assert u_a.get("onboarded") is True, "CRITICAL: Onboarded must be True on reload!"

    # Verify Task
    task_titles = [t.get("title") for t in reloaded_data_a.get("tasks", [])]
    print(f"Tasks: {task_titles}")
    assert "Complete AI Assignment" in task_titles, "Task not persisted on reload!"

    # Verify Goal
    goal_titles = [g.get("title") for g in reloaded_data_a.get("goals", [])]
    print(f"Goals: {goal_titles}")
    assert "Maintain 9.5 GPA" in goal_titles, "Goal not persisted on reload!"

    # Verify Calendar Event
    event_titles = [e.get("title") for e in reloaded_data_a.get("events", [])]
    print(f"Events: {event_titles}")
    assert "AI Lecture" in event_titles, "Calendar event not persisted on reload!"

    # Verify Subject
    subject_names = [s.get("name") for s in reloaded_data_a.get("subjects", [])]
    print(f"Subjects: {subject_names}")
    assert "Knowledge Representation" in subject_names or "Deep Learning" in subject_names, "Subject not persisted!"

    # Verify Document
    doc_names = [d.get("name") or d.get("filename") for d in reloaded_data_a.get("documents", [])]
    print(f"Documents: {doc_names}")
    assert any("AI_Notes_Varun" in str(d) for d in doc_names), "Document not persisted on reload!"

    print(">>> PASS: All User A data persisted permanently across reload!")

    # 10. MULTI-USER ISOLATION: Register User B
    print("\n[STEP 9] Registering User B to verify complete account data isolation...")
    user_b_email = f"user_b_{rand_suffix}@student.edu"
    user_b_pw = "Password123!"
    res = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": "User B",
        "email": user_b_email,
        "password": user_b_pw,
        "confirmPassword": user_b_pw
    })
    assert res.status_code == 200, f"Register User B failed: {res.text}"
    token_b = res.json().get("token") or res.json().get("access_token")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Fetch User B data
    res = requests.get(f"{BASE_URL}/api/data", headers=headers_b)
    assert res.status_code == 200, f"User B GET /api/data failed: {res.text}"
    data_b = res.json()

    print("\n--- VERIFYING USER B DATA ISOLATION ---")
    u_b = data_b.get("user", {})
    print(f"User B Name: {u_b.get('name')}")
    print(f"User B College: '{u_b.get('college')}' (Must NOT be User A's 'My University')")
    print(f"User B Tasks count: {len(data_b.get('tasks', []))} (Must be 0)")
    print(f"User B Goals count: {len(data_b.get('goals', []))} (Must be 0)")
    print(f"User B Events count: {len(data_b.get('events', []))} (Must be 0)")
    print(f"User B Subjects count: {len(data_b.get('subjects', []))} (Must be 0)")
    print(f"User B Documents count: {len(data_b.get('documents', []))} (Must be 0)")

    # Assertions for complete isolation
    assert u_b.get("college") != "My University", "LEAK: User B sees User A's university!"
    assert len(data_b.get("tasks", [])) == 0, "LEAK: User B sees User A's tasks!"
    assert len(data_b.get("goals", [])) == 0, "LEAK: User B sees User A's goals!"
    assert len(data_b.get("events", [])) == 0, "LEAK: User B sees User A's calendar events!"
    assert len(data_b.get("subjects", [])) == 0, "LEAK: User B sees User A's subjects!"
    assert len(data_b.get("documents", [])) == 0, "LEAK: User B sees User A's documents!"
    print(">>> PASS: User B has a clean, isolated account with 0 data from User A!")

    # 11. Re-check User A to ensure User A's data was completely untouched
    res = requests.get(f"{BASE_URL}/api/data", headers=headers_a)
    assert res.status_code == 200
    final_data_a = res.json()
    assert final_data_a.get("user", {}).get("name") == "Varun"
    assert len(final_data_a.get("tasks", [])) >= 1
    assert len(final_data_a.get("goals", [])) >= 1
    assert len(final_data_a.get("events", [])) >= 1
    assert len(final_data_a.get("documents", [])) >= 1
    print(">>> PASS: User A's data remains intact and unchanged after User B logged in!")

    print("\n==================================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    test_complete_persistence_flow()
