import os
import json
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app import storage
from app import time_utils

client = TestClient(app)

def test_10_time_aware_questions():
    print("=================== LIFEOS 10 TIME-AWARE QUESTIONS TEST ===================")
    
    # Reset storage to guarantee known test state
    storage.reset_all_data()
    
    # Setup test user, routine, academic subjects, tasks, and calendar events
    client.post("/api/data", json={
        "user": {
            "name": "Varun",
            "college": "Aurora University",
            "course": "B.Tech AI / CS",
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

    # Add Subject: Advanced DBMS with examDate
    curr_dt = time_utils.get_current_datetime()
    curr_date_str = curr_dt["date"]
    curr_date_obj = datetime.strptime(curr_date_str, "%Y-%m-%d").date()
    exam_date_str = (curr_date_obj + timedelta(days=5)).isoformat()
    assignment_deadline_str = (curr_date_obj + timedelta(days=2)).isoformat()
    overdue_deadline_str = (curr_date_obj - timedelta(days=1)).isoformat()

    client.post("/api/subjects", json={
        "name": "Advanced DBMS",
        "teacher": "Dr. Naveen",
        "credits": 3,
        "progress": 0,
        "examDate": exam_date_str,
        "examTime": "",
        "importantTopics": ["Indexing", "Query Optimization"]
    })

    # Add Tasks: 1 overdue, 1 upcoming DBMS assignment, 1 general
    client.post("/api/tasks", json={
        "title": "DBMS Assignment",
        "deadline": assignment_deadline_str,
        "priority": "high",
        "subject": "Advanced DBMS",
        "description": "Lab queries and report"
    })
    client.post("/api/tasks", json={
        "title": "Past Lab Report",
        "deadline": overdue_deadline_str,
        "priority": "high",
        "subject": "Advanced DBMS",
        "description": "Overdue submission"
    })

    print(f"Current Date: {curr_date_str}, Time: {curr_dt['time']} ({curr_dt['timezone']})")
    print(f"Added Subject: Advanced DBMS with exam on {exam_date_str}")
    print(f"Added Tasks: DBMS Assignment (due {assignment_deadline_str}), Past Lab Report (overdue {overdue_deadline_str})")

    # ----------------------------------------------------
    # QUESTION 1: "hello"
    # Expected: Fast normal response.
    # ----------------------------------------------------
    print("\n--- TEST 1: 'hello' ---")
    res1 = client.post("/api/agent", json={"message": "hello"})
    assert res1.status_code == 200
    d1 = res1.json()
    print("Response:\n" + d1["response"])
    assert d1["action"] == "none"
    assert "hello" in d1["response"].lower() or "assist" in d1["response"].lower() or curr_dt["day"].lower() in d1["response"].lower()
    print("[PASS] Test 1 passed.")

    # ----------------------------------------------------
    # QUESTION 2: "What time is it?"
    # Expected: Actual current time.
    # ----------------------------------------------------
    print("\n--- TEST 2: 'What time is it?' ---")
    res2 = client.post("/api/agent", json={"message": "What time is it?"})
    assert res2.status_code == 200
    d2 = res2.json()
    print("Response:\n" + d2["response"])
    assert d2["action"] == "none"
    assert curr_dt["time"] in d2["response"] or time_utils.format_time_12h(curr_dt["time"]) in d2["response"]
    assert curr_dt["day"] in d2["response"]
    print("[PASS] Test 2 passed.")

    # ----------------------------------------------------
    # QUESTION 3: "What should I do now?"
    # Expected: Analyzes current time + today's events/tasks/routine.
    # ----------------------------------------------------
    print("\n--- TEST 3: 'What should I do now?' ---")
    res3 = client.post("/api/agent", json={"message": "What should I do now?"})
    assert res3.status_code == 200
    d3 = res3.json()
    print("Response:\n" + d3["response"])
    assert d3["action"] == "none"
    # Should recommend next action based on current time
    assert len(d3["response"]) > 20
    print("[PASS] Test 3 passed.")

    # ----------------------------------------------------
    # QUESTION 4: "What is my next event?"
    # Expected: Nearest future event only.
    # ----------------------------------------------------
    print("\n--- TEST 4: 'What is my next event?' ---")
    # First test with no calendar events
    res4a = client.post("/api/agent", json={"message": "What is my next event?"})
    assert res4a.status_code == 200
    d4a = res4a.json()
    print("Response (No events):\n" + d4a["response"])
    assert d4a["action"] == "none"
    assert "no upcoming events" in d4a["response"].lower()

    # Now add an upcoming event for today or tomorrow and check
    tom_str = (curr_date_obj + timedelta(days=1)).isoformat()
    client.post("/api/events", json={
        "title": "AI Study Session",
        "date": tom_str,
        "startTime": "18:00",
        "endTime": "19:30",
        "type": "study"
    })
    res4b = client.post("/api/agent", json={"message": "What is my next event?"})
    assert res4b.status_code == 200
    d4b = res4b.json()
    print("Response (With future event):\n" + d4b["response"])
    assert "AI Study Session" in d4b["response"]
    assert d4b["action"] == "none"
    print("[PASS] Test 4 passed.")

    # ----------------------------------------------------
    # QUESTION 5: "What do I have today?"
    # Expected: Today's relevant tasks/events/deadlines.
    # ----------------------------------------------------
    print("\n--- TEST 5: 'What do I have today?' ---")
    res5 = client.post("/api/agent", json={"message": "What do I have today?"})
    assert res5.status_code == 200
    d5 = res5.json()
    print("Response:\n" + d5["response"])
    assert d5["action"] == "none"
    assert curr_date_str in d5["response"] or curr_dt["day"] in d5["response"]
    print("[PASS] Test 5 passed.")

    # ----------------------------------------------------
    # QUESTION 6: "What should I study now?"
    # Expected: Time-aware response using academic/tasks/events.
    # ----------------------------------------------------
    print("\n--- TEST 6: 'What should I study now?' ---")
    res6 = client.post("/api/agent", json={"message": "What should I study now?"})
    assert res6.status_code == 200
    d6 = res6.json()
    print("Response:\n" + d6["response"])
    assert d6["action"] == "none"
    # Academic subject or routine sleep/college is mentioned
    assert "dbms" in d6["response"].lower() or "rest" in d6["response"].lower() or "college" in d6["response"].lower()
    print("[PASS] Test 6 passed.")

    # ----------------------------------------------------
    # QUESTION 7: "How much free time do I have?"
    # Expected: Calculate available time using current time and next fixed event.
    # ----------------------------------------------------
    print("\n--- TEST 7: 'How much free time do I have?' ---")
    res7 = client.post("/api/agent", json={"message": "How much free time do I have?"})
    assert res7.status_code == 200
    d7 = res7.json()
    print("Response:\n" + d7["response"])
    assert d7["action"] == "none"
    assert "free" in d7["response"].lower() or "busy" in d7["response"].lower() or "college" in d7["response"].lower()
    print("[PASS] Test 7 passed.")

    # ----------------------------------------------------
    # QUESTION 8: "What are my upcoming deadlines?"
    # Expected: Only relevant future deadlines (distinguishing overdue).
    # ----------------------------------------------------
    print("\n--- TEST 8: 'What are my upcoming deadlines?' ---")
    res8 = client.post("/api/agent", json={"message": "What are my upcoming deadlines?"})
    assert res8.status_code == 200
    d8 = res8.json()
    print("Response:\n" + d8["response"])
    assert d8["action"] == "none"
    assert "DBMS Assignment" in d8["response"]
    # Overdue task is properly labeled or separated
    assert "overdue" in d8["response"].lower() or "past" in d8["response"].lower()
    print("[PASS] Test 8 passed.")

    # ----------------------------------------------------
    # QUESTION 9: "What should I do before my DBMS exam?"
    # Expected: Use exam date + tasks + routine + calendar + holidays. Zero calendar events created!
    # ----------------------------------------------------
    print("\n--- TEST 9: 'What should I do before my DBMS exam?' ---")
    events_before = len(storage.get_data().get("events", []))
    res9 = client.post("/api/agent", json={"message": "What should I do before my DBMS exam?"})
    assert res9.status_code == 200
    d9 = res9.json()
    print("Response:\n" + d9["response"])
    events_after = len(storage.get_data().get("events", []))
    assert events_before == events_after, f"Events were erroneously created ({events_after - events_before}) for informational question 9!"
    assert d9["action"] == "none"
    assert "Advanced DBMS" in d9["response"] or "DBMS" in d9["response"]
    assert "college" in d9["response"].lower()
    print("[PASS] Test 9 passed (zero calendar events created).")

    # ----------------------------------------------------
    # QUESTION 10: "Plan my DBMS preparation until the exam."
    # Expected: Use Gemini and generate a plan only because user explicitly requested planning.
    # ----------------------------------------------------
    print("\n--- TEST 10: 'Plan my DBMS preparation until the exam.' ---")
    events_before_10 = len(storage.get_data().get("events", []))
    res10 = client.post("/api/agent", json={"message": "Plan my DBMS preparation until the exam."})
    assert res10.status_code == 200
    d10 = res10.json()
    print("Response:\n" + d10["response"])
    events_after_10 = len(storage.get_data().get("events", []))
    assert d10["action"] in ["create_schedule", "create_calendar_event"]
    assert events_after_10 > events_before_10, "Events should be created when user explicitly requested planning!"
    print(f"Created {events_after_10 - events_before_10} preparation event(s).")
    print("[PASS] Test 10 passed.")

    # ----------------------------------------------------
    # ADDITIONAL TIME-AWARE QUESTIONS
    # ----------------------------------------------------
    print("\n--- TEST: 'What do I have tonight?' ---")
    res_tonight = client.post("/api/agent", json={"message": "What do I have tonight?"})
    assert res_tonight.status_code == 200
    print("Tonight Response:\n" + res_tonight.json()["response"])
    assert res_tonight.json()["action"] == "none"
    print("[PASS] 'What do I have tonight?' passed.")

    print("\n--- TEST: 'Am I free now?' ---")
    res_free = client.post("/api/agent", json={"message": "Am I free now?"})
    assert res_free.status_code == 200
    print("Am I free Response:\n" + res_free.json()["response"])
    assert res_free.json()["action"] == "none"
    print("[PASS] 'Am I free now?' passed.")

    print("\n--- TEST: 'What should I do tomorrow?' ---")
    res_tom = client.post("/api/agent", json={"message": "What should I do tomorrow?"})
    assert res_tom.status_code == 200
    print("Tomorrow Response:\n" + res_tom.json()["response"])
    assert res_tom.json()["action"] == "none"
    print("[PASS] 'What should I do tomorrow?' passed.")

    print("\n=================== ALL 10 TIME-AWARE TESTS PASSED 100% ===================")

if __name__ == "__main__":
    test_10_time_aware_questions()
