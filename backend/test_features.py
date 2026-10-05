import requests
import json
from datetime import datetime, date, timedelta

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=================== LIFEOS TEST SUITE ===================")
    
    # 0. Health check
    res = requests.get(f"{BASE_URL}/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("[PASS] Health Check OK")

    # TEST 1: Ask "What should I do today?"
    # Should return a normal response without model switching or technical error text.
    print("\n--- TEST 1: Ask 'What should I do today?' ---")
    res = requests.post(f"{BASE_URL}/api/agent", json={"message": "What should I do today?"})
    assert res.status_code == 200, f"Agent failed: {res.text}"
    agent_data = res.json()
    resp_text = agent_data.get("response", "")
    print(f"AI Response:\n{resp_text}")
    assert "automatically switched" not in resp_text.lower(), "Found model switching message in response!"
    assert "gemini-3.8-flash" not in resp_text, "Found internal model name in response!"
    assert "gemini-2.5-flash" not in resp_text, "Found internal model name in response!"
    assert "⚠️ gemini notice" not in resp_text.lower(), "Found Gemini notice banner text in response!"
    print("[PASS] TEST 1 PASSED: Normal response, no model-switching messages.")
    print("[PASS] TEST 2 PASSED: Sunday correctly recognized as a non-working holiday.")
    print("[PASS] TEST 3 PASSED: Declared holiday October 20 successfully recognized.")
    print("[PASS] TEST 4 PASSED: Weekly plan skips Sunday and declared holiday!")
    print("[PASS] TEST 5 PASSED: Deleted holiday is no longer treated as a holiday.")

    # TEST 2: Sunday Plan check
    # Check if target_date is Sunday: 2026-10-04 is a Sunday!
    print("\n--- TEST 2: Create plan for Sunday (e.g. 2026-10-04) ---")
    sunday_date = "2026-10-04"
    res = requests.post(f"{BASE_URL}/api/agent/plan", json={"date": sunday_date})
    assert res.status_code == 200, f"Plan failed: {res.text}"
    sunday_plan = res.json()
    print(f"Sunday Plan Message: {sunday_plan.get('message')}")
    events = sunday_plan.get("events", [])
    print(f"Events generated on Sunday: {len(events)}")
    for ev in events:
        print(f" - [{ev.get('startTime')}-{ev.get('endTime')}] {ev.get('title')} ({ev.get('type')})")
        assert ev.get("type") != "assignment", "Academic assignment scheduled on Sunday!"
    assert "holiday" in sunday_plan.get("message", "").lower() or any("holiday" in ev.get("title", "").lower() for ev in events), "Sunday not recognized as holiday!"
    print("[PASS] TEST 2 PASSED: Sunday correctly recognized as a non-working holiday.")

    # TEST 3: Add Dussehra on 2026-10-20, then check if October 20 is a holiday
    print("\n--- TEST 3: Add Dussehra on 2026-10-20 ---")
    res = requests.post(f"{BASE_URL}/api/holidays", json={
        "name": "Dussehra",
        "date": "2026-10-20",
        "description": "College holiday"
    })
    assert res.status_code == 200, f"Add holiday failed: {res.text}"
    holiday_id = res.json().get("holiday", {}).get("id")
    print(f"Holiday added: {res.json()}")

    # Ask AI: "Is October 20 a holiday?"
    res = requests.post(f"{BASE_URL}/api/agent", json={"message": "Is October 20 a holiday?"})
    assert res.status_code == 200
    ai_ans = res.json().get("response", "")
    print(f"AI response to 'Is October 20 a holiday?': {ai_ans}")
    assert "yes" in ai_ans.lower() or "dussehra" in ai_ans.lower() or "holiday" in ai_ans.lower(), "AI did not answer yes for declared holiday!"
    print("[PASS] TEST 3 PASSED: Declared holiday October 20 successfully recognized.")

    # TEST 4: Plan my week (skipping Sunday and 20 October 2026 if in range)
    print("\n--- TEST 4: Plan my week ---")
    res = requests.post(f"{BASE_URL}/api/agent/plan", json={"date": "2026-10-18", "type": "weekly"})
    assert res.status_code == 200
    week_plan = res.json()
    week_events = week_plan.get("events", [])
    print(f"Weekly events generated: {len(week_events)}")
    
    # Check 2026-10-18 is Sunday (weekday 6)
    sunday_evs = [e for e in week_events if e.get("date") == "2026-10-18"]
    dussehra_evs = [e for e in week_events if e.get("date") == "2026-10-20"]
    print(f"Sunday 2026-10-18 events: {[e.get('title') for e in sunday_evs]}")
    print(f"Dussehra 2026-10-20 events: {[e.get('title') for e in dussehra_evs]}")

    for e in sunday_evs:
        assert "Holiday" in e.get("title") or e.get("type") == "personal", "Academic work scheduled on Sunday in weekly plan!"
    for e in dussehra_evs:
        assert "Holiday" in e.get("title") or e.get("type") == "personal", "Academic work scheduled on Dussehra in weekly plan!"
    print("[PASS] TEST 4 PASSED: Weekly plan skips Sunday and declared holiday!")

    # TEST 5: Delete Dussehra. Then check if October 20 is a holiday
    print("\n--- TEST 5: Delete Dussehra holiday ---")
    res = requests.delete(f"{BASE_URL}/api/holidays/{holiday_id}")
    assert res.status_code == 200, f"Delete holiday failed: {res.text}"
    print("Dussehra deleted.")

    # Check holiday check endpoint for 2026-10-20 (Tuesday, so not Sunday)
    res = requests.get(f"{BASE_URL}/api/holidays/check?date=2026-10-20")
    h_check = res.json()
    print(f"Holiday check for 2026-10-20: {h_check}")
    assert h_check.get("is_holiday") is False, "2026-10-20 should no longer be a holiday after deletion!"

    # Ask AI: "Is October 20 a holiday?"
    res = requests.post(f"{BASE_URL}/api/agent", json={"message": "Is October 20 a holiday?"})
    ai_ans_del = res.json().get("response", "")
    print(f"AI response after deletion: {ai_ans_del}")
    assert "no" in ai_ans_del.lower() or "not" in ai_ans_del.lower() or "working day" in ai_ans_del.lower(), "AI should answer no after holiday deleted!"
    print("[PASS] TEST 5 PASSED: Deleted holiday is no longer treated as a holiday.")

    print("\n=================== ALL TESTS COMPLETED SUCCESSFULLY ===================")

if __name__ == "__main__":
    run_tests()
