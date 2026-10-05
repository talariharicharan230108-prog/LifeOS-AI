import os
import sys

# Use the current backend directory dynamically
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))

print("Starting calendar, holiday, and Gemini generation updates...")

# ----------------- 1. WRITE app/api/holidays.py -----------------
holidays_py_content = '''from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
import datetime

from app.database.session import get_db
from app.models.entities import Holiday, Profile, User
from app.auth.deps import get_current_user

router = APIRouter(prefix="/holidays", tags=["Holidays"])

class HolidayPayload(BaseModel):
    name: Optional[str] = None
    title: Optional[str] = None
    date: str
    description: Optional[str] = ""
    notes: Optional[str] = ""

@router.get("")
@router.get("/")
def get_holidays(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns holidays strictly belonging to the currently authenticated user."""
    holidays = db.query(Holiday).filter(Holiday.user_id == current_user.id).order_by(Holiday.date.asc()).all()
    working_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if profile and profile.college_days:
        working_days = [d.strip() for d in profile.college_days.split(",") if d.strip()]
        
    hol_list = [
        {
            "id": h.id,
            "date": h.date,
            "name": h.title,
            "title": h.title,
            "description": h.notes or "",
            "notes": h.notes or ""
        }
        for h in holidays
    ]
    return {
        "status": "success",
        "holidays": hol_list,
        "working_days": working_days
    }

@router.post("")
@router.post("/")
def create_holiday(
    holiday_in: HolidayPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates or updates a user-specific holiday."""
    h_title = (holiday_in.name or holiday_in.title or "Holiday").strip()
    h_date = holiday_in.date.strip()
    h_notes = (holiday_in.description or holiday_in.notes or "").strip()

    existing = db.query(Holiday).filter(
        Holiday.user_id == current_user.id,
        Holiday.date == h_date
    ).first()

    if existing:
        existing.title = h_title
        existing.notes = h_notes
        db.commit()
        db.refresh(existing)
        h_obj = {
            "id": existing.id,
            "date": existing.date,
            "name": existing.title,
            "title": existing.title,
            "description": existing.notes,
            "notes": existing.notes
        }
        return {"status": "success", "holiday": h_obj, "holidays": [h_obj]}

    new_h = Holiday(
        user_id=current_user.id,
        date=h_date,
        title=h_title,
        notes=h_notes
    )
    db.add(new_h)
    db.commit()
    db.refresh(new_h)

    h_obj = {
        "id": new_h.id,
        "date": new_h.date,
        "name": new_h.title,
        "title": new_h.title,
        "description": new_h.notes,
        "notes": new_h.notes
    }
    return {"status": "success", "holiday": h_obj, "holidays": [h_obj]}

@router.put("/{holiday_id}")
def update_holiday(
    holiday_id: int,
    holiday_in: HolidayPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates an existing holiday owned by current user."""
    h = db.query(Holiday).filter(
        Holiday.id == holiday_id,
        Holiday.user_id == current_user.id
    ).first()
    if not h:
        raise HTTPException(status_code=404, detail="Holiday not found")

    if holiday_in.name or holiday_in.title:
        h.title = (holiday_in.name or holiday_in.title).strip()
    if holiday_in.date:
        h.date = holiday_in.date.strip()
    if holiday_in.description is not None or holiday_in.notes is not None:
        h.notes = (holiday_in.description or holiday_in.notes or "").strip()

    db.commit()
    db.refresh(h)
    return {
        "status": "success",
        "holiday": {
            "id": h.id,
            "date": h.date,
            "name": h.title,
            "title": h.title,
            "description": h.notes
        }
    }

@router.delete("/{holiday_id}")
def delete_holiday(
    holiday_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a holiday owned by current user (by ID or title)."""
    q = db.query(Holiday).filter(Holiday.user_id == current_user.id)
    if holiday_id.isdigit():
        q = q.filter(Holiday.id == int(holiday_id))
    else:
        q = q.filter(Holiday.title == holiday_id)
    h = q.first()
    if h:
        db.delete(h)
        db.commit()
    return {"status": "success", "message": "Holiday deleted"}

@router.get("/check")
def check_holiday_status(
    date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Checks whether a given date is a holiday or Sunday for current user."""
    clean_date = str(date).split("T")[0].strip()
    # 1. Declared holiday takes precedence
    declared = db.query(Holiday).filter(
        Holiday.user_id == current_user.id,
        Holiday.date == clean_date
    ).first()
    if declared:
        return {"isHoliday": True, "reason": declared.title}

    # 2. Check working days
    try:
        dt = datetime.datetime.strptime(clean_date, "%Y-%m-%d")
        day_name = dt.strftime("%A")
        profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        working_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        if profile and profile.college_days:
            working_days = [d.strip() for d in profile.college_days.split(",") if d.strip()]
        if day_name not in working_days:
            return {"isHoliday": True, "reason": f"Non-working day ({day_name})"}
    except Exception:
        pass

    return {"isHoliday": False, "reason": ""}
'''

