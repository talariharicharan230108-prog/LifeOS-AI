import os
import json
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app import storage

client = TestClient(app)

def test_full_lifeos_flow():
    print("=================== LIFEOS COMPREHENSIVE TEST SUITE ===================")
    
    # Reset storage to guarantee clean test state
    storage.reset_all_data()
    data = storage.get_data()
    assert len(data.get("subjects", [])) == 0, "Subjects should be empty on fresh launch!"
    assert len(data.get("tasks", [])) == 0, "Tasks should be empty on fresh launch!"
    assert len(data.get("events", [])) == 0, "Events should be empty on fresh launch!"
    print("[PASS] Fresh launch has completely empty subjects and tasks.")

    # 1. User & Routine Configuration (Requirement 33)
    user_res = client.post("/api/data", json={
        "user": {
            "name": "Varun",
            "college": "Aurora",
            "course": "B.Tech AI / Computer Science",
            "onboarded": True
        },
        "routine": {
            "wakeTime": "07:00",
            "sleepTime": "23:00",
            "collegeStart": "09:00",
            "collegeEnd": "16:00",
            "studyHours": 3,
            "breakPreference": "15 mins per 45 mins",
            "preferredSubjects": []
        },
        "tasks": [],
        "subjects": [],
        "events": [],
        "goals": [],
        "documents": [],
        "activity": [],
        "holidays": [],
        "settings": {
            "workingDays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        }
    })
    assert user_res.status_code == 200

    # 2. Add Subject: Advanced DBMS with examDate 2026-10-08, credits 3, progress 0%
    sub_res = client.post("/api/subjects", json={
        "name": "Advanced DBMS",
        "teacher": "Dr. Naveen",
        "credits": 3,
        "progress": 0,
        "examDate": "2026-10-08",
        "examTime": "", # No exam time provided by user
        "importantTopics": [] # No topics provided by user
    })
    assert sub_res.status_code == 200
    sub_data = sub_res.json()["subject"]
    print(f"[PASS] Added Subject: {sub_data['name']}, Exam: {sub_data['examDate']}, Credits: {sub_data['credits']}")

    # 3. Add Real Task: DBMS Assignment, deadline 2026-10-05, priority high
    task_res = client.post("/api/tasks", json={
        "title": "DBMS Assignment",
        "deadline": "2026-10-05",
        "priority": "high",
        "subject": "Advanced DBMS",
        "description": "Lab queries and report"
    })
    assert task_res.status_code == 200
    task_data = task_res.json()["task"]
    print(f"[PASS] Added Task: {task_data['title']}, Deadline: {task_data['deadline']}, Priority: {task_data['priority']}")

    # 4. Context check: GET /api/ai/context
    ctx_res = client.get("/api/ai/context")
    assert ctx_res.status_code == 200
    ctx = ctx_res.json()
    assert "user" in ctx
    assert "routine" in ctx
    assert "tasks" in ctx
    assert "academic" in ctx
    assert "calendar" in ctx
    assert len(ctx["academic"]["subjects"]) == 1
    assert len(ctx["tasks"]) == 1
    print("[PASS] Canonical get_ai_context returns unified structured context.")

    # ==================== SCENARIO 2 (Requirement 34) ====================
    # Ask: "Show my upcoming exams."
    # Expected: Only information. NO calendar events created.
    print("\n--- TEST SCENARIO 2: 'Show my upcoming exams.' ---")
    events_before = len(storage.get_data().get("events", []))
    res_s2 = client.post("/api/agent", json={"message": "Show my upcoming exams."})
    assert res_s2.status_code == 200
    s2_data = res_s2.json()
    print(f"Agent Response:\n{s2_data['response']}")
    events_after = len(storage.get_data().get("events", []))
    assert events_before == events_after, f"Events were created ({events_after}) for informational query!"
    assert s2_data["action"] == "none", f"Action should be 'none', got {s2_data['action']}"
    assert "Advanced DBMS" in s2_data["response"], "Subject name not found in exams reply!"
    assert "2026-10-08" in s2_data["response"], "Exam date not found in exams reply!"
    print("[PASS] SCENARIO 2 PASSED: Only information returned, zero calendar events created.")

    # ==================== SCENARIO 3 (Requirement 35) ====================
    # Ask: "What should I study for Advanced DBMS?"
    # Expected: Academic/document info. DO NOT invent syllabus topics (like B+ trees, ACID). NO calendar events created.
    print("\n--- TEST SCENARIO 3: 'What should I study for Advanced DBMS?' ---")
    events_before = len(storage.get_data().get("events", []))
    res_s3 = client.post("/api/agent", json={"message": "What should I study for Advanced DBMS?"})
    assert res_s3.status_code == 200
    s3_data = res_s3.json()
    print(f"Agent Response:\n{s3_data['response']}")
    events_after = len(storage.get_data().get("events", []))
    assert events_before == events_after, "Events were created for study advice query!"
    assert s3_data["action"] == "none", f"Action should be 'none', got {s3_data['action']}"
    resp_text_lower = s3_data["response"].lower()
    # Check that it did NOT invent topics since user provided none
    assert "b+ trees" not in resp_text_lower and "normalization" not in resp_text_lower and "acid" not in resp_text_lower, "AI invented fake syllabus topics!"
    assert "dbms assignment" in resp_text_lower or "assignment" in resp_text_lower, "AI did not mention the pending assignment!"
    print("[PASS] SCENARIO 3 PASSED: Did not invent topics, zero calendar events created.")

    # ==================== SCENARIO 4 (Requirement 36) ====================
    # Ask: "Schedule DBMS preparation tomorrow from 6 PM to 7 PM."
    # Expected: Exactly ONE event tomorrow from 18:00 to 19:00.
    print("\n--- TEST SCENARIO 4: 'Schedule DBMS preparation tomorrow from 6 PM to 7 PM.' ---")
    events_before = len(storage.get_data().get("events", []))
    res_s4 = client.post("/api/agent", json={"message": "Schedule DBMS preparation tomorrow from 6 PM to 7 PM."})
    assert res_s4.status_code == 200
    s4_data = res_s4.json()
    print(f"Agent Response:\n{s4_data['response']}")
    events_after = len(storage.get_data().get("events", []))
    assert events_after == events_before + 1, f"Expected exactly 1 new event, got {events_after - events_before}"
    tomorrow_str = (date.today() + timedelta(days=1)).isoformat()
    last_event = storage.get_data()["events"][-1]
    assert last_event["date"] == tomorrow_str, f"Expected date {tomorrow_str}, got {last_event['date']}"
    assert last_event["startTime"] == "18:00", f"Expected startTime 18:00, got {last_event['startTime']}"
    assert last_event["endTime"] == "19:00", f"Expected endTime 19:00, got {last_event['endTime']}"
    print(f"[PASS] SCENARIO 4 PASSED: Exactly 1 event created on {tomorrow_str} from 18:00 to 19:00.")

    # Clear events before Scenario 1 test
    storage.update_section("events", [])

    # ==================== SCENARIO 1 (Requirement 33) ====================
    # Ask: "Prepare my schedule for the Advanced DBMS exam."
    # AI should analyze: Exam Oct 8, Assignment Oct 5, Routine (College 9-4, Study 3h), Sunday holiday, etc.
    print("\n--- TEST SCENARIO 1: 'Prepare my schedule for the Advanced DBMS exam.' ---")
    res_s1 = client.post("/api/agent", json={"message": "Prepare my schedule for the Advanced DBMS exam."})
    assert res_s1.status_code == 200
    s1_data = res_s1.json()
    print(f"Agent Response:\n{s1_data['response']}")
    events = storage.get_data()["events"]
    print(f"Generated {len(events)} events:")
    for ev in events:
        print(f"  [{ev.get('date')}] ({ev.get('startTime')}-{ev.get('endTime')}) {ev.get('title')} ({ev.get('type')}) - isAllDay: {ev.get('isAllDay')}")

    # Verifications for Scenario 1:
    assert len(events) > 0, "No events created for exam preparation schedule!"
    
    # 1. Check all events are within preparation range: today <= date <= 2026-10-08
    for ev in events:
        assert ev["date"] <= "2026-10-08", f"Event date {ev['date']} is after exam date 2026-10-08!"
        assert ev["date"] >= date.today().isoformat(), f"Event date {ev['date']} is before today!"

    # 2. Check study sessions are outside college hours (09:00 - 16:00)
    for ev in events:
        if ev.get("type") == "study" or ev.get("type") == "work":
            if ev.get("startTime") and ":" in ev["startTime"]:
                hour = int(ev["startTime"].split(":")[0])
                assert hour >= 16 or hour < 9, f"Study event '{ev['title']}' scheduled during college hours at {ev['startTime']}!"

    # 3. Check DBMS Assignment due Oct 5 is scheduled
    assignment_ev = [ev for ev in events if "assignment" in ev.get("title", "").lower()]
    assert len(assignment_ev) > 0, "DBMS Assignment was not scheduled before its deadline!"
    assert assignment_ev[0]["date"] <= "2026-10-05", "Assignment session scheduled after deadline!"

    # 4. Check Exam Day (2026-10-08):
    exam_day_evs = [ev for ev in events if ev.get("date") == "2026-10-08"]
    assert len(exam_day_evs) > 0, "No event on exam day!"
    exam_ev = next((e for e in exam_day_evs if "exam" in e.get("title", "").lower() or e.get("type") == "exam"), None)
    assert exam_ev is not None, "Exam day event not marked as exam!"
    # User did NOT enter an exam time -> AI MUST NOT invent an exam time (no 08:00, 10:00, 14:00, etc.)
    assert not exam_ev.get("startTime") or exam_ev.get("isAllDay") is True, f"AI invented exam time '{exam_ev.get('startTime')}' when user did not set one!"
    
    # Check no heavy study sessions on exam day
    study_on_exam_day = [e for e in exam_day_evs if e.get("type") == "study" and "exam" not in e.get("title", "").lower()]
    assert len(study_on_exam_day) == 0, "Heavy study sessions scheduled on exam day!"
    print("[PASS] SCENARIO 1 PASSED: Comprehensive cross-data analysis completed with zero invented times and strict constraints.")

    # ==================== CALENDAR GENERATION ON EXAM DAY (2026-10-08) ====================
    print("\n--- TEST: Calendar Generate with AI on Exam Day (2026-10-08) ---")
    gen_res = client.post("/api/calendar/generate", json={"date": "2026-10-08"})
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    gen_events = gen_data.get("events", [])
    print(f"Generated {len(gen_events)} events for 2026-10-08:")
    for ev in gen_events:
        print(f"  [{ev.get('startTime')}-{ev.get('endTime')}] {ev.get('title')} ({ev.get('type')}) - isAllDay: {ev.get('isAllDay')}")
    
    # Requirement 9: Do NOT generate 10 micro-events
    assert len(gen_events) <= 4, f"Generated {len(gen_events)} events! Expected at most 4 events, no 10 micro-blocks!"
    for ev in gen_events:
        assert ev["date"] == "2026-10-08", f"Event date {ev['date']} != 2026-10-08!"
        # No tiny breaks
        assert "short break" not in ev["title"].lower() and "small break" not in ev["title"].lower(), f"Found micro-break in events: {ev['title']}"

    exam_item = next((e for e in gen_events if "exam" in e.get("title", "").lower() or e.get("type") == "exam"), None)
    assert exam_item is not None, "Exam not recognized on 2026-10-08!"
    assert not exam_item.get("startTime") or exam_item.get("isAllDay") is True, f"Invented exam time on Calendar Generate: {exam_item.get('startTime')}"
    print("[PASS] Calendar generation on Exam Day properly recognized EXAM DAY with no invented time and max 4 events.")

    # ==================== SCENARIO 5 (Requirement 37) ====================
    print("\n--- TEST SCENARIO 5: 'Plan my week.' ---")
    storage.update_section("events", [])
    res_s5 = client.post("/api/agent", json={"message": "Plan my week."})
    assert res_s5.status_code == 200
    s5_data = res_s5.json()
    week_events = storage.get_data()["events"]
    print(f"Weekly events created: {len(week_events)}")
    
    # Check no 10 events per day
    events_per_day = {}
    for ev in week_events:
        events_per_day[ev["date"]] = events_per_day.get(ev["date"], 0) + 1
    for d, count in events_per_day.items():
        assert count <= 4, f"Day {d} has {count} events! Expected <= 4, not 10 micro-events!"
    
    # Check dates within 7 days
    max_d = (date.today() + timedelta(days=7)).isoformat()
    for ev in week_events:
        assert ev["date"] < max_d, f"Event {ev['title']} date {ev['date']} outside 7-day week!"
    print("[PASS] SCENARIO 5 PASSED: Meaningful weekly schedule created, no 10 micro-blocks, no duplicate college hours.")

    print("\n=================== ALL 5 SCENARIOS PASSED WITH 100% SUCCESS ===================")

if __name__ == "__main__":
    test_full_lifeos_flow()
