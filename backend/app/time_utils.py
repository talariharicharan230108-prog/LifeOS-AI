import os
import re
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple

def get_current_datetime(timezone_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Requirement 1: Dynamically obtain current system date and time.
    Uses Python datetime and timezone-aware datetime.
    Configurable timezone, default to system local timezone.
    Returns:
    {
        "date": "YYYY-MM-DD",
        "time": "HH:MM",
        "day": "Monday",
        "timezone": "...",
        "datetime": "..."
    }
    """
    tz = None
    if timezone_str:
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(timezone_str)
        except Exception:
            pass

    if tz is None:
        env_tz = os.getenv("LIFEOS_TIMEZONE") or os.getenv("TIMEZONE")
        if env_tz:
            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(env_tz)
            except Exception:
                pass

    if tz:
        now = datetime.now(tz)
    else:
        now = datetime.now().astimezone()

    tz_name = now.tzname() or str(now.tzinfo) or "Local"
    return {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "day": now.strftime("%A"),
        "timezone": tz_name,
        "datetime": now.isoformat()
    }

def parse_time_minutes(time_str: str) -> int:
    """Parses 'HH:MM' into integer minutes from midnight (0..1439). Returns -1 if invalid."""
    if not time_str or not isinstance(time_str, str):
        return -1
    parts = time_str.strip().split(":")
    if len(parts) >= 2:
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return -1
    return -1

def format_minutes_to_time(minutes: int) -> str:
    """Converts integer minutes to 'HH:MM' 24-hour string."""
    m = minutes % 1440
    h = m // 60
    mins = m % 60
    return f"{h:02d}:{mins:02d}"

def format_time_12h(time_str: str) -> str:
    """Converts '18:30' -> '6:30 PM', '09:00' -> '9:00 AM'."""
    if not time_str:
        return ""
    try:
        parts = time_str.strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        suffix = "PM" if h >= 12 else "AM"
        h12 = h % 12
        if h12 == 0:
            h12 = 12
        if m == 0:
            return f"{h12} {suffix}"
        return f"{h12}:{m:02d} {suffix}"
    except Exception:
        return time_str

def format_duration(minutes: int) -> str:
    """Formats minute duration into friendly text, e.g. '10 minutes', 'about 2 hours', '1 hour and 15 minutes'."""
    if minutes <= 0:
        return "0 minutes"
    hours = minutes // 60
    rem = minutes % 60
    if hours > 0 and rem > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} and {rem} minute{'s' if rem > 1 else ''}"
    elif hours > 0:
        return f"about {hours} hour{'s' if hours > 1 else ''}"
    else:
        return f"{rem} minute{'s' if rem > 1 else ''}"

def evaluate_event_status(event: Dict[str, Any], curr_time_str: str) -> Dict[str, Any]:
    """
    Requirement 6: Current Event Detection:
    current_time < event_start -> Upcoming
    event_start <= current_time < event_end -> In Progress
    current_time >= event_end -> Completed
    """
    curr_m = parse_time_minutes(curr_time_str)
    start_str = event.get("startTime", "").strip()
    end_str = event.get("endTime", "").strip()
    is_all_day = event.get("isAllDay", False)

    if is_all_day or not start_str:
        return {
            "status": "all_day",
            "minutes_until": 0,
            "minutes_remaining": 0,
            "start": start_str,
            "end": end_str,
            "event": event
        }

    start_m = parse_time_minutes(start_str)
    if not end_str:
        end_m = (start_m + 60) % 1440
        end_str = format_minutes_to_time(end_m)
    else:
        end_m = parse_time_minutes(end_str)

    if curr_m < start_m:
        return {
            "status": "upcoming",
            "minutes_until": start_m - curr_m,
            "minutes_remaining": 0,
            "start": start_str,
            "end": end_str,
            "event": event
        }
    elif start_m <= curr_m < end_m:
        return {
            "status": "in_progress",
            "minutes_until": 0,
            "minutes_remaining": end_m - curr_m,
            "start": start_str,
            "end": end_str,
            "event": event
        }
    else:
        return {
            "status": "completed",
            "minutes_until": 0,
            "minutes_remaining": 0,
            "start": start_str,
            "end": end_str,
            "event": event
        }

def get_time_analysis(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Requirement 4, 6, 7, 8, 9, 10, 11, 12, 13:
    Deterministic time, routine, calendar, task, and exam calculation in Python.
    Evaluates exact current state without calling Gemini.
    """
    today_info = ctx.get("today", {})
    curr_date = today_info.get("date")
    curr_time = today_info.get("time")
    curr_day = today_info.get("dayOfWeek")
    curr_tz = today_info.get("timezone", "Local")
    is_holiday = today_info.get("isHoliday", False)
    holiday_reason = today_info.get("holidayReason", "")

    routine = ctx.get("routine", {})
    wake_time = routine.get("wakeTime", "07:00")
    sleep_time = routine.get("sleepTime", "23:00")
    college_start = routine.get("collegeStart", "09:00")
    college_end = routine.get("collegeEnd", "16:00")
    working_days = ctx.get("workingDays", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"])
    is_working_day = (curr_day in working_days) and not is_holiday

    curr_m = parse_time_minutes(curr_time)
    wake_m = parse_time_minutes(wake_time)
    sleep_m = parse_time_minutes(sleep_time)
    c_start_m = parse_time_minutes(college_start)
    c_end_m = parse_time_minutes(college_end)

    in_college_hours = is_working_day and (c_start_m <= curr_m < c_end_m)
    before_college = is_working_day and (wake_m <= curr_m < c_start_m)
    after_college = is_working_day and (c_end_m <= curr_m < sleep_m)
    is_night = curr_m >= sleep_m or curr_m < wake_m

    all_events = ctx.get("calendar", {}).get("events", [])
    today_events = [e for e in all_events if e.get("date") == curr_date]
    evaluated_events = [evaluate_event_status(e, curr_time) for e in today_events]

    completed_events = [e for e in evaluated_events if e["status"] == "completed"]
    in_progress_events = [e for e in evaluated_events if e["status"] == "in_progress"]
    upcoming_events = [e for e in evaluated_events if e["status"] == "upcoming"]
    all_day_events = [e for e in evaluated_events if e["status"] == "all_day"]

    upcoming_events.sort(key=lambda x: parse_time_minutes(x["start"]))
    current_event = in_progress_events[0] if in_progress_events else None
    next_event = upcoming_events[0] if upcoming_events else None

    # Future events on days after today
    future_events = [e for e in all_events if e.get("date") and e.get("date") > curr_date]
    future_events.sort(key=lambda x: (x.get("date", ""), x.get("startTime", "")))
    next_future_event = future_events[0] if future_events else None

    # Calculate free time
    if current_event:
        free_minutes = 0
        free_until_desc = f"until {format_time_12h(current_event['end'])} ({current_event['event'].get('title')})"
    elif in_college_hours:
        free_minutes = 0
        free_until_desc = f"until college hours end at {format_time_12h(college_end)}"
    elif next_event:
        free_minutes = next_event["minutes_until"]
        free_until_desc = f"before your next scheduled event, **{next_event['event'].get('title')}** at {format_time_12h(next_event['start'])}"
    elif before_college:
        free_minutes = max(0, c_start_m - curr_m)
        free_until_desc = f"before college starts at {format_time_12h(college_start)}"
    elif curr_m < sleep_m:
        free_minutes = max(0, sleep_m - curr_m)
        free_until_desc = f"before your routine sleep time ({format_time_12h(sleep_time)})"
    else:
        free_minutes = 0
        free_until_desc = f"for tonight (past your routine sleep time of {format_time_12h(sleep_time)})"

    # Task status categorization (Requirement 8: Overdue, Due Today, Upcoming, Completed)
    tasks = ctx.get("tasks", [])
    overdue_tasks = []
    due_today_tasks = []
    upcoming_tasks = []
    no_deadline_tasks = []
    completed_tasks = []

    for t in tasks:
        if t.get("completed"):
            completed_tasks.append(t)
            continue
        dl = str(t.get("deadline", "")).split("T")[0].strip()
        if not dl:
            no_deadline_tasks.append(t)
        elif dl < curr_date:
            try:
                d_dl = datetime.strptime(dl, "%Y-%m-%d").date()
                d_curr = datetime.strptime(curr_date, "%Y-%m-%d").date()
                days_overdue = (d_curr - d_dl).days
            except Exception:
                days_overdue = 1
            t_copy = dict(t)
            t_copy["days_overdue"] = days_overdue
            overdue_tasks.append(t_copy)
        elif dl == curr_date:
            due_today_tasks.append(t)
        else:
            try:
                d_dl = datetime.strptime(dl, "%Y-%m-%d").date()
                d_curr = datetime.strptime(curr_date, "%Y-%m-%d").date()
                days_left = (d_dl - d_curr).days
                day_name = d_dl.strftime("%A")
            except Exception:
                days_left = 1
                day_name = ""
            t_copy = dict(t)
            t_copy["days_left"] = days_left
            t_copy["day_name"] = day_name
            upcoming_tasks.append(t_copy)

    overdue_tasks.sort(key=lambda t: t.get("deadline", ""))
    due_today_tasks.sort(key=lambda t: t.get("priority") == "high", reverse=True)
    upcoming_tasks.sort(key=lambda t: t.get("deadline", ""))

    # Upcoming exams
    subjects = ctx.get("academic", {}).get("subjects", [])
    upcoming_exams = []
    for s in subjects:
        ex_d = str(s.get("examDate", "")).split("T")[0].strip()
        if ex_d:
            try:
                ex_date_obj = datetime.strptime(ex_d, "%Y-%m-%d").date()
                curr_date_obj = datetime.strptime(curr_date, "%Y-%m-%d").date()
                diff_days = (ex_date_obj - curr_date_obj).days
                if diff_days >= 0:
                    upcoming_exams.append({
                        "subject": s,
                        "name": s.get("name"),
                        "examDate": ex_d,
                        "examTime": s.get("examTime", ""),
                        "days_remaining": diff_days,
                        "day_name": ex_date_obj.strftime("%A"),
                        "is_today": diff_days == 0
                    })
            except Exception:
                pass
    upcoming_exams.sort(key=lambda x: x["days_remaining"])

    return {
        "curr_date": curr_date,
        "curr_time": curr_time,
        "curr_day": curr_day,
        "curr_tz": curr_tz,
        "is_holiday": is_holiday,
        "holiday_reason": holiday_reason,
        "is_working_day": is_working_day,
        "routine": routine,
        "in_college_hours": in_college_hours,
        "before_college": before_college,
        "after_college": after_college,
        "is_night": is_night,
        "current_event": current_event,
        "next_event": next_event,
        "next_future_event": next_future_event,
        "completed_events": completed_events,
        "in_progress_events": in_progress_events,
        "upcoming_events": upcoming_events,
        "all_day_events": all_day_events,
        "free_minutes": free_minutes,
        "free_until_desc": free_until_desc,
        "overdue_tasks": overdue_tasks,
        "due_today_tasks": due_today_tasks,
        "upcoming_tasks": upcoming_tasks,
        "no_deadline_tasks": no_deadline_tasks,
        "completed_tasks": completed_tasks,
        "upcoming_exams": upcoming_exams
    }