t1_holidays_file = os.path.join(BACKEND_DIR, "app", "api", "holidays.py")
with open(t1_holidays_file, "w", encoding="utf-8") as f:
    f.write(holidays_py_content)
print(f"Created {t1_holidays_file}")

# ----------------- 2. UPDATE app/api/calendar.py with /generate in TERM 1 BACKEND -----------------
t1_calendar_file = os.path.join(BACKEND_DIR, "app", "api", "calendar.py")
with open(t1_calendar_file, "r", encoding="utf-8") as f:
    cal_code = f.read()

# Add schedule generation endpoint to calendar.py
generate_endpoint_code = '''
# --- AI CALENDAR SCHEDULE GENERATION ---

@router.post("/generate")
@router.post("/generate/")
async def generate_calendar_schedule(
    req: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Academic Requirements:
    Generates an optimized, conflict-free, realistic AI daily schedule for target_date.
    Uses current authenticated user's profile, routine, pending tasks, subjects, exams, and holidays.
    Reuses the central Gemini manager with multi-model fallback.
    Prevents duplicates and strictly respects date YYYY-MM-DD.
    """
    raw_date = req.get("date") or req.get("target_date") or datetime.date.today().isoformat()
    clean_date = str(raw_date).split("T")[0].strip()
    try:
        target_dt = datetime.datetime.strptime(clean_date, "%Y-%m-%d")
    except Exception:
        clean_date = datetime.date.today().isoformat()
        target_dt = datetime.datetime.strptime(clean_date, "%Y-%m-%d")

    day_name = target_dt.strftime("%A")

    # 1. Fetch user-specific profile, routine, tasks, courses, exams, holidays
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    wake_time = profile.wake_time if (profile and profile.wake_time) else "07:00"
    sleep_time = profile.sleep_time if (profile and profile.sleep_time) else "23:00"
    college_start = profile.college_start if (profile and profile.college_start) else "09:00"
    college_end = profile.college_end if (profile and profile.college_end) else "16:00"
    study_hours = profile.daily_study_hours if (profile and profile.daily_study_hours) else 3.0

    working_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    if profile and profile.college_days:
        working_days = [d.strip() for d in profile.college_days.split(",") if d.strip()]

    # 2. Check if clean_date is a declared holiday or Sunday/non-working day
    user_holidays = db.query(Holiday).filter(Holiday.user_id == current_user.id).all()
    declared_h = next((h for h in user_holidays if h.date == clean_date), None)
    is_sunday = (target_dt.weekday() == 6)
    is_non_working = (day_name not in working_days)
    is_holiday = bool(declared_h or is_sunday or is_non_working)
    holiday_reason = declared_h.title if declared_h else (f"Non-working day ({day_name})" if is_non_working else "")

    # 3. Fetch user's pending tasks & exams
    tasks = db.query(Task).filter(Task.user_id == current_user.id, Task.status != "COMPLETED").all()
    courses = db.query(Course).filter(Course.user_id == current_user.id).all()
    exams = db.query(Exam).filter(Exam.user_id == current_user.id).all()

    # 4. Fetch existing events on clean_date to prevent duplicates
    start_of_day = datetime.datetime.combine(target_dt.date(), datetime.time.min)
    end_of_day = datetime.datetime.combine(target_dt.date(), datetime.time.max)
    existing_events = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.start_time >= start_of_day,
        CalendarEvent.start_time <= end_of_day
    ).all()
    existing_event_keys = {(e.title.strip().lower(), e.start_time.strftime("%H:%M")) for e in existing_events}

    task_lines = [f"- {t.title} [Priority: {t.priority}, Deadline: {t.deadline.strftime('%Y-%m-%d') if t.deadline else 'None'}]" for t in tasks[:8]]
    exam_lines = [f"- {ex.title} ({ex.course_name}) on {ex.exam_date.strftime('%Y-%m-%d') if ex.exam_date else 'Upcoming'}" for ex in exams[:5]]
    course_names = [c.title for c in courses]

    # 5. Build strict prompt for Gemini
    prompt = f"""Generate an optimized academic & personal schedule for student '{current_user.name}' for {clean_date} ({day_name}).

STUDENT INFORMATION:
- Target Date: {clean_date} ({day_name})
- Is Holiday / Off-Day: {is_holiday} ({holiday_reason})
- Wake Time: {wake_time}, Sleep Time: {sleep_time}
- College Timings: {college_start} to {college_end} (only schedule college if NOT a holiday)
- Target Daily Study Hours: {study_hours}h
- Enrolled Subjects: {', '.join(course_names) if course_names else 'Computer Science / AI'}
- Pending Tasks:
{chr(10).join(task_lines) if task_lines else 'None'}
- Upcoming Exams:
{chr(10).join(exam_lines) if exam_lines else 'None'}

RULES:
1. Return ONLY a valid JSON array of event objects.
2. Each event object must have:
   - "title": concise descriptive title
   - "startTime": "HH:MM" (between {wake_time} and {sleep_time})
   - "endTime": "HH:MM"
   - "category": "COLLEGE" | "STUDY" | "EXAM" | "HEALTH" | "PERSONAL"
   - "notes": brief focus note
3. If it is a holiday/Sunday: DO NOT schedule routine college classes. Schedule 1-2 focused study blocks if tasks/exams are due, plus rest and recharge blocks.
4. Ensure no overlapping time intervals.
5. Return ONLY the raw JSON array, without markdown blocks."""

    # 6. Call Gemini using the same central Gemini service
    from app import gemini
    ai_schedule_raw = []
    try:
        gemini_res = await gemini.generate_content(
            prompt=prompt,
            system_instruction="You are an expert AI academic scheduler. Return only valid JSON array with scheduled blocks.",
            temperature=0.3,
            response_json=True
        )
        if gemini_res.get("success") and gemini_res.get("text"):
            text = gemini_res["text"].strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            ai_schedule_raw = json.loads(text.strip())
    except Exception as e:
        print(f"[Calendar] Gemini generation fallback to deterministic: {e}")

    # Fallback to deterministic slots if AI failed or returned empty
    if not ai_schedule_raw or not isinstance(ai_schedule_raw, list):
        ai_schedule_raw = []
        if not is_holiday and college_start and college_end:
            ai_schedule_raw.append({
                "title": "College Lectures & Labs",
                "startTime": college_start,
                "endTime": college_end,
                "category": "COLLEGE",
                "notes": "Academic attendance"
            })
        if tasks:
            top_t = tasks[0]
            ai_schedule_raw.append({
                "title": f"Study Block: {top_t.title}",
                "startTime": "17:30",
                "endTime": "19:00",
                "category": "STUDY",
                "notes": f"Work on {top_t.title}"
            })
        if is_holiday:
            ai_schedule_raw.append({
                "title": f"Rest & Personal Project ({holiday_reason or 'Holiday'})",
                "startTime": "10:00",
                "endTime": "12:00",
                "category": "PERSONAL",
                "notes": "Recharge & leisure"
            })

    # 7. Persist generated events to database, preventing duplicates
    created_events = []
    for item in ai_schedule_raw:
        if not isinstance(item, dict):
            continue
        title = item.get("title", "").strip()
        st_hm = item.get("startTime", "09:00").strip()
        et_hm = item.get("endTime", "10:00").strip()
        cat = item.get("category", "GENERAL").upper()
        notes = item.get("notes", "")

        if not title:
            continue

        # Prevent duplicate event on same date and start time
        if (title.lower(), st_hm) in existing_event_keys:
            continue

        try:
            st = datetime.datetime.fromisoformat(f"{clean_date}T{st_hm}:00")
            et = datetime.datetime.fromisoformat(f"{clean_date}T{et_hm}:00")
        except Exception:
            continue

        new_ev = CalendarEvent(
            user_id=current_user.id,
            title=title,
            start_time=st,
            end_time=et,
            category=cat,
            notes=notes,
            ai_scheduled=True,
            is_fixed=False
        )
        db.add(new_ev)
        created_events.append(new_ev)
        existing_event_keys.add((title.lower(), st_hm))

    db.commit()

    # Query all events on target date for user
    final_events = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == current_user.id,
        CalendarEvent.start_time >= start_of_day,
        CalendarEvent.start_time <= end_of_day
    ).all()

    return {
        "status": "success",
        "message": f"AI Schedule generated for {clean_date} ({len(created_events)} new event(s))!",
        "date": clean_date,
        "is_holiday": is_holiday,
        "holiday_reason": holiday_reason,
        "events": [
            {
                "id": e.id,
                "title": e.title,
                "date": clean_date,
                "startTime": e.start_time.strftime("%H:%M"),
                "endTime": e.end_time.strftime("%H:%M"),
                "type": "class" if e.category == "COLLEGE" else ("study" if e.category == "STUDY" else "work"),
                "category": e.category,
                "source": "ai" if e.ai_scheduled else "user",
                "description": e.notes or "",
                "notes": e.notes or ""
            }
            for e in final_events
        ],
        "count": len(created_events)
    }
'''

