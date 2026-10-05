import sys
import requests
import json
import uuid
import time

BASE_URL = "http://127.0.0.1:8000"

def test_full_system():
    print("==================================================")
    print("RUNNING FINAL CLEAN FIX + PERSISTENCE + GEMINI TEST")
    print("==================================================")

    rand_suffix = str(uuid.uuid4())[:6]
    user_a_email = f"student_a_{rand_suffix}@university.edu"
    user_a_pw = "Password123!"

    # 1. Register User A
    print(f"\n[1] Registering User A ({user_a_email})...")
    res = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": "Varun A",
        "email": user_a_email,
        "password": user_a_pw,
        "confirmPassword": user_a_pw
    })
    assert res.status_code == 200, f"Register User A failed: {res.text}"
    token_a = res.json().get("access_token") or res.json().get("token")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Verify User A starts with clean empty state
    res = requests.get(f"{BASE_URL}/api/data", headers=headers_a)
    assert res.status_code == 200
    data_a_init = res.json()
    assert data_a_init.get("user", {}).get("onboarded") is False, "New account must start with onboarded = False"
    assert len(data_a_init.get("tasks", [])) == 0, "New account must have 0 tasks"
    assert len(data_a_init.get("events", [])) == 0, "New account must have 0 events"
    assert len(data_a_init.get("goals", [])) == 0, "New account must have 0 goals"
    assert len(data_a_init.get("subjects", [])) == 0, "New account must have 0 subjects"
    assert len(data_a_init.get("holidays", [])) == 0, "New account must have 0 holidays"
    print(">>> PASS: New user starts with clean empty workspace!")

    # 2. User A sets Profile & Routine
    print("\n[2] Setting User A Profile & Routine...")
    res = requests.post(f"{BASE_URL}/api/data", json={
        "user": {
            "name": "Varun Kumar",
            "college": "SRM University",
            "course": "B.Tech AI & Data Science",
            "onboarded": True
        },
        "routine": {
            "wakeTime": "06:30",
            "sleepTime": "23:30",
            "collegeStart": "09:00",
            "collegeEnd": "16:00",
            "studyHours": 3.5,
            "breakPreference": "15 mins per 45 mins",
            "preferredSubjects": ["Deep Learning", "Knowledge Engineering"]
        },
        "subjects": [
            {
                "name": "Deep Learning",
                "teacher": "Dr. Naveen",
                "credits": 4,
                "progress": 80.0
            }
        ]
    }, headers=headers_a)
    assert res.status_code == 200

    # 3. User A adds Task, Goal, Calendar Event, Academic Subject, Holiday
    print("\n[3] User A adds Task, Goal, Event, Subject, and Holiday...")
    # Task
    t_res = requests.post(f"{BASE_URL}/api/tasks", json={
        "title": "Build AI CSP Agent",
        "description": "Project implementation",
        "priority": "HIGH",
        "category": "ACADEMIC",
        "deadline": "2026-10-12T23:59:00"
    }, headers=headers_a)
    assert t_res.status_code == 200, f"Task creation failed: {t_res.text}"

    # Goal
    g_res = requests.post(f"{BASE_URL}/api/goals", json={
        "title": "Publish AI Paper",
        "category": "ACADEMIC",
        "progress": 40,
        "deadline": "2026-12-15"
    }, headers=headers_a)
    assert g_res.status_code == 200, f"Goal creation failed: {g_res.text}"

    # Event
    e_res = requests.post(f"{BASE_URL}/api/events", json={
        "title": "Lab Demonstration",
        "date": "2026-10-06",
        "startTime": "14:00",
        "endTime": "15:30",
        "type": "class",
        "description": "Final Lab Evaluation"
    }, headers=headers_a)
    assert e_res.status_code == 200, f"Event creation failed: {e_res.text}"

    # Subject
    s_res = requests.post(f"{BASE_URL}/api/subjects", json={
        "name": "Knowledge Engineering",
        "teacher": "Prof. Rao",
        "credits": 3,
        "progress": 75.0
    }, headers=headers_a)
    assert s_res.status_code == 200, f"Subject creation failed: {s_res.text}"

    # Holiday
    h_res = requests.post(f"{BASE_URL}/api/holidays", json={
        "name": "Diwali Festival",
        "date": "2026-11-01",
        "description": "Campus closed for Diwali"
    }, headers=headers_a)
    assert h_res.status_code == 200, f"Holiday creation failed: {h_res.text}"
    print("All entities created successfully for User A!")

    # 4. TEST GEMINI INTEGRATIONS
    print("\n[4] Testing Gemini Integrations...")

    # A. AI Agent: 'What should I do today?'
    print("  Testing A: AI Agent ('What should I do today?')...")
    agent_res = requests.post(f"{BASE_URL}/api/agent", json={
        "message": "What should I do today?"
    }, headers=headers_a)
    assert agent_res.status_code == 200, f"AI Agent error: {agent_res.text}"
    agent_data = agent_res.json()
    resp_text = agent_data.get("response") or agent_data.get("response_text") or ""
    print(f"  AI Agent response length: {len(resp_text)} chars")
    assert len(resp_text) > 0, "AI Agent returned empty response"

    # B. Calendar: 'Generate my schedule for today' (via /api/calendar/generate)
    print("  Testing B: Calendar AI Generation ('Generate schedule for today')...")
    cal_gen_res = requests.post(f"{BASE_URL}/api/calendar/generate", json={
        "date": "2026-10-04"
    }, headers=headers_a)
    assert cal_gen_res.status_code == 200, f"Calendar generation error: {cal_gen_res.text}"
    cal_gen_data = cal_gen_res.json()
    print(f"  Calendar generation message: {cal_gen_data.get('message')}")
    print(f"  Calendar events generated: {len(cal_gen_data.get('events', []))}")
    assert len(cal_gen_data.get("events", [])) > 0, "Calendar AI generation returned 0 events"

    # C. Dashboard: 'Generate AI Schedule for Today' (calls calendar/generate for today)
    print("  Testing C: Dashboard AI Schedule Generation...")
    dash_gen_res = requests.post(f"{BASE_URL}/api/calendar/generate", json={
        "date": "2026-10-04"
    }, headers=headers_a)
    assert dash_gen_res.status_code == 200, f"Dashboard generation error: {dash_gen_res.text}"
    print(">>> PASS: All 3 Gemini features (Agent, Calendar, Dashboard) working 100%!")

    # 5. SIMULATE LOGOUT & RE-LOGIN FOR USER A
    print("\n[5] Simulating Logout -> Re-login for User A...")
    # Logout
    requests.post(f"{BASE_URL}/api/auth/logout", headers=headers_a)

    # Login
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": user_a_email,
        "password": user_a_pw
    })
    assert login_res.status_code == 200
    token_a_new = login_res.json().get("access_token") or login_res.json().get("token")
    headers_a_new = {"Authorization": f"Bearer {token_a_new}"}

    # Fetch User A data after re-login
    res = requests.get(f"{BASE_URL}/api/data", headers=headers_a_new)
    assert res.status_code == 200
    reloaded_a = res.json()

    # Verify everything persisted
    assert reloaded_a.get("user", {}).get("name") == "Varun Kumar"
    assert reloaded_a.get("user", {}).get("college") == "SRM University"
    assert reloaded_a.get("user", {}).get("course") == "B.Tech AI & Data Science"
    assert reloaded_a.get("user", {}).get("onboarded") is True

    # Verify tasks, goals, events, subjects, holidays
    t_titles = [t["title"] for t in reloaded_a.get("tasks", [])]
    g_titles = [g["title"] for g in reloaded_a.get("goals", [])]
    e_titles = [e["title"] for e in reloaded_a.get("events", [])]
    s_names = [s["name"] for s in reloaded_a.get("subjects", [])]
    h_names = [h.get("name") or h.get("title") for h in reloaded_a.get("holidays", [])]

    print("User A reloaded data:")
    print("  Tasks:", t_titles)
    print("  Goals:", g_titles)
    print("  Events count:", len(e_titles))
    print("  Subjects:", s_names)
    print("  Holidays:", h_names)

    assert "Build AI CSP Agent" in t_titles, "Task missing after relogin!"
    assert "Publish AI Paper" in g_titles, "Goal missing after relogin!"
    assert any("Lab Demonstration" in t for t in e_titles), "Event missing after relogin!"
    assert "Knowledge Engineering" in s_names, "Subject missing after relogin!"
    assert "Diwali Festival" in h_names, "User-declared holiday missing after relogin!"

    # Verify /api/holidays endpoint directly
    hol_res = requests.get(f"{BASE_URL}/api/holidays", headers=headers_a_new)
    assert hol_res.status_code == 200
    user_a_hols = [h.get("name") or h.get("title") for h in hol_res.json().get("holidays", [])]
    assert "Diwali Festival" in user_a_hols, "Holiday missing from /api/holidays endpoint!"
    print(">>> PASS: Logout -> Login preserved ALL User A data, including declared holiday!")

    # 6. REGISTER USER B AND VERIFY COMPLETE MULTI-USER ISOLATION
    print("\n[6] Registering User B to verify complete account data isolation...")
    user_b_email = f"student_b_{rand_suffix}@university.edu"
    user_b_pw = "Password123!"

    res = requests.post(f"{BASE_URL}/api/auth/register", json={
        "name": "Student B",
        "email": user_b_email,
        "password": user_b_pw,
        "confirmPassword": user_b_pw
    })
    assert res.status_code == 200
    token_b = res.json().get("access_token") or res.json().get("token")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Fetch User B data
    res_b = requests.get(f"{BASE_URL}/api/data", headers=headers_b)
    assert res_b.status_code == 200
    data_b = res_b.json()

    print("User B isolation checks:")
    print("  College:", data_b.get("user", {}).get("college"))
    print("  Tasks:", len(data_b.get("tasks", [])))
    print("  Goals:", len(data_b.get("goals", [])))
    print("  Events:", len(data_b.get("events", [])))
    print("  Subjects:", len(data_b.get("subjects", [])))
    print("  Holidays:", len(data_b.get("holidays", [])))

    assert data_b.get("user", {}).get("college") != "SRM University", "LEAK: User B sees User A's university!"
    assert len(data_b.get("tasks", [])) == 0, "LEAK: User B sees User A's tasks!"
    assert len(data_b.get("goals", [])) == 0, "LEAK: User B sees User A's goals!"
    assert len(data_b.get("events", [])) == 0, "LEAK: User B sees User A's events!"
    assert len(data_b.get("subjects", [])) == 0, "LEAK: User B sees User A's subjects!"
    assert len(data_b.get("holidays", [])) == 0, "LEAK: User B sees User A's declared holidays!"

    # Check /api/holidays for User B
    b_hol_res = requests.get(f"{BASE_URL}/api/holidays", headers=headers_b)
    assert b_hol_res.status_code == 200
    b_hols = b_hol_res.json().get("holidays", [])
    assert len(b_hols) == 0, "LEAK: User B sees User A's holidays in /api/holidays!"
    print(">>> PASS: User B sees ZERO data from User A! Perfect isolation!")

    print("\n==================================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    test_full_system()
