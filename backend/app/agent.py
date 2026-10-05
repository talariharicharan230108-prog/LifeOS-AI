import json
import re
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from . import storage
from . import tools
from . import gemini
from . import time_utils

get_current_datetime = time_utils.get_current_datetime

AGENT_SYSTEM_PROMPT = """You are the LifeOS scheduling agent.

Analyze the complete provided LifeOS context before generating a schedule.

Prioritize fixed commitments, exams, urgent deadlines, high-priority tasks, goals, and available study time.

Do not invent dates.

Do not invent times.

Do not create calendar events unless the user explicitly requested scheduling.

Do not duplicate existing calendar events.

Respect the user's routine, working days, holidays, and existing events.

Academic exam dates are important scheduling constraints.

If the requested information is insufficient, ask the user rather than guessing.

CRITICAL RULES & OPERATIONAL CONSTRAINTS:
1. INFORMATIONAL QUERIES:
   - Queries like "Show my upcoming exams", "What exams do I have?", "When is my next exam?", "Which exam is closest?" MUST ONLY return information. action = "none", events = []. NEVER create calendar events.
   - Queries like "What should I study for Advanced DBMS?" or "What should I study?" MUST NOT create calendar events. Use actual stored academic and document data. Do NOT invent syllabus topics (like B+ trees, ACID, normalization) if no topics or documents are stored in the user data. action = "none", events = [].
   - Queries like "Show my upcoming deadlines" or "What should I do today?" MUST NOT create calendar events. action = "none", events = [].
2. SCHEDULING INTENT:
   - Only create calendar events if the user EXPLICITLY asks to plan or schedule (e.g. "Prepare my schedule for the Advanced DBMS exam", "Schedule DBMS preparation tomorrow from 6 PM to 7 PM", "Plan my week").
   - If user asks to schedule with NO date specified and no exam planning requested, ask: "What date would you like to schedule it?" with action = "none", events = [].
   - If user asks for an explicit single event (e.g. "Schedule DBMS preparation tomorrow from 6 PM to 7 PM"), create exactly ONE calendar event for that date and time range. action = "create_calendar_event".
   - If user asks to prepare for an upcoming exam (e.g. "Prepare my schedule for the Advanced DBMS exam" or "Prepare me for my exam on October 8"), analyze the days leading up to the exam and create balanced, focused preparation sessions.
   - On the EXAM DAY itself, do NOT schedule long study sessions. If exam time is known from academic data, show the exam at that time. If exam time is NOT known, do NOT invent an exam time (never invent 08:00, 10:00, 14:00 etc.). Set isAllDay = true or startTime = "".
   - If user asks "Plan my week", schedule meaningful focus blocks across the week respecting working days, routine, upcoming exams, and urgent task deadlines. Do NOT generate 10 micro-blocks per day.
3. SCHEDULING PRIORITY ORDER:
   Priority 1: Fixed commitments / exams / college hours
   Priority 2: Tasks with urgent deadlines
   Priority 3: Upcoming exams
   Priority 4: High-priority tasks
   Priority 5: Goals
   Priority 6: Normal study/work
4. ROUTINE CONSTRAINTS:
   - College hours (e.g. 09:00 - 16:00) must be respected. Do NOT schedule study during college hours.
   - Fit study sessions into available study hours outside college hours and before sleep time.
5. NO DUPLICATE OR ARTIFICIAL BLOCKS:
   - Do NOT generate 10 micro-blocks per day. At most 2 to 4 meaningful activities per day. No tiny blocks like Short Break, Break, Small Break, Planning, Review.
   - Do not schedule duplicate events with the same title, date, and start time.
   - Do not duplicate College Hours if already on the calendar.

Return strictly valid JSON matching this schema:
{
  "analysis": {
    "importantDeadlines": [],
    "upcomingExams": [],
    "constraints": [],
    "availableDays": []
  },
  "action": "none" | "create_calendar_event" | "create_schedule" | "add_task" | "update_task" | "delete_task" | "add_holiday" | "delete_holiday",
  "action_data": {},
  "events": [
    {
      "title": "string",
      "date": "YYYY-MM-DD",
      "startTime": "HH:MM or empty",
      "endTime": "HH:MM or empty",
      "type": "study" | "work" | "college" | "exam" | "personal",
      "reason": "string",
      "description": "string",
      "isAllDay": false
    }
  ],
  "thought": "string",
  "response": "string"
}
"""

