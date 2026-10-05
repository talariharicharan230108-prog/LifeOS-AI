import os
import re
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple

def get_current_datetime(timezone_str: Optional[str] = None) -> Dict[str, Any]:
    tz = None
    if timezone_str:
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(timezone_str)
        except Exception:
            pass
    if tz is None:
        env_tz = os.getenv("LIFEOS_TIMEZONE")
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
    m = minutes % 1440
    h = m // 60
    mins = m % 60
    return f"{h:02d}:{mins:02d}"

def format_duration(minutes: int) -> str:
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

def format_time_12h(time_str: str) -> str:
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

def evaluate_event_status(event: Dict[str, Any], curr_time_str: str) -> Dict[str, Any]:
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
    today_info = ctx.get("today", {})
    curr_date = today_info.get("date")
    curr_time = today_info.get("time")
    curr_day = today_info.get("dayOfWeek")
    curr_tz = today_info.get("timezone")
    is_holiday = today_info.get("isHoliday")
    holiday_reason = today_info.get("holidayReason")

    routine = ctx.get("routine", {})
    wake_time = routine.get("wakeTime", "07:00")
    sleep_time = routine.get("sleepTime", "23:00")
    college_start = routine.get("collegeStart", "09:00")
    college_end = routine.get("collegeEnd", "16:00")
    working_days = ctx.get("workingDays", [])
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

    # Future events after today
    future_events = [e for e in all_events if e.get("date") and e.get("date") > curr_date]
    future_events.sort(key=lambda x: (x.get("date", ""), x.get("startTime", "")))
    next_future_event = future_events[0] if future_events else None

    # Free time
    if current_event:
        free_minutes = 0
        free_until_desc = f"until {current_event['end']} ({current_event['event'].get('title')})"
    elif in_college_hours:
        free_minutes = 0
        free_until_desc = f"until college ends at {college_end}"
    elif next_event:
        free_minutes = next_event["minutes_until"]
        free_until_desc = f"before your next scheduled event, **{next_event['event'].get('title')}** at {next_event['start']}"
    elif before_college:
        free_minutes = c_start_m - curr_m
        free_until_desc = f"before college starts at {college_start}"
    elif curr_m < sleep_m:
        free_minutes = sleep_m - curr_m
        free_until_desc = f"before your routine sleep time ({sleep_time})"
    else:
        free_minutes = 0
        free_until_desc = f"for tonight (past your routine sleep time of {sleep_time})"

    # Task status categorization
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
            overdue_tasks.append(t)
        elif dl == curr_date:
            due_today_tasks.append(t)
        else:
            upcoming_tasks.append(t)

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

print("Time analysis loaded successfully.")
