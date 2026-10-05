import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from . import storage

def get_tasks(status: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns the list of user tasks strictly where user_id matches, optionally filtered by status ('pending' or 'completed')."""
    data = storage.get_data(user_id)
    target_uid = user_id or data.get("id")
    tasks = data.get("tasks", [])
    if target_uid:
        for t in tasks:
            if "user_id" not in t:
                t["user_id"] = target_uid
        tasks = [t for t in tasks if t.get("user_id") == target_uid]
    if status == "pending":
        return [t for t in tasks if not t.get("completed", False)]
    elif status == "completed":
        return [t for t in tasks if t.get("completed", False)]
    return tasks

def add_task(title: str, deadline: Optional[str] = None, priority: str = "medium", subject: str = "", description: str = "", user_id: Optional[str] = None) -> Dict[str, Any]:
    """Adds a new task to LifeOS storage tagged with user_id."""
    data = storage.get_data(user_id)
    target_uid = user_id or data.get("id")
    new_task = {
        "id": str(uuid.uuid4())[:8],
        "user_id": target_uid,
        "title": title.strip(),
        "deadline": deadline or "",
        "priority": priority.lower() if priority else "medium",
        "subject": subject.strip(),
        "description": description.strip(),
        "completed": False,
        "createdAt": datetime.now().isoformat()
    }
    data.setdefault("tasks", []).append(new_task)
    storage.save_data(data, user_id)
    storage.log_activity("add_task", f"Added task '{title}'", user_id=user_id)
    return {"status": "success", "message": f"Task '{title}' added successfully.", "task": new_task}

def update_task(task_id: str, updates: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Updates an existing task."""
    data = storage.get_data(user_id)
    for task in data.get("tasks", []):
        if task.get("id") == task_id or task.get("title", "").lower() == task_id.lower():
            task.update(updates)
            storage.save_data(data, user_id)
            storage.log_activity("update_task", f"Updated task '{task.get('title')}'", user_id=user_id)
            return {"status": "success", "message": f"Task '{task.get('title')}' updated.", "task": task}
    return {"status": "error", "message": f"Task '{task_id}' not found."}

def delete_task(task_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Deletes a task by ID or exact title."""
    data = storage.get_data(user_id)
    tasks = data.get("tasks", [])
    initial_len = len(tasks)
    remaining = [t for t in tasks if t.get("id") != task_id and t.get("title", "").lower() != task_id.lower()]
    if len(remaining) < initial_len:
        data["tasks"] = remaining
        storage.save_data(data, user_id)
        storage.log_activity("delete_task", f"Deleted task '{task_id}'", user_id=user_id)
        return {"status": "success", "message": f"Task '{task_id}' deleted."}
    return {"status": "error", "message": f"Task '{task_id}' not found."}

def get_calendar_events(date_str: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns calendar events strictly where user_id matches, optionally filtered for a specific date (YYYY-MM-DD)."""
    data = storage.get_data(user_id)
    target_uid = user_id or data.get("id")
    events = data.get("events", [])
    if target_uid:
        for e in events:
            if "user_id" not in e:
                e["user_id"] = target_uid
        events = [e for e in events if e.get("user_id") == target_uid]
    if date_str:
        clean = str(date_str).split("T")[0].strip()
        return [e for e in events if e.get("date") == clean]
    return events

# Alias for backward compatibility
get_schedule = get_calendar_events

def create_calendar_event(
    title: str,
    date: str,
    startTime: Optional[str] = None,
    endTime: Optional[str] = None,
    type: str = "work",
    description: str = "",
    source: str = "user",
    isAllDay: bool = False,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Creates a single calendar event on the strictly specified date with user_id tag.
    Checks for duplicates before inserting.
    If type == 'exam' and no start time is specified, does NOT invent times (sets isAllDay=True).
    """
    if not title or not title.strip():
        return {"status": "error", "message": "Event title is required."}
    if not date or not date.strip():
        return {"status": "error", "message": "Event date (YYYY-MM-DD) is required."}

    date_clean = str(date).split("T")[0].strip()
    data = storage.get_data(user_id)
    target_uid = user_id or data.get("id")
    existing_events = data.setdefault("events", [])

    is_exam = (type or "").lower() == "exam" or "exam" in title.lower()

    if is_exam and not startTime:
        startTime_clean = ""
        endTime_clean = ""
        is_all_day = True
    else:
        startTime_clean = startTime if startTime is not None else ("" if isAllDay else "18:00")
        endTime_clean = endTime if endTime is not None else ("" if isAllDay else "19:00")
        is_all_day = isAllDay or (startTime_clean == "" and endTime_clean == "")

    # Duplicate check: same date, same title (case-insensitive)
    for e in existing_events:
        e_title = e.get("title", "").strip().lower()
        if e.get("date") == date_clean and e_title == title.strip().lower():
            if is_all_day or e.get("isAllDay") or e.get("startTime") == startTime_clean:
                return {"status": "success", "message": f"Event '{title}' already exists on {date_clean}.", "event": e, "duplicate": True}
        if e.get("date") == date_clean and "college" in title.strip().lower() and "college" in e_title:
            return {"status": "success", "message": f"College hours already scheduled on {date_clean}.", "event": e, "duplicate": True}

    new_event = {
        "id": "event-" + str(uuid.uuid4())[:8],
        "user_id": target_uid,
        "title": title.strip(),
        "date": date_clean,
        "startTime": startTime_clean,
        "endTime": endTime_clean,
        "isAllDay": is_all_day,
        "type": type.lower() if type else "work",
        "description": description.strip() if description else "",
        "source": source or "user"
    }
    existing_events.append(new_event)
    storage.save_data(data, user_id)
    storage.log_activity("create_calendar_event", f"Scheduled '{title}' on {date_clean}", user_id=user_id)
    return {"status": "success", "message": f"Scheduled '{title}' on {date_clean}.", "event": new_event}

def update_calendar_event(event_id: str, updates: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Updates an existing calendar event."""
    data = storage.get_data(user_id)
    for ev in data.get("events", []):
        if ev.get("id") == event_id or ev.get("title", "").lower() == event_id.lower():
            ev.update(updates)
            storage.save_data(data, user_id)
            storage.log_activity("update_calendar_event", f"Updated event '{ev.get('title')}'", user_id=user_id)
            return {"status": "success", "message": f"Event '{ev.get('title')}' updated.", "event": ev}
    return {"status": "error", "message": f"Event '{event_id}' not found."}

def delete_calendar_event(event_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Deletes a calendar event by ID or exact title."""
    data = storage.get_data(user_id)
    events = data.get("events", [])
    initial_len = len(events)
    remaining = [e for e in events if e.get("id") != event_id and e.get("title", "").lower() != event_id.lower()]
    if len(remaining) < initial_len:
        data["events"] = remaining
        storage.save_data(data, user_id)
        storage.log_activity("delete_calendar_event", f"Deleted event '{event_id}'", user_id=user_id)
        return {"status": "success", "message": f"Event '{event_id}' deleted."}
    return {"status": "error", "message": f"Event '{event_id}' not found."}

def create_schedule(events: List[Dict[str, Any]], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Batch creates calendar events, avoiding exact duplicates."""
    created = []
    for ev in events:
        res = create_calendar_event(
            title=ev.get("title", "Scheduled Activity"),
            date=ev.get("date", ""),
            startTime=ev.get("startTime"),
            endTime=ev.get("endTime"),
            type=ev.get("type", "work"),
            description=ev.get("description", ""),
            source=ev.get("source", "ai"),
            isAllDay=ev.get("isAllDay", False),
            user_id=user_id
        )
        if res.get("status") == "success" and not res.get("duplicate"):
            created.append(res.get("event"))
    return {"status": "success", "message": f"Created {len(created)} calendar event(s).", "events": created}

def get_routine(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Returns user routine and working days configuration."""
    data = storage.get_data(user_id)
    return {
        "user_id": user_id or data.get("id"),
        "routine": data.get("routine", {}),
        "workingDays": storage.get_working_days(user_id)
    }

def get_goals(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all user goals strictly where user_id matches."""
    data = storage.get_data(user_id)
    target_uid = user_id or data.get("id")
    goals = data.get("goals", [])
    if target_uid:
        for g in goals:
            if "user_id" not in g:
                g["user_id"] = target_uid
        return [g for g in goals if g.get("user_id") == target_uid]
    return goals

def get_academic_data(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Returns user's academic profile and enrolled subjects strictly where user_id matches."""
    data = storage.get_data(user_id)
    target_uid = user_id or data.get("id")
    subjects = data.get("subjects", [])
    if target_uid:
        for s in subjects:
            if "user_id" not in s:
                s["user_id"] = target_uid
        subjects = [s for s in subjects if s.get("user_id") == target_uid]
    return {
        "user_id": target_uid,
        "user": data.get("user"),
        "subjects": subjects,
        "routine": data.get("routine", {})
    }

def search_documents(query: str = "", user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Searches uploaded document metadata and extracted text snippets strictly where user_id matches."""
    data = storage.get_data(user_id)
    target_uid = user_id or data.get("id")
    docs = data.get("documents", [])
    if target_uid:
        for d in docs:
            if "user_id" not in d:
                d["user_id"] = target_uid
        docs = [d for d in docs if d.get("user_id") == target_uid]
    if not query:
        return docs
    q = query.lower()
    results = []
    for doc in docs:
        if q in doc.get("name", "").lower() or q in doc.get("textSnippet", "").lower():
            results.append(doc)
    return results

def get_holidays(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns all declared holidays in LifeOS (Note: Sunday is also automatically an eternal holiday)."""
    data = storage.get_data(user_id)
    return data.get("holidays", [])

def add_holiday(name: str, date: str, description: str = "", user_id: Optional[str] = None) -> Dict[str, Any]:
    """Adds a declared holiday (name, date in YYYY-MM-DD, optional description)."""
    data = storage.get_data(user_id)
    clean_date = str(date).split("T")[0].strip()
    new_h = {
        "id": "holiday-" + str(uuid.uuid4())[:8],
        "name": name.strip(),
        "date": clean_date,
        "description": description.strip()
    }
    data.setdefault("holidays", []).append(new_h)
    storage.save_data(data, user_id)
    storage.log_activity("add_holiday", f"Added holiday '{name}' on {clean_date}", user_id=user_id)
    return {"status": "success", "message": f"Holiday '{name}' on {clean_date} added successfully.", "holiday": new_h}

def delete_holiday(holiday_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Deletes a declared holiday by ID or name. (Sunday cannot be deleted as it is a permanent weekly holiday)."""
    data = storage.get_data(user_id)
    holidays = data.get("holidays", [])
    initial_len = len(holidays)
    remaining = [h for h in holidays if h.get("id") != holiday_id and h.get("name", "").lower() != holiday_id.lower() and h.get("date", "") != holiday_id]
    if len(remaining) < initial_len:
        data["holidays"] = remaining
        storage.save_data(data, user_id)
        storage.log_activity("delete_holiday", f"Deleted holiday '{holiday_id}'", user_id=user_id)
        return {"status": "success", "message": f"Holiday '{holiday_id}' deleted."}
    return {"status": "error", "message": f"Holiday '{holiday_id}' not found."}

def check_is_holiday(date_str: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Checks whether a given date (YYYY-MM-DD) is a holiday (Sunday or declared holiday)."""
    is_h, reason = storage.is_holiday(date_str, user_id=user_id)
    return {
        "date": date_str,
        "is_holiday": is_h,
        "reason": reason if is_h else "Working day"
    }

# Map of tool names to functions for AI execution
TOOL_REGISTRY = {
    "get_tasks": get_tasks,
    "add_task": add_task,
    "update_task": update_task,
    "delete_task": delete_task,
    "get_calendar_events": get_calendar_events,
    "create_calendar_event": create_calendar_event,
    "update_calendar_event": update_calendar_event,
    "delete_calendar_event": delete_calendar_event,
    "get_schedule": get_schedule,
    "create_schedule": create_schedule,
    "get_routine": get_routine,
    "get_goals": get_goals,
    "get_academic_data": get_academic_data,
    "search_documents": search_documents,
    "get_holidays": get_holidays,
    "add_holiday": add_holiday,
    "delete_holiday": delete_holiday,
    "is_holiday": check_is_holiday
}