if "def generate_calendar_schedule" not in cal_code:
    cal_code += "\n" + generate_endpoint_code
    with open(t1_calendar_file, "w", encoding="utf-8") as f:
        f.write(cal_code)
    print(f"Added /calendar/generate endpoint to {t1_calendar_file}")
else:
    print(f"/calendar/generate already present in {t1_calendar_file}")

# ----------------- 3. UPDATE app/api/data.py in TERM 1 BACKEND (Include Holidays) -----------------
t1_data_file = os.path.join(BACKEND_DIR, "app", "api", "data.py")
with open(t1_data_file, "r", encoding="utf-8") as f:
    data_code = f.read()

# Make sure data.py imports Holiday
if "Holiday" not in data_code:
    data_code = data_code.replace("Course, CalendarEvent, Document", "Course, CalendarEvent, Document, Holiday")

# Make sure data.py queries Holiday for current user
if "holidays = db.query(Holiday).filter(Holiday.user_id == current_user.id).all()" not in data_code:
    data_code = data_code.replace(
        "docs = db.query(Document).filter(Document.user_id == current_user.id).all()",
        "docs = db.query(Document).filter(Document.user_id == current_user.id).all()\n    holidays = db.query(Holiday).filter(Holiday.user_id == current_user.id).all()"
    )
    data_code = data_code.replace(
        '"holidays": []',
        '''"holidays": [
        {
            "id": h.id,
            "date": h.date,
            "name": h.title,
            "title": h.title,
            "description": h.notes or "",
            "notes": h.notes or ""
        }
        for h in holidays
    ]'''
    )
    with open(t1_data_file, "w", encoding="utf-8") as f:
        f.write(data_code)
    print(f"Updated {t1_data_file} to include user-specific holidays in GET /api/data!")

# ----------------- 4. UPDATE app/api/__init__.py in TERM 1 BACKEND -----------------
t1_api_init = os.path.join(BACKEND_DIR, "app", "api", "__init__.py")
with open(t1_api_init, "r", encoding="utf-8") as f:
    init_code = f.read()

if "from app.api.holidays import router as holidays_router" not in init_code:
    init_code = init_code.replace(
        "from app.api.subjects import router as subjects_router",
        "from app.api.subjects import router as subjects_router\nfrom app.api.holidays import router as holidays_router"
    )
    init_code = init_code.replace(
        "api_router.include_router(subjects_router)",
        "api_router.include_router(subjects_router)\napi_router.include_router(holidays_router)"
    )
    with open(t1_api_init, "w", encoding="utf-8") as f:
        f.write(init_code)
    print(f"Updated {t1_api_init} to mount /api/holidays!")

print("Backend calendar, holiday, and Gemini updates applied successfully!")