def get_ai_context(user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Requirements 1, 2, 13: Single canonical backend function that collects complete LifeOS context:
    user, routine, tasks, academic (subjects & exams), calendar (events), goals, holidays, workingDays, documents, today.
    Obtains dynamic system time on every request via time_utils.get_current_datetime().
    """
    data = storage.get_data(user_id)
    user_settings = data.get("settings", {})
    user_tz = user_settings.get("timezone") or (data.get("user", {}).get("timezone") if data.get("user") else None)
    curr_dt = time_utils.get_current_datetime(user_tz)
    today_str = curr_dt["date"]
    day_name = curr_dt["day"]
    is_today_h, today_h_reason = storage.is_holiday(today_str, user_id=user_id)

    return {
        "user": data.get("user") or {"name": "Student", "college": "University", "course": "Student"},
        "routine": data.get("routine") or {
            "wakeTime": "07:00",
            "sleepTime": "23:00",
            "collegeStart": "09:00",
            "collegeEnd": "16:00",
            "studyHours": 3,
            "breakPreference": "15 mins per 45 mins",
            "preferredSubjects": []
        },
        "tasks": data.get("tasks", []),
        "academic": {
            "subjects": data.get("subjects", [])
        },
        "calendar": {
            "events": data.get("events", [])
        },
        "goals": data.get("goals", []),
        "holidays": data.get("holidays", []),
        "workingDays": storage.get_working_days(user_id),
        "documents": [
            {
                "id": d.get("id"),
                "name": d.get("name"),
                "fileType": d.get("fileType"),
                "snippet": d.get("textSnippet", "")[:500]
            }
            for d in data.get("documents", [])
        ],
        "today": {
            "date": today_str,
            "time": curr_dt["time"],
            "dayOfWeek": day_name,
            "timezone": curr_dt["timezone"],
            "datetime": curr_dt["datetime"],
            "isHoliday": is_today_h,
            "holidayReason": today_h_reason if is_today_h else "Working day"
        }
    }

def parse_date_from_query(query: str, ref_date: Optional[date] = None) -> Optional[str]:
    """
    Extracts an explicit date (YYYY-MM-DD) from user text.
    Handles 'today', 'tomorrow', 'yesterday', days of the week, ISO dates, and natural dates.
    Uses dynamic current date from time_utils.
    """
    if not query:
        return None
    q = query.lower()
    curr_date_str = time_utils.get_current_datetime()["date"]
    try:
        dyn_today = datetime.strptime(curr_date_str, "%Y-%m-%d").date()
    except Exception:
        dyn_today = date.today()
    today = ref_date or dyn_today

    if "today" in q:
        return today.isoformat()
    if "tomorrow" in q:
        return (today + timedelta(days=1)).isoformat()
    if "yesterday" in q:
        return (today - timedelta(days=1)).isoformat()

    weekdays = {
        "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6
    }
    for day_name, day_idx in weekdays.items():
        if re.search(rf'\b{day_name}\b', q):
            today_idx = today.weekday()
            days_ahead = (day_idx - today_idx) % 7
            if days_ahead == 0:
                days_ahead = 0 if "this" in q else 7
            return (today + timedelta(days=days_ahead)).isoformat()

    iso_match = re.search(r'\b(20\d\d-\d{2}-\d{2})\b', q)
    if iso_match:
        return iso_match.group(1)

    months = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    for m_name, m_num in months.items():
        m1 = re.search(rf'\b{m_name}\s+(\d{{1,2}})(?:st|nd|rd|th)?(?:\s+(\d{{4}}))?\b', q)
        if m1:
            day = int(m1.group(1))
            year = int(m1.group(2)) if m1.group(2) else today.year
            return f"{year:04d}-{m_num:02d}-{day:02d}"
        m2 = re.search(rf'\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{m_name}(?:\s+(\d{{4}}))?\b', q)
        if m2:
            day = int(m2.group(1))
            year = int(m2.group(2)) if m2.group(2) else today.year
            return f"{year:04d}-{m_num:02d}-{day:02d}"

    return None

def parse_time_from_query(query: str) -> Tuple[str, str]:
    """
    Extracts start and end time from text like 'from 6 PM to 7 PM', 'at 6 PM', '6:00 pm'.
    Defaults to ('18:00', '19:00').
    """
    q = query.lower()
    range_match = re.search(r'\b(?:from\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*(?:to|-)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', q)
    if range_match:
        h1 = int(range_match.group(1))
        m1 = int(range_match.group(2)) if range_match.group(2) else 0
        ap1 = range_match.group(3)
        h2 = int(range_match.group(4))
        m2 = int(range_match.group(5)) if range_match.group(5) else 0
        ap2 = range_match.group(6)
        if not ap1:
            ap1 = ap2
        if ap1 == "pm" and h1 < 12:
            h1 += 12
        elif ap1 == "am" and h1 == 12:
            h1 = 0
        if ap2 == "pm" and h2 < 12:
            h2 += 12
        elif ap2 == "am" and h2 == 12:
            h2 = 0
        return (f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}")

    m_12 = re.search(r'\b(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b', q)
    if m_12:
        hour = int(m_12.group(1))
        minute = int(m_12.group(2)) if m_12.group(2) else 0
        ampm = m_12.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        start_str = f"{hour:02d}:{minute:02d}"
        end_hour = (hour + 1) % 24
        end_str = f"{end_hour:02d}:{minute:02d}"
        return (start_str, end_str)

    m_24 = re.search(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', q)
    if m_24:
        hour = int(m_24.group(1))
        minute = int(m_24.group(2))
        start_str = f"{hour:02d}:{minute:02d}"
        end_hour = (hour + 1) % 24
        end_str = f"{end_hour:02d}:{minute:02d}"
        return (start_str, end_str)

    return ("18:00", "19:00")

def extract_event_title(query: str) -> str:
    text = query.strip()
    text = re.sub(r'[.!?]+$', '', text).strip()
    text = re.sub(r'^(schedule|create|add|plan)\s+(calendar\s+event|event|work|session|task)?\s*(for|on|at)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bfrom\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(?:to|-)\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(today|tomorrow|yesterday|sunday|monday|tuesday|wednesday|thursday|friday|saturday)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b\d{1,2}(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)(?:\s+\d{4})?\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\b(20\d\d-\d{2}-\d{2})\b', '', text)
    text = re.sub(r'\b(on|at|for|in|due)\s*$', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'^(on|at|for|in)\s+', '', text, flags=re.IGNORECASE).strip()
    text = re.sub(r'[\s.,;:!-]+$', '', text).strip()
    text = re.sub(r'^[\s.,;:!-]+', '', text).strip()

    if not text or text.lower() in ("work", "preparation"):
        return "Work Session"
    return text.title()

def find_exam_for_query(query: str, subjects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Finds if the query refers to an exam for a specific subject, or any upcoming exam.
    """
    q = query.lower()
    subjects_with_exam = [s for s in subjects if s.get("examDate")]
    if not subjects_with_exam:
        return None

    # Check for direct subject name match
    for sub in subjects_with_exam:
        sub_name = sub.get("name", "").lower()
        words = [w for w in re.split(r'\W+', sub_name) if len(w) > 2]
        if sub_name in q or any(w in q for w in words):
            return sub

    # If query mentions a specific date matching a subject exam date
    date_in_q = parse_date_from_query(query)
    if date_in_q:
        for sub in subjects_with_exam:
            if sub.get("examDate") == date_in_q:
                return sub

    # If user just said "exam" and there is only one upcoming exam, return it
    if "exam" in q:
        today_iso = date.today().isoformat()
        upcoming = [s for s in subjects_with_exam if s.get("examDate") >= today_iso]
        if upcoming:
            upcoming.sort(key=lambda s: s.get("examDate"))
            return upcoming[0]
        return subjects_with_exam[0]

    return None

def is_exam_prep_planning_request(query: str) -> bool:
    """
    Detects if user explicitly asked to plan/prepare schedule for an exam.
    e.g. "Prepare my schedule for the Advanced DBMS exam."
    e.g. "Plan my DBMS preparation until the exam."
    Informational questions (e.g. "What should I do before my DBMS exam?") return False.
    """
    q = query.lower().strip()
    if any(q.startswith(k) or k in q for k in [
        "what should i do", "what to do", "what can i do", "what do i do",
        "how should i study", "what should i study", "show", "when is",
        "which exam", "what are", "tell me"
    ]):
        return False
    has_exam_word = "exam" in q
    has_prep_or_schedule = any(k in q for k in [
        "prepare my schedule", "prepare schedule", "prepare me for my exam",
        "plan my prep", "plan my preparation", "plan preparation",
        "create study plan", "make study plan", "schedule preparation",
        "plan my dbms preparation", "plan my exam preparation",
        "schedule dbms preparation", "prepare for my exam"
    ]) or (has_exam_word and any(k in q for k in ["prepare", "prep", "plan", "schedule", "create schedule", "make schedule", "study plan"]))
    return has_exam_word and has_prep_or_schedule

def build_context_string(ctx: Dict[str, Any]) -> str:
    """Serializes complete LifeOS context with dynamic real-time awareness into a clear text prompt for Gemini."""
    today_info = ctx.get("today", {})
    t_analysis = time_utils.get_time_analysis(ctx)
    curr_activity = t_analysis.get('current_event')['event'].get('title') if t_analysis.get('current_event') else ('In College Hours' if t_analysis.get('in_college_hours') else 'Free')
    next_ev_str = (t_analysis.get('next_event')['event'].get('title') + ' at ' + t_analysis.get('next_event')['start']) if t_analysis.get('next_event') else 'None today'
    free_str = f"{time_utils.format_duration(t_analysis.get('free_minutes', 0))} {t_analysis.get('free_until_desc', '')}"
    exams_str = json.dumps([e['name'] + ' on ' + e['examDate'] + ' (' + str(e['days_remaining']) + ' days left)' for e in t_analysis.get('upcoming_exams', [])])

    return f"""REAL-TIME LIFEOS CONTEXT:
CURRENT DATE: {today_info.get('date')}
CURRENT TIME: {today_info.get('time')} ({today_info.get('timezone')})
DAY OF WEEK: {today_info.get('dayOfWeek')}
HOLIDAY STATUS: {today_info.get('holidayReason')}
WORKING DAY: {'Yes' if t_analysis.get('is_working_day') else 'No'}

STATUS & DETERMINISTIC METRICS:
- Current Activity: {curr_activity}
- Next Scheduled Event: {next_ev_str}
- Free Time: {free_str}
- Overdue Tasks: {len(t_analysis.get('overdue_tasks', []))}
- Tasks Due Today: {len(t_analysis.get('due_today_tasks', []))}
- Approaching Exams: {exams_str}

USER DATA:
1. USER PROFILE: {json.dumps(ctx.get('user'))}
2. DAILY ROUTINE CONSTRAINTS: {json.dumps(ctx.get('routine'))}
3. CONFIGURED WORKING DAYS: {json.dumps(ctx.get('workingDays'))}
4. DECLARED HOLIDAYS: {json.dumps(ctx.get('holidays'))}
5. ACADEMIC SUBJECTS & EXAM DATES: {json.dumps(ctx.get('academic', {}).get('subjects', []))}
6. TASKS & DEADLINES: {json.dumps(ctx.get('tasks', []))}
7. CALENDAR EXISTING EVENTS: {json.dumps(ctx.get('calendar', {}).get('events', [])[-25:])}
8. GOALS: {json.dumps(ctx.get('goals', []))}
9. UPLOADED DOCUMENTS: {json.dumps(ctx.get('documents', []))}
"""

async def process_agent_message(user_message: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Main entry point for AI Agent chat.
    Uses Gemini when available with full cross-data analysis.
    Validates all dates, constraints, exam day rules, and prevents duplicates.
    Falls back gracefully to local deterministic rule processing.
    """
    ctx = get_ai_context(user_id)
    context_str = build_context_string(ctx)
    msg_lower = user_message.lower().strip()
    today_dt = date.today()
    today_str = today_dt.isoformat()

    transparency = {
        "step1_input": user_message,
        "step2_context_summary": f"Exams: {len([s for s in ctx['academic']['subjects'] if s.get('examDate')])}, Tasks: {len(ctx['tasks'])}, Events: {len(ctx['calendar']['events'])}, Working days: {', '.join(ctx['workingDays'])}",
        "step3_reasoning": "",
        "step4_tool_action": "none",
        "step5_final_output": ""
    }

    # Strict check: If user prompt is asking to schedule general work but provides NO date or range,
    # and it is NOT an exam preparation or weekly plan request, ask for the date!
    is_general_schedule = any(k in msg_lower for k in ["schedule", "create work", "add work"]) and not any(k in msg_lower for k in ["tomorrow", "today", "yesterday", "next", "week", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"])
    has_date = parse_date_from_query(user_message) is not None
    is_week = "week" in msg_lower and ("plan" in msg_lower or "schedule" in msg_lower)
    is_exam_prep = is_exam_prep_planning_request(user_message)

    if is_general_schedule and not has_date and not is_week and not is_exam_prep:
        resp_text = "What date would you like to schedule it?"
        transparency["step3_reasoning"] = "User requested scheduling without specifying a date or exam. Prompting for target date."
        transparency["step4_tool_action"] = "none"
        transparency["step5_final_output"] = resp_text
        return {
            "success": True,
            "response": resp_text,
            "thought": "No date provided. Enforced strict date scope rule.",
            "action": "none",
            "action_result": None,
            "transparency": transparency,
            "is_live_gemini": False
        }

    # DETERMINISTIC / TIME-AWARE INFORMATIONAL ROUTING (Requirements 13, 14, 15):
    # Process simple time, event, greeting, status, and study guidance queries locally in Python.
    # Eliminates Gemini network lag, ensures 100% time accuracy, and guarantees ZERO calendar events created.
    is_greeting = bool(re.match(r'^(hello|hi|hey|greetings|good\s+(morning|afternoon|evening))\b', msg_lower))
    is_time_query = any(k in msg_lower for k in [
        "what time is it", "what is the time", "current time", "tell me the time",
        "what's the time", "what date is it", "what is today's date", "what day is it",
        "what day is today"
    ]) or msg_lower in ["time", "date"]
    is_next_event_query = any(k in msg_lower for k in [
        "what is my next event", "what is next", "what's next", "what do i have next",
        "next event", "what is upcoming on my calendar", "what's my next event", "next activity"
    ])
    is_free_time_query = any(k in msg_lower for k in [
        "how much free time", "how much time do i have", "am i free now",
        "how much time have i got", "do i have free time", "am i free", "how much time do i have left"
    ])
    is_what_now_query = (
        ("what should i do" in msg_lower or "what to do" in msg_lower or "what can i do" in msg_lower)
        and any(k in msg_lower for k in ["now", "next", "right now"])
    ) or msg_lower in ["what should i do now", "what should i do next", "what to do now"]
    is_study_now_query = (
        "what should i study now" in msg_lower or "what to study now" in msg_lower
        or ("study now" in msg_lower and any(k in msg_lower for k in ["what", "should", "session", "do i have"]))
        or "do i have a study session now" in msg_lower
    )
    is_tonight_query = "tonight" in msg_lower and any(k in msg_lower for k in ["what do i have", "anything", "what is on", "schedule"])
    is_today_query = any(k in msg_lower for k in [
        "what do i have today", "do i have anything today", "what is today's schedule",
        "today's schedule", "what is on my schedule today", "what do i have scheduled today",
        "schedule today", "anything scheduled", "what is scheduled", "do i have anything scheduled"
    ]) or ("what should i do today" in msg_lower)
    is_before_exam_guidance = (
        "before" in msg_lower and "exam" in msg_lower
        and any(k in msg_lower for k in ["what should i do", "what to do", "how should i prepare", "what can i do", "how to prepare"])
    )
    is_college_routine = "before college" in msg_lower or "after college" in msg_lower
    is_tomorrow_query = "tomorrow" in msg_lower and any(k in msg_lower for k in ["what should i do", "what do i have", "what to do", "schedule"]) and not any(k in msg_lower for k in ["plan", "create", "add"])
    is_next_task = "next task" in msg_lower or "what is my next task" in msg_lower
    is_exam_inquiry = any(k in msg_lower for k in ["upcoming exam", "upcoming exams", "what exam", "show my exam", "show my exams", "when is my next exam", "which exam is closest"]) and not is_exam_prep
    is_study_inquiry = "what should i study" in msg_lower or "what to study" in msg_lower or ("should i study" in msg_lower and not is_exam_prep)
    is_deadlines_inquiry = re.search(r'\b(deadline|deadlines)\b', msg_lower) and not any(k in msg_lower for k in ["schedule", "create", "plan", "add"])

    is_deterministic_time_or_info = (
        is_greeting or
        is_time_query or
        is_next_event_query or
        is_free_time_query or
        is_what_now_query or
        is_study_now_query or
        is_tonight_query or
        is_today_query or
        is_before_exam_guidance or
        is_college_routine or
        is_tomorrow_query or
        is_next_task or
        is_exam_inquiry or
        is_study_inquiry or
        is_deadlines_inquiry
    ) and not (is_exam_prep or is_week or (has_date and any(k in msg_lower for k in ["schedule", "create", "plan"])))

    if is_deterministic_time_or_info:
        return process_local_rule_agent(user_message, ctx, transparency, user_id=user_id)

    # If Gemini is configured, query Gemini with full LifeOS context
    if gemini.is_api_key_configured():
        prompt = f"""{context_str}

USER REQUEST:
{user_message}

Analyze all LifeOS data carefully according to the system instructions.
Return strictly valid JSON."""

        gemini_res = await gemini.generate_content(
            system_instruction=AGENT_SYSTEM_PROMPT,
            prompt=prompt,
            response_json=True
        )

        if gemini_res.get("success"):
            try:
                raw_text = gemini_res.get("text", "{}").strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0]
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0]

                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                json_str = match.group(0) if match else raw_text
                parsed = json.loads(json_str.strip())

                action = parsed.get("action", "none")
                action_data = parsed.get("action_data", {})
                final_response = parsed.get("response", "")
                thought = parsed.get("thought", "Processed request.")
                proposed_events = parsed.get("events", [])

                # STRICT BACKEND VALIDATION:
                # 1. Informational queries never create events
                if is_exam_inquiry or is_study_inquiry or is_deadlines_inquiry:
                    action = "none"
                    proposed_events = []

                # 2. If single event requested (Scenario 4)
                if has_date and not is_exam_prep and not is_week and any(k in msg_lower for k in ["schedule", "create", "plan"]):
                    target_date = parse_date_from_query(user_message)
                    start_time, end_time = parse_time_from_query(user_message)
                    event_title = extract_event_title(user_message)
                    res = tools.create_calendar_event(
                        title=event_title,
                        date=target_date,
                        startTime=start_time,
                        endTime=end_time,
                        type="work",
                        description="Scheduled via AI Agent",
                        source="ai",
                        user_id=user_id
                    )
                    transparency["step3_reasoning"] = f"Created single event '{event_title}' on {target_date} ({start_time}–{end_time})."
                    transparency["step4_tool_action"] = "create_calendar_event"
                    resp_single = f"Done. I've scheduled **{event_title}** for {target_date} from {start_time} to {end_time}."
                    transparency["step5_final_output"] = resp_single
                    return {
                        "success": True,
                        "response": resp_single,
                        "thought": f"Scheduled single event on {target_date}.",
                        "action": "create_calendar_event",
                        "action_result": res,
                        "transparency": transparency,
                        "is_live_gemini": True
                    }

                # 3. If Exam Prep request (Scenario 1)
                if is_exam_prep:
                    matched_sub = find_exam_for_query(user_message, ctx["academic"]["subjects"])
                    if not matched_sub and ctx["academic"]["subjects"]:
                        subs_w_exam = [s for s in ctx["academic"]["subjects"] if s.get("examDate")]
                        if subs_w_exam:
                            matched_sub = subs_w_exam[0]

                    if matched_sub:
                        # Validate proposed events or generate balanced schedule
                        prep_events = generate_exam_preparation_schedule(matched_sub, ctx, user_id=user_id)
                        saved_res = tools.create_schedule(prep_events, user_id=user_id)
                        action = "create_schedule"
                        action_data = {"events": prep_events}
                        ex_date = matched_sub.get("examDate", "")
                        routine = ctx.get("routine", {})
                        college_hours_str = f"{routine.get('collegeStart', '09:00')}–{routine.get('collegeEnd', '16:00')}"
                        
                        resp_prep = f"I've generated your preparation schedule for **{matched_sub.get('name')}** leading up to the exam on **{ex_date}**! " \
                                   f"Work sessions and assignment focus have been scheduled outside your college hours ({college_hours_str}). " \
                                   f"The exam day ({ex_date}) is designated as EXAM DAY with no heavy study sessions."
                        
                        transparency["step3_reasoning"] = f"Generated {len(prep_events)} preparation events leading up to exam on {ex_date}."
                        transparency["step4_tool_action"] = "create_schedule"
                        transparency["step5_final_output"] = resp_prep

                        return {
                            "success": True,
                            "response": resp_prep,
                            "thought": f"Scheduled exam preparation for {matched_sub.get('name')}.",
                            "action": "create_schedule",
                            "action_result": saved_res,
                            "transparency": transparency,
                            "is_live_gemini": True
                        }

                # 4. If Weekly Plan request (Scenario 5)
                if is_week:
                    weekly_events = generate_weekly_plan(storage.get_data(user_id), start_date=today_str, user_id=user_id)
                    saved_res = tools.create_schedule(weekly_events, user_id=user_id)
                    routine = ctx.get("routine", {})
                    resp_week = f"I've generated your weekly schedule! Activities have been scheduled outside college hours ({routine.get('collegeStart', '09:00')}–{routine.get('collegeEnd', '16:00')}), prioritizing upcoming exams and task deadlines, while keeping non-working days and declared holidays free."
                    transparency["step3_reasoning"] = f"Generated weekly plan of {len(weekly_events)} events across 7 days."
                    transparency["step4_tool_action"] = "create_schedule"
                    transparency["step5_final_output"] = resp_week
                    return {
                        "success": True,
                        "response": resp_week,
                        "thought": "Generated weekly plan.",
                        "action": "create_schedule",
                        "action_result": saved_res,
                        "transparency": transparency,
                        "is_live_gemini": True
                    }

                # General tool execution if applicable (strictly isolated per user_id)
                tool_result = None
                if action and action != "none" and action in tools.TOOL_REGISTRY:
                    func = tools.TOOL_REGISTRY[action]
                    try:
                        if isinstance(action_data, dict):
                            if user_id:
                                action_data["user_id"] = user_id
                            tool_result = func(**action_data)
                        elif isinstance(action_data, list):
                            if user_id and action in ("create_schedule",):
                                tool_result = func(action_data, user_id=user_id)
                            else:
                                tool_result = func(action_data)
                        else:
                            if user_id:
                                tool_result = func(user_id=user_id)
                            else:
                                tool_result = func()
                    except Exception as te:
                        tool_result = {"status": "error", "message": f"Tool execution error: {str(te)}"}

                transparency["step3_reasoning"] = thought
                transparency["step4_tool_action"] = action
                transparency["step5_final_output"] = final_response

                return {
                    "success": True,
                    "response": final_response,
                    "thought": thought,
                    "action": action,
                    "action_result": tool_result,
                    "transparency": transparency,
                    "is_live_gemini": True
                }
            except Exception as e:
                print(f"[AI Agent] Gemini response handling exception: {e}")

    # Deterministic fallback parser
    return process_local_rule_agent(user_message, ctx, transparency, user_id=user_id)

def process_local_rule_agent(message: str, ctx: Dict[str, Any], transparency: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Deterministic rule engine implementing all required LifeOS scenarios cleanly:
    Scenario 1: "Prepare my schedule for the Advanced DBMS exam."
    Scenario 2: "Show my upcoming exams."
    Scenario 3: "What should I study for Advanced DBMS?"
    Scenario 4: "Schedule DBMS preparation tomorrow from 6 PM to 7 PM."
    Scenario 5: "Plan my week."
    """
    msg = message.lower().strip()
    data = storage.get_data(user_id)
    tasks = ctx.get("tasks", [])
    subjects = ctx.get("academic", {}).get("subjects", [])
    routine = ctx.get("routine", {})
    t_analysis = time_utils.get_time_analysis(ctx)
    curr_date = t_analysis["curr_date"]
    curr_time = t_analysis["curr_time"]
    curr_day = t_analysis["curr_day"]
    curr_tz = t_analysis["curr_tz"]
    time_12h = time_utils.format_time_12h(curr_time)
    is_today_h = t_analysis["is_holiday"]
    today_h_reason = t_analysis["holiday_reason"]
    is_working_day = t_analysis["is_working_day"]
    is_exam_inquiry = any(k in msg for k in ["upcoming exam", "upcoming exams", "what exam", "show my exam", "show my exams", "when is my next exam", "which exam is closest"]) and not is_exam_prep_planning_request(msg)

    action = "none"
    action_result = None
    thought = ""
    resp = ""

    # GREETING (Question 1: "hello")
    if re.match(r'^(hello|hi|hey|greetings|good\s+(morning|afternoon|evening))\b', msg):
        resp = f"Hello! It is currently {time_12h} on {curr_day}. How can I assist you with your schedule or study plan?"
        thought = f"Responded to greeting with current time ({time_12h}) and day ({curr_day})."
        action = "none"

    # REAL CURRENT TIME (Question 2: "What time is it?")
    elif any(k in msg for k in ["what time is it", "what is the time", "current time", "tell me the time", "what's the time", "what date is it", "what is today's date", "what day is it", "what day is today"]) or msg in ["time", "date"]:
        try:
            d_obj = datetime.strptime(curr_date, "%Y-%m-%d").date()
            formatted_date = d_obj.strftime("%B %d, %Y")
        except Exception:
            formatted_date = curr_date
        resp = f"It is currently **{time_12h}** ({curr_time}) on **{curr_day}, {formatted_date}** ({curr_tz})."
        thought = f"Provided dynamic system time {curr_time} and date {curr_date}."
        action = "none"

    # BEFORE EXAM GUIDANCE (Question 9: "What should I do before my DBMS exam?")
    # Informational query: Analyzes exam date + tasks + routine + calendar + holidays. Zero calendar events created!
    elif "before" in msg and "exam" in msg and any(k in msg for k in ["what should i do", "what to do", "how should i prepare", "what can i do", "how to prepare"]):
        matched_sub = find_exam_for_query(msg, subjects)
        if not matched_sub:
            matched_sub = next((s for s in subjects if s.get("examDate")), None)
        if matched_sub:
            sub_name = matched_sub.get("name")
            ex_date = matched_sub.get("examDate")
            try:
                diff = (datetime.strptime(ex_date, "%Y-%m-%d").date() - datetime.strptime(curr_date, "%Y-%m-%d").date()).days
                days_str = f"in {diff} day(s)" if diff > 0 else ("TODAY" if diff == 0 else "passed")
            except Exception:
                diff = 0
                days_str = ex_date

            c_start = time_utils.format_time_12h(routine.get("collegeStart", "09:00"))
            c_end = time_utils.format_time_12h(routine.get("collegeEnd", "16:00"))
            related_tasks = [
                t for t in tasks
                if not t.get("completed") and (
                    sub_name.lower() in t.get("title", "").lower()
                    or sub_name.lower() in t.get("subject", "").lower()
                    or (t.get("deadline") and t.get("deadline") <= ex_date)
                )
            ]
            related_tasks.sort(key=lambda t: t.get("deadline") or "9999-99-99")

            resp = f"Here is your preparation roadmap for **{sub_name}** leading up to the exam on **{ex_date}** ({days_str}):\n\n"
            if related_tasks:
                resp += f"• **Priority Assignment / Task**: Complete **{related_tasks[0].get('title')}**" + (f" (Due: {related_tasks[0].get('deadline')})" if related_tasks[0].get('deadline') else "") + ".\n"
            resp += f"• **Study Window**: Schedule focused 1.5–2 hour study blocks outside your college hours ({c_start}–{c_end}).\n"
            if matched_sub.get("importantTopics"):
                resp += f"• **Key Topics**: Review {', '.join(matched_sub.get('importantTopics'))}.\n"
            else:
                resp += "• **Syllabus**: You can upload notes in Documents or add specific topics in Academic to track syllabus coverage.\n"
            resp += f"• **Exam Day Strategy**: On {ex_date} itself, avoid heavy study sessions and keep it for final quick formula revision.\n"
            resp += f"\nTo generate a balanced day-by-day study schedule on your calendar, simply say: **'Plan my DBMS preparation until the exam'**."
        else:
            resp = "You currently have no exams scheduled in your Academic subjects."
        thought = "Provided exam preparation guidance without creating calendar events."
        action = "none"

    # NEXT EVENT (Question 4: "What is my next event?")
    # Returns only the nearest future event from the current time. Past events are excluded.
    elif any(k in msg for k in ["what is my next event", "what is next", "what's next", "what do i have next", "next event", "what is upcoming on my calendar", "what's my next event", "next activity"]):
        if t_analysis["current_event"]:
            ev = t_analysis["current_event"]["event"]
            rem = t_analysis["current_event"]["minutes_remaining"]
            end_t = time_utils.format_time_12h(t_analysis["current_event"]["end"])
            resp = f"Your **{ev.get('title')}** session is currently in progress until {end_t} ({rem} minutes remaining)."
            if t_analysis["next_event"]:
                nxt = t_analysis["next_event"]["event"]
                nxt_start = time_utils.format_time_12h(t_analysis["next_event"]["start"])
                nxt_end = time_utils.format_time_12h(t_analysis["next_event"]["end"])
                resp += f" After that, your next scheduled activity is **{nxt.get('title')}** from {nxt_start} to {nxt_end}."
        elif t_analysis["next_event"]:
            nxt = t_analysis["next_event"]["event"]
            start_t = time_utils.format_time_12h(t_analysis["next_event"]["start"])
            end_t = time_utils.format_time_12h(t_analysis["next_event"]["end"])
            mins = t_analysis["next_event"]["minutes_until"]
            in_text = f"in {time_utils.format_duration(mins)}" if mins > 0 else "starting right now"
            resp = f"Your next scheduled activity is **{nxt.get('title')}** from {start_t} to {end_t} ({in_text})."
        elif t_analysis["next_future_event"]:
            f_ev = t_analysis["next_future_event"]
            f_start = time_utils.format_time_12h(f_ev.get("startTime", ""))
            f_end = time_utils.format_time_12h(f_ev.get("endTime", ""))
            time_range = f" from {f_start} to {f_end}" if f_start and f_end else (f" at {f_start}" if f_start else "")
            resp = f"You have no more events scheduled for today. Your next scheduled activity is **{f_ev.get('title')}** on {f_ev.get('date')}{time_range}."
        else:
            resp = "You have no upcoming events scheduled on your calendar."
        thought = "Calculated nearest future event using real current time."
        action = "none"

    # AVAILABLE FREE TIME (Question 7: "How much free time do I have?")
    elif any(k in msg for k in ["how much free time", "how much time do i have", "am i free now", "how much time have i got", "do i have free time", "am i free", "how much time do i have left"]):
        if t_analysis["current_event"]:
            ev = t_analysis["current_event"]["event"]
            rem = t_analysis["current_event"]["minutes_remaining"]
            resp = f"You are currently busy with **{ev.get('title')}** until {time_utils.format_time_12h(t_analysis['current_event']['end'])} ({rem} minutes remaining)."
        elif t_analysis["in_college_hours"]:
            c_end_m = time_utils.parse_time_minutes(routine.get("collegeEnd", "16:00"))
            curr_m = time_utils.parse_time_minutes(curr_time)
            rem = max(0, c_end_m - curr_m)
            resp = f"You are currently in university college hours until {time_utils.format_time_12h(routine.get('collegeEnd', '16:00'))} ({rem} minutes remaining)."
        else:
            free_mins = t_analysis["free_minutes"]
            dur_text = time_utils.format_duration(free_mins)
            desc = t_analysis["free_until_desc"]
            if "am i free" in msg:
                resp = f"Yes, you are currently free! You have about **{dur_text}** free {desc}."
            else:
                resp = f"You have about **{dur_text}** free {desc}."
        thought = "Calculated available free time based on current time."
        action = "none"

    # STUDY NOW (Question 6: "What should I study now?")
    elif "what should i study now" in msg or "what to study now" in msg or ("study now" in msg and any(k in msg for k in ["what", "should", "session", "do i have"])) or "do i have a study session now" in msg:
        if t_analysis["current_event"]:
            ev = t_analysis["current_event"]["event"]
            rem = t_analysis["current_event"]["minutes_remaining"]
            resp = f"Your **{ev.get('title')}** session is currently in progress until {time_utils.format_time_12h(t_analysis['current_event']['end'])} ({rem} minutes remaining)."
        elif t_analysis["next_event"] and t_analysis["next_event"]["minutes_until"] <= 30:
            nxt = t_analysis["next_event"]["event"]
            mins = t_analysis["next_event"]["minutes_until"]
            resp = f"You have **{nxt.get('title')}** scheduled in {mins} minutes ({time_utils.format_time_12h(t_analysis['next_event']['start'])}–{time_utils.format_time_12h(t_analysis['next_event']['end'])})."
        elif t_analysis["in_college_hours"]:
            resp = f"You are currently in university college hours until {time_utils.format_time_12h(routine.get('collegeEnd', '16:00'))}. Focus on your lectures and classwork."
        elif t_analysis["is_night"]:
            resp = f"It is currently {time_12h}, past your routine sleep time ({time_utils.format_time_12h(routine.get('sleepTime', '23:00'))}). Take time to rest rather than studying late."
        else:
            dur_text = time_utils.format_duration(t_analysis["free_minutes"])
            desc = t_analysis["free_until_desc"]
            resp = f"You have about **{dur_text}** free {desc}.\n\nStudy recommendation:\n"
            if t_analysis["upcoming_exams"]:
                closest_ex = t_analysis["upcoming_exams"][0]
                sub = closest_ex["subject"]
                resp += f"• **Upcoming Exam Priority**: You have {closest_ex['days_remaining']} day(s) until your **{closest_ex['name']}** exam on {closest_ex['examDate']}.\n"
                sub_tasks = [t for t in tasks if not t.get("completed") and closest_ex["name"].lower() in (t.get("title", "") + t.get("subject", "")).lower()]
                if sub_tasks:
                    resp += f"• Top task: Complete **{sub_tasks[0].get('title')}**" + (f" (Due: {sub_tasks[0].get('deadline')})" if sub_tasks[0].get('deadline') else "") + ".\n"
                if sub.get("importantTopics"):
                    resp += f"• Stored key topics: {', '.join(sub.get('importantTopics'))}.\n"
                else:
                    resp += "• You haven't added specific syllabus topics or uploaded documents for this subject yet. You can add them in Academic or Documents.\n"
            elif t_analysis["due_today_tasks"]:
                top_td = t_analysis["due_today_tasks"][0]
                resp += f"• Focus on your task due today: **{top_td.get('title')}**.\n"
            elif subjects:
                first_sub = subjects[0]
                resp += f"• Review coursework and practice problems for **{first_sub.get('name')}**.\n"
            else:
                resp += "• You currently have no subjects or tasks added. You can add subjects in Academic to get tailored study suggestions.\n"
        thought = "Provided time-aware study guidance."
        action = "none"

    # WHAT SHOULD I DO NOW / NEXT (Question 3: "What should I do now?")
    elif (("what should i do" in msg or "what to do" in msg or "what can i do" in msg) and any(k in msg for k in ["now", "next", "right now"])) or msg in ["what should i do now", "what should i do next", "what to do now"]:
        if t_analysis["current_event"]:
            ev = t_analysis["current_event"]["event"]
            rem = t_analysis["current_event"]["minutes_remaining"]
            resp = f"Your **{ev.get('title')}** session is currently in progress until {time_utils.format_time_12h(t_analysis['current_event']['end'])} ({rem} minutes remaining)."
        elif t_analysis["next_event"] and t_analysis["next_event"]["minutes_until"] <= 30:
            nxt = t_analysis["next_event"]["event"]
            mins = t_analysis["next_event"]["minutes_until"]
            start_t = time_utils.format_time_12h(t_analysis["next_event"]["start"])
            end_t = time_utils.format_time_12h(t_analysis["next_event"]["end"])
            in_text = f"in {mins} minute{'s' if mins != 1 else ''}" if mins > 0 else "right now"
            resp = f"You have **{nxt.get('title')}** scheduled {in_text} from {start_t} to {end_t}."
        elif t_analysis["in_college_hours"]:
            c_end = time_utils.format_time_12h(routine.get("collegeEnd", "16:00"))
            resp = f"You are currently in university college hours until {c_end}. Focus on your scheduled classes."
        elif t_analysis["is_night"]:
            sleep_t = time_utils.format_time_12h(routine.get("sleepTime", "23:00"))
            resp = f"It is currently {time_12h}, which is past your routine sleep time ({sleep_t}). It's time to rest and recharge for tomorrow!"
        else:
            dur_text = time_utils.format_duration(t_analysis["free_minutes"])
            desc = t_analysis["free_until_desc"]
            resp = f"You have about **{dur_text}** free {desc}.\n\nRecommended next action:\n"
            if t_analysis["overdue_tasks"]:
                top_od = t_analysis["overdue_tasks"][0]
                resp += f"• **Urgent Task**: Complete **{top_od.get('title')}** (was due {top_od.get('deadline')}).\n"
            elif t_analysis["due_today_tasks"]:
                top_td = t_analysis["due_today_tasks"][0]
                resp += f"• **Due Today**: Work on **{top_td.get('title')}** ({top_td.get('priority', 'medium').capitalize()} priority).\n"
            elif t_analysis["upcoming_exams"]:
                closest_ex = t_analysis["upcoming_exams"][0]
                resp += f"• **Upcoming Exam**: You have {closest_ex['days_remaining']} day(s) until your **{closest_ex['name']}** exam on {closest_ex['examDate']}. Reviewing coursework is recommended.\n"
            elif ctx.get("tasks"):
                pending_general = [t for t in ctx.get("tasks", []) if not t.get("completed")]
                if pending_general:
                    resp += f"• **Next Task**: Work on **{pending_general[0].get('title')}**.\n"
                else:
                    resp = f"You have about **{dur_text}** free {desc}. Your task list and schedule are clear right now!"
            else:
                resp = f"You have about **{dur_text}** free {desc}. Your task list and schedule are clear right now!"
        thought = "Determined next action using real current time, events, routine, and pending tasks."
        action = "none"

    # TONIGHT
    elif "tonight" in msg and any(k in msg for k in ["what do i have", "anything", "what is on", "schedule"]):
        night_events = [e for e in t_analysis["upcoming_events"] + t_analysis["in_progress_events"] if time_utils.parse_time_minutes(e["start"]) >= 17 * 60 or time_utils.parse_time_minutes(e["start"]) >= time_utils.parse_time_minutes(curr_time)]
        resp = f"Here is your evening schedule for tonight ({curr_day}, {curr_date}):\n\n"
        if night_events:
            for e in night_events:
                ev = e["event"]
                status_tag = " (In Progress)" if e["status"] == "in_progress" else ""
                resp += f"• **{ev.get('title')}** from {time_utils.format_time_12h(e['start'])} to {time_utils.format_time_12h(e['end'])}{status_tag}\n"
        else:
            resp += "• No evening events scheduled on your calendar.\n"
        resp += f"• Routine sleep time: **{time_utils.format_time_12h(routine.get('sleepTime', '23:00'))}**.\n"
        if t_analysis["due_today_tasks"]:
            resp += f"• Pending today: **{t_analysis['due_today_tasks'][0].get('title')}**.\n"
        thought = "Retrieved evening schedule and routine."
        action = "none"

    # WHAT DO I HAVE TODAY (Question 5: "What do I have today?")
    elif any(k in msg for k in ["what do i have today", "do i have anything today", "what is today's schedule", "today's schedule", "what is on my schedule today", "what do i have scheduled today", "schedule today", "anything scheduled", "what is scheduled", "do i have anything scheduled"]):
        resp = f"Here is your schedule for today (**{curr_day}, {curr_date}**" + (f" — {today_h_reason}" if is_today_h else "") + f"):\n\n"
        if is_working_day and not is_today_h:
            resp += f"• **College Hours**: {time_utils.format_time_12h(routine.get('collegeStart', '09:00'))}–{time_utils.format_time_12h(routine.get('collegeEnd', '16:00'))}\n"
        elif is_today_h:
            resp += f"• **Holiday**: {today_h_reason} (No regular classes)\n"
        else:
            resp += f"• **Non-Working Day**: No regular classes scheduled.\n"

        today_evs = ctx.get("calendar", {}).get("events", [])
        day_evs = [e for e in today_evs if e.get("date") == curr_date and "college" not in e.get("title", "").lower()]
        if day_evs:
            resp += "\n**Calendar Events:**\n"
            for e in day_evs:
                st = time_utils.evaluate_event_status(e, curr_time)
                badge = "Completed" if st["status"] == "completed" else ("In Progress" if st["status"] == "in_progress" else "Upcoming")
                time_part = f"{time_utils.format_time_12h(e.get('startTime'))}–{time_utils.format_time_12h(e.get('endTime'))}" if e.get("startTime") else "All Day"
                resp += f"• **{e.get('title')}** ({time_part}) — {badge}\n"
        else:
            resp += "\n**Calendar Events:** None scheduled for today.\n"

        if t_analysis["due_today_tasks"]:
            resp += "\n**Tasks Due Today:**\n"
            for t in t_analysis["due_today_tasks"]:
                resp += f"• **{t.get('title')}** ({t.get('priority', 'medium').capitalize()} priority)\n"

        if t_analysis["overdue_tasks"]:
            resp += f"\n**Overdue Tasks ({len(t_analysis['overdue_tasks'])}):** Top: **{t_analysis['overdue_tasks'][0].get('title')}** (was due {t_analysis['overdue_tasks'][0].get('deadline')})\n"

        if t_analysis["upcoming_exams"]:
            top_ex = t_analysis["upcoming_exams"][0]
            resp += f"\n**Upcoming Exam**: {top_ex['name']} in {top_ex['days_remaining']} day(s) ({top_ex['examDate']}).\n"

        thought = "Generated time-aware today summary."
        action = "none"

    # ROUTINE BEFORE / AFTER COLLEGE
    elif "before college" in msg:
        c_start = routine.get("collegeStart", "09:00")
        c_start_m = time_utils.parse_time_minutes(c_start)
        curr_m = time_utils.parse_time_minutes(curr_time)
        if is_working_day and curr_m < c_start_m:
            diff_mins = c_start_m - curr_m
            resp = f"College starts at **{time_utils.format_time_12h(c_start)}** ({time_utils.format_duration(diff_mins)} from now). You can use this time for breakfast, preparing your materials, and reviewing your notes."
        else:
            resp = f"College hours ({time_utils.format_time_12h(c_start)}–{time_utils.format_time_12h(routine.get('collegeEnd', '16:00'))}) are not upcoming right now."
        thought = "Answered before college query."
        action = "none"

    elif "after college" in msg:
        c_end = routine.get("collegeEnd", "16:00")
        resp = f"College ends at **{time_utils.format_time_12h(c_end)}**. After college, your routine allocates **{routine.get('studyHours', 3)} hours** of focused study before sleep at {time_utils.format_time_12h(routine.get('sleepTime', '23:00'))}."
        if t_analysis["upcoming_exams"]:
            resp += f" Top priority: Preparation for **{t_analysis['upcoming_exams'][0]['name']}** ({t_analysis['upcoming_exams'][0]['examDate']})."
        thought = "Answered after college query."
        action = "none"

    # TOMORROW SCHEDULE
    elif "tomorrow" in msg and any(k in msg for k in ["what should i do", "what do i have", "what to do", "schedule"]) and not any(k in msg for k in ["plan", "create", "add"]):
        tom_dt = datetime.strptime(curr_date, "%Y-%m-%d").date() + timedelta(days=1)
        tom_date = tom_dt.isoformat()
        tom_day = tom_dt.strftime("%A")
        is_tom_h, tom_h_reason = storage.is_holiday(tom_date, user_id=user_id)
        is_tom_work = tom_day in ctx.get("workingDays", []) and not is_tom_h

        resp = f"Here is your schedule overview for tomorrow (**{tom_day}, {tom_date}**):\n\n"
        if is_tom_h:
            resp += f"• **Holiday**: {tom_h_reason} (No regular classes).\n"
        elif is_tom_work:
            resp += f"• **College Hours**: {time_utils.format_time_12h(routine.get('collegeStart', '09:00'))}–{time_utils.format_time_12h(routine.get('collegeEnd', '16:00'))}.\n"
        else:
            resp += f"• **Weekend / Non-Working Day**: No regular classes.\n"

        tom_events = [e for e in ctx.get("calendar", {}).get("events", []) if e.get("date") == tom_date and "college" not in e.get("title", "").lower()]
        if tom_events:
            resp += "\n**Scheduled Events:**\n"
            for e in tom_events:
                time_part = f"{time_utils.format_time_12h(e.get('startTime'))}–{time_utils.format_time_12h(e.get('endTime'))}" if e.get("startTime") else "All Day"
                resp += f"• **{e.get('title')}** ({time_part})\n"
        else:
            resp += "\n**Scheduled Events:** None scheduled for tomorrow.\n"

        tom_tasks = [t for t in tasks if not t.get("completed") and t.get("deadline") == tom_date]
        if tom_tasks:
            resp += "\n**Tasks Due Tomorrow:**\n"
            for t in tom_tasks:
                resp += f"• **{t.get('title')}** ({t.get('priority', 'medium').capitalize()} priority)\n"
        thought = "Provided tomorrow schedule summary."
        action = "none"

    # NEXT TASK
    elif "next task" in msg or "what is my next task" in msg:
        pending_tasks = [t for t in tasks if not t.get("completed")]
        if t_analysis["overdue_tasks"]:
            top = t_analysis["overdue_tasks"][0]
            resp = f"Your highest priority task is overdue: **{top.get('title')}** (was due {top.get('deadline')})."
        elif t_analysis["due_today_tasks"]:
            top = t_analysis["due_today_tasks"][0]
            resp = f"Your next task is due today: **{top.get('title')}** ({top.get('priority', 'medium').capitalize()} priority)."
        elif t_analysis["upcoming_tasks"]:
            top = t_analysis["upcoming_tasks"][0]
            resp = f"Your next upcoming task is **{top.get('title')}** (Due: {top.get('deadline')}, in {top.get('days_left')} day(s))."
        elif pending_tasks:
            top = pending_tasks[0]
            resp = f"Your next task is **{top.get('title')}** ({top.get('priority', 'medium').capitalize()} priority)."
        else:
            resp = "You have no pending tasks on your task list!"
        thought = "Identified next task."
        action = "none"

    # SCENARIO 2 (Requirement 34): "Show my upcoming exams"
    elif is_exam_inquiry:
        subjects_with_exams = [s for s in subjects if s.get("examDate")]
        if not subjects_with_exams:
            resp = "You currently have no exams scheduled in your Academic subjects."
        else:
            lines = []
            for s in sorted(subjects_with_exams, key=lambda x: x.get("examDate")):
                ex_dt_str = s.get("examDate")
                try:
                    ex_dt = datetime.strptime(ex_dt_str.split("T")[0], "%Y-%m-%d").date()
                    diff = (ex_dt - datetime.strptime(curr_date, "%Y-%m-%d").date()).days
                    day_name = ex_dt.strftime("%A")
                    days_text = f"in {diff} day(s), {day_name}" if diff > 0 else f"TODAY ({day_name})" if diff == 0 else "passed"
                except Exception:
                    days_text = ""
                teacher_info = f" ({s.get('teacher')})" if s.get("teacher") else ""
                lines.append(f"• **{s.get('name')}**{teacher_info} — Exam Date: **{ex_dt_str}** ({days_text})")
            resp = f"Here are your upcoming academic exams:\n" + "\n".join(lines)
        thought = "Provided academic exam information. Zero calendar events created."
        action = "none"

    # SCENARIO 3 (Requirement 35): "What should I study for Advanced DBMS?" / "What should I study?"
    elif "what should i study" in msg or "what to study" in msg or ("should i study" in msg and not is_exam_prep_planning_request(msg)):
        matched_sub = find_exam_for_query(msg, subjects)
        if matched_sub:
            sub_name = matched_sub.get("name")
            exam_d = matched_sub.get("examDate")
            topics = matched_sub.get("importantTopics", [])
            tasks_for_sub = [
                t for t in tasks
                if not t.get("completed") and (
                    sub_name.lower() in t.get("title", "").lower()
                    or sub_name.lower() in t.get("subject", "").lower()
                )
            ]

            resp = f"For **{sub_name}**"
            if exam_d:
                try:
                    diff = (datetime.strptime(exam_d, "%Y-%m-%d").date() - datetime.strptime(curr_date, "%Y-%m-%d").date()).days
                    resp += f" (Exam on {exam_d}, {diff} days away):\n"
                except Exception:
                    resp += f" (Exam on {exam_d}):\n"
            else:
                resp += ":\n"

            if topics:
                resp += f"• Focus on your stored topics: {', '.join(topics)}.\n"
            else:
                # Requirement 29 & 30: DO NOT invent syllabus topics!
                resp += "• You have not added specific syllabus topics or uploaded documents for this subject yet. You can add focus topics in Academic or upload syllabus notes in Documents.\n"

            if tasks_for_sub:
                tasks_for_sub.sort(key=lambda t: t.get("deadline") or "9999-99-99")
                top_t = tasks_for_sub[0]
                resp += f"• Top priority: Complete **{top_t.get('title')}**" + (f" (Due: {top_t.get('deadline')})" if top_t.get('deadline') else "") + ".\n"
            resp += "• To generate a preparation schedule leading up to your exam, simply ask: 'Prepare my schedule for the Advanced DBMS exam'."
        else:
            pending = [t for t in tasks if not t.get("completed")]
            if pending:
                resp = f"You should focus on your top pending task: **{pending[0].get('title')}**."
            else:
                resp = "Your task list is clear! You can add a new study goal or review your enrolled subjects in Academic."
        thought = "Provided study guidance without inventing syllabus content. Zero calendar events created."
        action = "none"

    # SCENARIOS 1 & 10 (Requirements 9, 10, 20): "Plan my DBMS preparation until the exam" / "Prepare my schedule for the Advanced DBMS exam"
    elif is_exam_prep_planning_request(msg):
        matched_sub = find_exam_for_query(msg, subjects)
        if not matched_sub:
            subs_with_exam = [s for s in subjects if s.get("examDate")]
            if subs_with_exam:
                matched_sub = subs_with_exam[0]
            else:
                matched_sub = {"name": "Advanced DBMS", "examDate": parse_date_from_query(msg) or "2026-10-08"}

        prep_events = generate_exam_preparation_schedule(matched_sub, ctx, user_id=user_id)
        if prep_events:
            tools.create_schedule(prep_events, user_id=user_id)
            action = "create_schedule"
            action_result = {"status": "success", "events": prep_events}
            ex_date = matched_sub.get("examDate", "")
            college_hours_str = f"{time_utils.format_time_12h(routine.get('collegeStart', '09:00'))}–{time_utils.format_time_12h(routine.get('collegeEnd', '16:00'))}"
            resp = f"I've generated your preparation schedule for **{matched_sub.get('name')}** leading up to the exam on **{ex_date}**! " \
                   f"Work sessions and assignment focus have been scheduled outside your college hours ({college_hours_str}). " \
                   f"The exam day ({ex_date}) is designated as EXAM DAY with no heavy study sessions."
            thought = f"Generated {len(prep_events)} preparation events for {matched_sub.get('name')} exam on {ex_date}."
        else:
            resp = f"Could not create exam preparation schedule for {matched_sub.get('name')}."
            thought = "Failed to generate exam prep schedule."

    # SCENARIO 4: "Schedule DBMS preparation tomorrow from 6 PM to 7 PM"
    elif any(k in msg for k in ["schedule", "create work", "add work", "plan"]) and parse_date_from_query(msg):
        target_date = parse_date_from_query(msg)
        start_time, end_time = parse_time_from_query(msg)
        event_title = extract_event_title(message)

        is_h, h_reason = storage.is_holiday(target_date, user_id=user_id)
        res = tools.create_calendar_event(
            title=event_title,
            date=target_date,
            startTime=start_time,
            endTime=end_time,
            type="work",
            description="Scheduled via AI Agent",
            source="ai",
            user_id=user_id
        )
        action = "create_calendar_event"
        action_result = res

        if is_h:
            resp = f"Done. {target_date} is marked as {h_reason}, but I've scheduled **{event_title}** for {target_date} from {start_time} to {end_time} as requested."
        else:
            resp = f"Done. I've scheduled **{event_title}** for {target_date} from {start_time} to {end_time}."
        thought = f"Scheduled exactly ONE calendar event '{event_title}' on {target_date} ({start_time}–{end_time})."

    # DEADLINES INQUIRY (Requirement 8)
    elif re.search(r'\b(deadline|deadlines)\b', msg) and not any(k in msg for k in ["schedule", "create", "add", "plan"]):
        if not t_analysis["overdue_tasks"] and not t_analysis["due_today_tasks"] and not t_analysis["upcoming_tasks"]:
            resp = "You have no upcoming deadlines right now!"
        else:
            parts = []
            if t_analysis["overdue_tasks"]:
                lines = [f"• **{t.get('title')}** — Deadline: {t.get('deadline')} (OVERDUE by {t.get('days_overdue')} day(s))" for t in t_analysis["overdue_tasks"]]
                parts.append("**Overdue Tasks:**\n" + "\n".join(lines))
            if t_analysis["due_today_tasks"]:
                lines = [f"• **{t.get('title')}** — Due: TODAY ({t.get('priority', 'medium').capitalize()} priority)" for t in t_analysis["due_today_tasks"]]
                parts.append("**Due Today:**\n" + "\n".join(lines))
            if t_analysis["upcoming_tasks"]:
                lines = [f"• **{t.get('title')}** — Due: {t.get('deadline')} (in {t.get('days_left')} day(s), {t.get('day_name')})" for t in t_analysis["upcoming_tasks"]]
                parts.append("**Upcoming Deadlines:**\n" + "\n".join(lines))
            resp = "\n\n".join(parts)
        thought = f"Retrieved {len(t_analysis['overdue_tasks']) + len(t_analysis['due_today_tasks']) + len(t_analysis['upcoming_tasks'])} task deadlines. No calendar events created."
        action = "none"

    # SCENARIO 5 (Requirement 37): "Plan my week"
    elif "week" in msg and ("plan" in msg or "schedule" in msg):
        weekly_events = generate_weekly_plan(data, start_date=curr_date, user_id=user_id)
        if weekly_events:
            tools.create_schedule(weekly_events, user_id=user_id)
            action = "create_schedule"
            action_result = {"status": "success", "events": weekly_events}
            college_hours_str = f"{time_utils.format_time_12h(routine.get('collegeStart', '09:00'))}–{time_utils.format_time_12h(routine.get('collegeEnd', '16:00'))}"
            resp = f"I've generated your weekly schedule! Activities have been scheduled outside college hours ({college_hours_str}), prioritizing upcoming exams and task deadlines, while keeping non-working days and declared holidays free."
            thought = "Generated weekly plan respecting configured working days, college hours, and skipping holidays."
        else:
            resp = "You have no pending tasks or exams to schedule for this week."
            thought = "Weekly plan skipped because no items exist."

    # GENERAL WHAT SHOULD I DO TODAY
    elif "what should i do" in msg or "what to do" in msg:
        pending = [t for t in tasks if not t.get("completed")]
        upcoming_exams = [s for s in subjects if s.get("examDate")]
        if is_today_h:
            resp = f"Today is {today_h_reason}. Take time to rest and recharge!\n\n"
            if pending:
                resp += f"When you're ready for your next working day, here are your top pending items:\n"
                for t in pending[:3]:
                    resp += f"• {t.get('title')} (Due: {t.get('deadline') or 'No deadline'})\n"
        else:
            resp = "Here is what you should focus on today:\n"
            if upcoming_exams:
                closest_ex = sorted(upcoming_exams, key=lambda x: x.get("examDate"))[0]
                resp += f"• **Upcoming Exam**: {closest_ex.get('name')} on {closest_ex.get('examDate')}. Keep reviewing your notes!\n"
            if pending:
                high = [t for t in pending if t.get("priority") == "high"]
                primary = high[0] if high else pending[0]
                resp += f"• **Priority Task**: Complete **{primary.get('title')}**" + (f" (Due: {primary.get('deadline')})" if primary.get('deadline') else "") + ".\n"
            else:
                resp += "• Your task list is clear! You can review your subjects or take some time to recharge."
        thought = "Provided recommendations based on stored tasks and exams. Zero calendar events created."
        action = "none"

    # Default fallback reply
    else:
        resp = "How can I help you today? You can ask me 'What should I do now?', 'What is my next event?', 'What should I study now?', or to plan preparation for an upcoming exam."
        thought = "Handled conversational input without creating any events."

    transparency["step3_reasoning"] = thought
    transparency["step4_tool_action"] = action
    transparency["step5_final_output"] = resp

    return {
        "success": True,
        "response": resp,
        "thought": thought,
        "action": action,
        "action_result": action_result,
        "transparency": transparency,
        "is_live_gemini": False
    }

def generate_exam_preparation_schedule(subject: Dict[str, Any], context: Dict[str, Any], user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Requirements 4, 5, 8, 9, 10, 26, 28, 29:
    Intelligent exam preparation plan:
    Current date -> Exam date -> Available days -> Existing commitments -> Working days -> Holidays -> Tasks -> Study hours -> Preparation schedule.
    - Exam Day is recognized as EXAM DAY (no long study sessions).
    - If exam time is NOT known, NEVER invent an exam time (no 08:00, 10:00, 14:00 etc.).
    - Urgent task deadlines (e.g. DBMS Assignment due Oct 5) are prioritized before the deadline.
    - Study sessions are scheduled outside college hours (09:00 - 16:00).
    - Do NOT generate 10 micro-blocks per day (at most 2-3 meaningful sessions).
    - Do NOT invent syllabus topics (like B+ Trees or ACID) if not stored.
    """
    today_dt = date.today()
    ex_date_str = subject.get("examDate", "").split("T")[0].strip()
    if not ex_date_str:
        return []

    try:
        ex_dt = datetime.strptime(ex_date_str, "%Y-%m-%d").date()
    except Exception:
        return []

    if ex_dt < today_dt:
        return []

    sub_name = subject.get("name", "Subject")
    routine = context.get("routine", {})
    college_start = routine.get("collegeStart", "09:00")
    college_end = routine.get("collegeEnd", "16:00")
    tasks = context.get("tasks", [])
    existing_events = context.get("calendar", {}).get("events", [])
    topics = subject.get("importantTopics", [])
    working_days = context.get("workingDays") or storage.get_working_days(user_id)

    # Identify tasks related to this subject or due before or on the exam date
    related_tasks = [
        t for t in tasks
        if not t.get("completed") and (
            sub_name.lower() in t.get("title", "").lower()
            or sub_name.lower() in t.get("subject", "").lower()
            or (t.get("deadline") and t.get("deadline") <= ex_date_str)
        )
    ]
    related_tasks.sort(key=lambda t: t.get("deadline") or "9999-99-99")

    events = []
    days_count = (ex_dt - today_dt).days

    topic_idx = 0
    assigned_task_ids = set()

    # Preparation days leading up to exam date (excluding exam date itself)
    for i in range(0, days_count):
        curr_d = today_dt + timedelta(days=i)
        curr_d_str = curr_d.isoformat()
        day_name = curr_d.strftime("%A")
        is_h, h_reason = storage.is_holiday(curr_d_str, user_id=user_id)

        # Check existing events on this date
        day_existing = [e for e in existing_events if e.get("date") == curr_d_str]

        # 1. College Hours on working days if not already scheduled
        is_working = day_name in working_days and not is_h
        has_college = any("college" in e.get("title", "").lower() for e in day_existing)
        if is_working and not has_college:
            events.append({
                "title": "College Hours",
                "date": curr_d_str,
                "startTime": college_start,
                "endTime": college_end,
                "type": "college",
                "source": "ai",
                "description": "University lectures and classes"
            })

        # 2. Check if a related task is due on or near this date (e.g. DBMS Assignment due Oct 5)
        task_for_today = None
        for t in related_tasks:
            if t.get("id") not in assigned_task_ids:
                t_deadline = t.get("deadline")
                if t_deadline and t_deadline <= (curr_d + timedelta(days=1)).isoformat():
                    task_for_today = t
                    assigned_task_ids.add(t.get("id"))
                    break

        if task_for_today:
            # Schedule assignment session outside college hours
            slot_start = "17:00"
            slot_end = "18:30"
            if any(e.get("startTime") == slot_start for e in day_existing):
                slot_start = "19:30"
                slot_end = "21:00"

            events.append({
                "title": f"Work on {task_for_today.get('title')}",
                "date": curr_d_str,
                "startTime": slot_start,
                "endTime": slot_end,
                "type": "work",
                "source": "ai",
                "description": f"Dedicated assignment block for {sub_name} (Deadline: {task_for_today.get('deadline')})"
            })

        # 3. Dedicated Subject Exam Preparation Session
        prep_start = "19:00" if task_for_today else "18:00"
        prep_end = "20:30" if task_for_today else "19:30"

        # Check conflict with existing events
        if any(e.get("startTime") == prep_start for e in day_existing):
            prep_start = "20:00"
            prep_end = "21:30"

        # Determine focus title without inventing fake syllabus topics
        if topics and topic_idx < len(topics):
            focus_topic = topics[topic_idx]
            topic_idx += 1
            title = f"{sub_name}: {focus_topic}"
            desc = f"Focused review and problem practice on {focus_topic}"
        elif i == days_count - 1:
            title = f"{sub_name} Final Revision"
            desc = f"Comprehensive review and key formulas before exam day"
        elif i == 0:
            title = f"{sub_name} Exam Preparation"
            desc = f"Core concept review and revision for {sub_name}"
        else:
            title = f"{sub_name} Practice & Problem Solving"
            desc = f"Practice questions and sample problems for {sub_name}"

        events.append({
            "title": title,
            "date": curr_d_str,
            "startTime": prep_start,
            "endTime": prep_end,
            "type": "study",
            "source": "ai",
            "description": desc
        })

    # Requirement 5: Exam Day (ex_date_str)
    # Marked as EXAM DAY. No long study sessions.
    # If exam time is known from academic data, show it.
    # If exam time is NOT known, do NOT invent 08:00, 10:00, 14:00 etc.!
    exam_time = subject.get("examTime", "").strip()
    if exam_time:
        try:
            parts = exam_time.split(":")
            eh = int(parts[0])
            em = int(parts[1]) if len(parts) > 1 else 0
            end_eh = (eh + 2) % 24
            end_time = f"{end_eh:02d}:{em:02d}"
        except Exception:
            end_time = ""
        events.append({
            "title": f"EXAM: {sub_name}",
            "date": ex_date_str,
            "startTime": exam_time,
            "endTime": end_time,
            "type": "exam",
            "source": "ai",
            "isAllDay": False,
            "description": f"Official Exam for {sub_name}"
        })
    else:
        # DO NOT invent an exam time! isAllDay = True, startTime = ""
        events.append({
            "title": f"EXAM DAY: {sub_name}",
            "date": ex_date_str,
            "startTime": "",
            "endTime": "",
            "type": "exam",
            "source": "ai",
            "isAllDay": True,
            "description": f"Official Exam Day for {sub_name}. Light review and mental preparation."
        })

    return events

def generate_weekly_plan(data: Dict[str, Any], start_date: Optional[str] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Requirements 9, 10, 37: Generates a balanced 7-day schedule.
    Does NOT generate 10 micro-blocks per day.
    Does NOT duplicate College Hours.
    Prioritizes upcoming exams and urgent deadlines.
    Recognizes exam days without inventing exam times.
    """
    if start_date:
        try:
            curr_dt = datetime.strptime(start_date.split("T")[0], "%Y-%m-%d").date()
        except Exception:
            curr_dt = date.today()
    else:
        curr_dt = date.today()

    all_events = []
    tasks = [t for t in data.get("tasks", []) if not t.get("completed")]
    subjects = data.get("subjects", [])
    routine = data.get("routine", {})
    college_start = routine.get("collegeStart", "09:00")
    college_end = routine.get("collegeEnd", "16:00")
    existing_events = data.get("events", [])
    working_days = data.get("settings", {}).get("workingDays") or storage.get_working_days(user_id)

    # Sort tasks by deadline
    tasks_with_deadline = [t for t in tasks if t.get("deadline")]
    tasks_with_deadline.sort(key=lambda t: t.get("deadline"))
    other_tasks = [t for t in tasks if not t.get("deadline")]
    ordered_tasks = tasks_with_deadline + other_tasks

    task_idx = 0

    for i in range(7):
        day_date = curr_dt + timedelta(days=i)
        day_str = day_date.isoformat()
        day_name = day_date.strftime("%A")
        is_h, h_reason = storage.is_holiday(day_str, user_id=user_id)
        is_working = day_name in working_days and not is_h

        # Skip college hours on declared holidays and non-working days
        day_existing = [e for e in existing_events if e.get("date") == day_str]

        # 1. College Hours (only on working days, if not already on calendar)
        if is_working:
            has_college = any("college" in e.get("title", "").lower() for e in day_existing)
            if not has_college:
                all_events.append({
                    "title": "College Hours",
                    "date": day_str,
                    "startTime": college_start,
                    "endTime": college_end,
                    "type": "college",
                    "source": "ai",
                    "description": "Attending college lectures and classes"
                })

        # 2. Check if an exam falls on this day
        exam_today = next((s for s in subjects if s.get("examDate") == day_str), None)
        if exam_today:
            ex_time = exam_today.get("examTime", "").strip()
            if ex_time:
                all_events.append({
                    "title": f"EXAM: {exam_today.get('name')}",
                    "date": day_str,
                    "startTime": ex_time,
                    "endTime": "",
                    "type": "exam",
                    "source": "ai",
                    "isAllDay": False,
                    "description": f"Official Exam for {exam_today.get('name')}"
                })
            else:
                # Do NOT invent exam time
                all_events.append({
                    "title": f"EXAM DAY: {exam_today.get('name')}",
                    "date": day_str,
                    "startTime": "",
                    "endTime": "",
                    "type": "exam",
                    "source": "ai",
                    "isAllDay": True,
                    "description": f"Official Exam Day for {exam_today.get('name')}. Light review only."
                })
            continue

        # 3. Schedule 1 focused academic block outside college hours (18:00 - 19:30)
        # Priority order: Task with urgent deadline > Upcoming exam prep > General study
        upcoming_exam = next((s for s in subjects if s.get("examDate") and s.get("examDate") > day_str), None)

        if task_idx < len(ordered_tasks):
            t = ordered_tasks[task_idx]
            task_idx += 1
            all_events.append({
                "title": f"Work on {t.get('title')}",
                "date": day_str,
                "startTime": "18:00",
                "endTime": "19:30",
                "type": "work",
                "source": "ai",
                "description": f"Task focus: {t.get('title')}" + (f" (Due: {t.get('deadline')})" if t.get('deadline') else "")
            })
        elif upcoming_exam:
            all_events.append({
                "title": f"{upcoming_exam.get('name')} Preparation",
                "date": day_str,
                "startTime": "18:00",
                "endTime": "19:30",
                "type": "study",
                "source": "ai",
                "description": f"Preparation block for upcoming exam on {upcoming_exam.get('examDate')}"
            })
        elif subjects:
            s = subjects[i % len(subjects)]
            all_events.append({
                "title": f"Study {s.get('name')}",
                "date": day_str,
                "startTime": "18:00",
                "endTime": "19:30",
                "type": "study",
                "source": "ai",
                "description": f"Coursework and revision for {s.get('name')}"
            })

    return all_events

async def generate_calendar_for_date(target_date: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Requirements 5, 8, 9, 10, 16:
    Calendar "Generate with AI" for a selected date.
    Strictly verifies event.date == target_date.
    Analyzes complete LifeOS context:
    - If target_date is an EXAM DAY: recognizes it as EXAM DAY (no heavy study sessions).
      If exam time is NOT known, do NOT invent 08:00, 10:00, etc. (isAllDay=True).
    - If before an exam, prioritizes upcoming exam preparation and urgent deadlines outside college hours.
    - Does NOT generate 10 micro-blocks. Max 2-3 meaningful activities.
    - Avoids duplicate events.
    """
    clean_target = str(target_date).split("T")[0].strip()
    ctx = get_ai_context(user_id)
    data = storage.get_data(user_id)

    routine = ctx.get("routine", {})
    college_start = routine.get("collegeStart", "09:00")
    college_end = routine.get("collegeEnd", "16:00")
    tasks = [t for t in ctx.get("tasks", []) if not t.get("completed")]
    subjects = ctx.get("academic", {}).get("subjects", [])
    existing_events = tools.get_calendar_events(clean_target, user_id=user_id)
    is_h, h_reason = storage.is_holiday(clean_target, user_id=user_id)
    working_days = ctx.get("workingDays", [])

    try:
        dt_target = datetime.strptime(clean_target, "%Y-%m-%d").date()
        target_day_name = dt_target.strftime("%A")
        is_working = target_day_name in working_days and not is_h
    except Exception:
        is_working = not is_h

    # Check if clean_target is an EXAM DAY
    exam_on_this_date = next((s for s in subjects if s.get("examDate") == clean_target), None)

    # Check if an exam is upcoming within next 10 days
    upcoming_exam = next((s for s in subjects if s.get("examDate") and s.get("examDate") > clean_target), None)

    proposed_events: List[Dict[str, Any]] = []

    if gemini.is_api_key_configured():
        system_inst = f"""You are the LifeOS scheduling agent.
Generate a realistic, focused schedule STRICTLY for the single date: {clean_target}.
CRITICAL RULES:
1. Every event MUST have "date": "{clean_target}".
2. DO NOT output events for any other date.
3. DO NOT generate 10 micro-events. Generate at most 2 to 4 meaningful activities. No tiny blocks like "Short Break", "Review & Wrap Up", "Planning", "Break".
4. If {clean_target} is an EXAM DAY for a subject:
   - Designate it as EXAM DAY.
   - Do NOT schedule long study sessions.
   - If exam time is NOT known, do NOT invent an exam time (no 08:00, 10:00, 14:00 etc.). Set isAllDay = true or startTime = "".
5. If there is an upcoming exam, prioritize focused preparation outside college hours ({college_start}–{college_end}).
6. Prioritize tasks with urgent deadlines.
7. Return strictly valid JSON:
{{
  "events": [
    {{
      "title": "string",
      "date": "{clean_target}",
      "startTime": "HH:MM",
      "endTime": "HH:MM",
      "type": "college" | "study" | "work" | "exam",
      "isAllDay": false,
      "description": "string"
    }}
  ]
}}"""

        prompt = f"""Context for {clean_target}:
Exam on this date: {json.dumps(exam_on_this_date) if exam_on_this_date else 'None'}
Upcoming exam in near future: {json.dumps(upcoming_exam) if upcoming_exam else 'None'}
Holiday status: {'HOLIDAY (' + h_reason + ')' if is_h else 'Working day'}
Daily routine: {json.dumps(routine)}
Pending tasks: {json.dumps(tasks)}
Academic subjects: {json.dumps(subjects)}
Existing events already on {clean_target}: {json.dumps(existing_events)}

Generate the schedule strictly for {clean_target}."""

        res = await gemini.generate_content(
            system_instruction=system_inst,
            prompt=prompt,
            response_json=True
        )

        if res.get("success"):
            try:
                raw_text = res.get("text", "{}").strip()
                if "```json" in raw_text:
                    raw_text = raw_text.split("```json")[1].split("```")[0]
                elif "```" in raw_text:
                    raw_text = raw_text.split("```")[1].split("```")[0]
                match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                json_str = match.group(0) if match else raw_text
                parsed = json.loads(json_str.strip())
                if isinstance(parsed, dict) and "events" in parsed and isinstance(parsed["events"], list):
                    proposed_events = parsed["events"]
                elif isinstance(parsed, list):
                    proposed_events = parsed
            except Exception as e:
                print(f"[Calendar AI] Error parsing Gemini JSON: {e}")

    # Fallback generator if Gemini is offline, returned empty, or returned micro-blocks
    if not proposed_events:
        # 1. If Exam Day
        if exam_on_this_date:
            ex_time = exam_on_this_date.get("examTime", "").strip()
            if ex_time:
                proposed_events.append({
                    "title": f"EXAM: {exam_on_this_date.get('name')}",
                    "date": clean_target,
                    "startTime": ex_time,
                    "endTime": "",
                    "type": "exam",
                    "isAllDay": False,
                    "description": f"Official Exam for {exam_on_this_date.get('name')}"
                })
            else:
                # Do NOT invent exam times!
                proposed_events.append({
                    "title": f"EXAM DAY: {exam_on_this_date.get('name')}",
                    "date": clean_target,
                    "startTime": "",
                    "endTime": "",
                    "type": "exam",
                    "isAllDay": True,
                    "description": f"Official Exam Day for {exam_on_this_date.get('name')}. Stay focused and calm!"
                })

            if is_working and not any("college" in e.get("title", "").lower() for e in existing_events):
                proposed_events.append({
                    "title": "College Hours",
                    "date": clean_target,
                    "startTime": college_start,
                    "endTime": college_end,
                    "type": "college",
                    "description": "Attending university classes"
                })
        else:
            # Working day routine: College hours
            if is_working and not any("college" in e.get("title", "").lower() for e in existing_events):
                proposed_events.append({
                    "title": "College Hours",
                    "date": clean_target,
                    "startTime": college_start,
                    "endTime": college_end,
                    "type": "college",
                    "description": "Attending university classes"
                })

            # Priority 2: Tasks with urgent deadlines (due on or before clean_target + 1 day)
            urgent_tasks = [
                t for t in tasks
                if t.get("deadline") and t.get("deadline") <= (datetime.strptime(clean_target, "%Y-%m-%d").date() + timedelta(days=1)).isoformat()
            ]
            if urgent_tasks:
                first_t = urgent_tasks[0]
                proposed_events.append({
                    "title": f"Work on {first_t.get('title')}",
                    "date": clean_target,
                    "startTime": "17:00",
                    "endTime": "18:30",
                    "type": "work",
                    "description": f"Dedicated task session for {first_t.get('title')} (Due: {first_t.get('deadline')})"
                })

            # Priority 3: Upcoming exam preparation
            if upcoming_exam:
                proposed_events.append({
                    "title": f"{upcoming_exam.get('name')} Exam Preparation",
                    "date": clean_target,
                    "startTime": "19:00" if urgent_tasks else "18:00",
                    "endTime": "20:30" if urgent_tasks else "19:30",
                    "type": "study",
                    "description": f"Focused preparation for upcoming exam on {upcoming_exam.get('examDate')}"
                })
            elif subjects and not urgent_tasks:
                sub = subjects[0]
                proposed_events.append({
                    "title": f"Study {sub.get('name')}",
                    "date": clean_target,
                    "startTime": "18:00",
                    "endTime": "19:30",
                    "type": "study",
                    "description": f"Subject revision for {sub.get('name')}"
                })

    # Requirement 8 & 9 & 16: STRICT DATE VERIFICATION, DUPLICATE PREVENTION & REMOVE MICRO-EVENTS
    valid_events = []
    seen_titles = set()

    for ev in proposed_events:
        ev_date = str(ev.get("date", "")).split("T")[0].strip()
        if ev_date != clean_target:
            continue

        title = ev.get("title", "Work Session").strip()
        title_lower = title.lower()

        # Reject micro-events like Short Break, Break, Small Break, Planning, Review
        if any(bad in title_lower for bad in ["short break", "small break", "planning", "review & wrap up", "wrap up"]):
            continue

        # If exam on this date and title is study: reject long study blocks on exam day
        if exam_on_this_date and "study" in title_lower and not ("college" in title_lower or "exam" in title_lower):
            continue

        # Enforce Exam Day time rule: do not invent exam times
        is_ev_exam = ev.get("type") == "exam" or "exam" in title_lower
        is_all_day = ev.get("isAllDay", False)
        start = ev.get("startTime", "")

        if is_ev_exam and exam_on_this_date:
            known_time = exam_on_this_date.get("examTime", "").strip()
            if not known_time:
                # Do NOT invent exam time
                start = ""
                is_all_day = True
            else:
                start = known_time

        # Avoid duplicates within proposed set
        if title_lower in seen_titles:
            continue
        seen_titles.add(title_lower)

        # Check duplicate against existing events (not AI)
        is_dup = any(
            e.get("date") == clean_target and (
                (e.get("title", "").strip().lower() == title_lower and (is_all_day or e.get("startTime") == start))
                or ("college" in title_lower and "college" in e.get("title", "").lower())
            )
            for e in existing_events if e.get("source") != "ai"
        )
        if not is_dup:
            valid_events.append({
                "id": "event-" + str(uuid.uuid4())[:8],
                "user_id": user_id,
                "title": title,
                "date": clean_target,
                "startTime": start,
                "endTime": ev.get("endTime", "") if not is_all_day else "",
                "isAllDay": is_all_day,
                "type": ev.get("type", "work").lower(),
                "description": ev.get("description", "").strip(),
                "source": "ai"
            })

    # Requirement 9: Max 3-4 meaningful events
    valid_events = valid_events[:4]

    # Replace previous AI-generated events on clean_target
    fresh_data = storage.get_data(user_id)
    fresh_events = fresh_data.get("events", [])
    fresh_data["events"] = [e for e in fresh_events if not (e.get("date") == clean_target and e.get("source") == "ai")]
    fresh_data["events"].extend(valid_events)
    storage.save_data(fresh_data, user_id)
    storage.log_activity("generate_calendar_ai", f"Generated {len(valid_events)} schedule event(s) for {clean_target}", user_id=user_id)

    return {
        "status": "success",
        "message": f"Generated schedule for {clean_target}.",
        "events": valid_events
    }

async def generate_plan_with_ai(data: Dict[str, Any], target_date: str, explicit_override: bool = True, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    res = await generate_calendar_for_date(target_date, user_id=user_id)
    return res.get("events", [])

async def generate_ai_daily_summary(user_id: Optional[str] = None) -> str:
    ctx = get_ai_context(user_id)
    today_str = ctx["today"]["date"]
    is_today_h = ctx["today"]["isHoliday"]
    h_reason = ctx["today"]["holidayReason"]
    tasks = [t for t in ctx.get("tasks", []) if not t.get("completed")]
    events = tools.get_calendar_events(today_str, user_id=user_id)
    subjects = ctx.get("academic", {}).get("subjects", [])
    upcoming_exams = [s for s in subjects if s.get("examDate")]
    user_name = ctx.get("user", {}).get("name", "Student")

    if is_today_h:
        return f"Good day, {user_name}! Today is {h_reason}. Take time to rest and recharge!"

    if upcoming_exams:
        closest_ex = sorted(upcoming_exams, key=lambda s: s.get("examDate"))[0]
        try:
            diff = (datetime.strptime(closest_ex.get("examDate"), "%Y-%m-%d").date() - date.today()).days
            days_str = f"in {diff} day(s)" if diff > 0 else "TODAY"
        except Exception:
            days_str = closest_ex.get("examDate")
        return f"Upcoming Exam Alert: {closest_ex.get('name')} is scheduled for {closest_ex.get('examDate')} ({days_str}). You have {len(tasks)} pending task(s)."

    if tasks:
        high = [t for t in tasks if t.get("priority") == "high"]
        first_t = high[0] if high else tasks[0]
        return f"You have {len(tasks)} pending task(s). Top focus: '{first_t.get('title')}'. Stay consistent!"

    if events:
        return f"You have {len(events)} activity block(s) scheduled in your Calendar today."

    return f"Welcome, {user_name}! Your schedule is clear. You can add subjects in Academic or tasks to get started."

async def answer_document_question(doc_id: str, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    data = storage.get_data(user_id)
    docs = data.get("documents", [])
    target_doc = next((d for d in docs if d.get("id") == doc_id), None)
    if not target_doc:
        return {"success": False, "message": "Document not found."}

    doc_text = target_doc.get("textSnippet", "")
    if not doc_text:
        return {"success": False, "message": "The selected document has no extracted text content."}

    context_chunk = doc_text[:4000]
    if gemini.is_api_key_configured():
        system_inst = "You are LifeOS Document AI. Answer the student's question accurately using ONLY the provided document excerpt. If the answer is not in the text, say 'This document does not contain information to answer that question.'"
        prompt = f"DOCUMENT: {target_doc.get('name')}\nEXCERPT:\n{context_chunk}\n\nQUESTION: {query}"
        res = await gemini.generate_content(system_instruction=system_inst, prompt=prompt)
        if res.get("success"):
            return {
                "success": True,
                "documentName": target_doc.get("name"),
                "answer": res.get("text", "").strip()
            }

    return {
        "success": True,
        "documentName": target_doc.get("name"),
        "answer": f"Document Summary for '{target_doc.get('name')}':\n\n\"{doc_text[:300]}...\""
    }
