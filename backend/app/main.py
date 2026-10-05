import os
import uuid
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import set_key, load_dotenv

from . import storage
from . import tools
from . import gemini
from . import agent

load_dotenv()

app = FastAPI(title="LifeOS AI API", version="1.0.0")

# Enable CORS for frontend Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- SCHEMAS -----------------
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirmPassword: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    currentPassword: str
    newPassword: str
    confirmNewPassword: str

class ProfileUpdateRequest(BaseModel):
    name: str

class AgentRequest(BaseModel):
    message: str

class CalendarGenerateRequest(BaseModel):
    date: str

class PlanRequest(BaseModel):
    date: Optional[str] = None
    type: Optional[str] = "daily"
    override: Optional[bool] = False

class DocumentQARequest(BaseModel):
    doc_id: str
    query: str

class ApiKeyUpdate(BaseModel):
    api_key: str

class HolidayCreate(BaseModel):
    name: str
    date: str
    description: Optional[str] = ""

class HolidayUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None

# ----------------- AUTH DEPENDENCIES -----------------
def get_current_user_optional(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    if not authorization:
        return None
    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    if not token:
        return None
    try:
        return storage.get_user_by_token(token)
    except Exception as e:
        print(f"Error resolving user by token: {e}")
        return None

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    user = get_current_user_optional(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication token required or expired.")
    return user

# ----------------- SYSTEM & HEALTH -----------------
@app.get("/api/health")
async def health_check():
    gemini_status = await gemini.test_connection()
    return {
        "status": "healthy",
        "app": "LifeOS AI Personal Life & Study Assistant",
        "gemini": gemini_status,
        "timestamp": datetime.now().isoformat()
    }

# ----------------- AUTHENTICATION ENDPOINTS -----------------
@app.post("/api/auth/register")
def register_account(req: RegisterRequest):
    name = req.name.strip()
    email = req.email.strip().lower()
    password = req.password
    confirm_password = req.confirmPassword

    if not name or not email or not password or not confirm_password:
        raise HTTPException(status_code=400, detail="All fields are required.")

    if "@" not in email or "." not in email:
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")

    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long.")

    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    try:
        user_info, token = storage.register_user(name, email, password)
        return {
            "user": user_info,
            "token": token,
            "message": "Account created successfully."
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/auth/login")
def login_account(req: LoginRequest):
    email = req.email.strip().lower()
    password = req.password

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    res = storage.authenticate_user(email, password)
    if not res:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    user_info, token = res
    return {
        "user": user_info,
        "token": token,
        "message": "Logged in successfully."
    }

@app.post("/api/auth/logout")
def logout_account(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        if token:
            storage.delete_session(token)
    return {"status": "success", "message": "Logged out successfully."}

@app.get("/api/auth/me")
def get_current_user_profile(user: Dict[str, Any] = Depends(get_current_user)):
    return {"user": user}

@app.post("/api/auth/change-password")
def change_user_password(req: ChangePasswordRequest, user: Dict[str, Any] = Depends(get_current_user)):
    if not req.currentPassword or not req.newPassword or not req.confirmNewPassword:
        raise HTTPException(status_code=400, detail="All password fields are required.")

    if len(req.newPassword) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters long.")

    if req.newPassword != req.confirmNewPassword:
        raise HTTPException(status_code=400, detail="New password and confirmation do not match.")

    try:
        storage.change_password(user["id"], req.currentPassword, req.newPassword)
        return {"status": "success", "message": "Password changed successfully."}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to change password: {str(e)}")

@app.put("/api/auth/profile")
def update_profile(req: ProfileUpdateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name cannot be empty.")
    try:
        updated = storage.update_user_name(user["id"], name)
        return {"status": "success", "user": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ----------------- DATA MANAGEMENT (PER USER) -----------------
@app.get("/api/data")
def get_all_data(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    return storage.get_data(uid)

@app.post("/api/data")
def save_all_data(data: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    saved = storage.save_data(data, uid)
    return {"status": "success", "data": saved}

@app.post("/api/data/reset")
def reset_data(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    cleared = storage.reset_all_data(uid)
    return {"status": "success", "message": "All data cleared successfully.", "data": cleared}

# ----------------- PROFILE MANAGEMENT (PER USER) -----------------
@app.get("/api/profile")
def get_profile(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    u_obj = data.get("user") or {}
    r_obj = data.get("routine") or {}
    return {
        "id": 1,
        "user_id": uid,
        "name": u_obj.get("name", user["name"] if user else "Student"),
        "academic_institution": u_obj.get("college", ""),
        "degree_program": u_obj.get("course", ""),
        "wake_time": r_obj.get("wakeTime", ""),
        "sleep_time": r_obj.get("sleepTime", ""),
        "college_start": r_obj.get("collegeStart", ""),
        "college_end": r_obj.get("collegeEnd", ""),
        "daily_study_hours": r_obj.get("studyHours", 3.0),
        "onboarding_completed": bool(data.get("settings", {}).get("onboardingCompleted", False))
    }

@app.put("/api/profile")
@app.post("/api/profile")
@app.post("/api/profile/onboarding")
def save_profile(payload: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    u_obj = data.setdefault("user", {})
    r_obj = data.setdefault("routine", {})
    s_obj = data.setdefault("settings", {})
    if "name" in payload:
        u_obj["name"] = payload["name"]
        data["name"] = payload["name"]
    if "academic_institution" in payload or "college" in payload:
        u_obj["college"] = payload.get("academic_institution") or payload.get("college")
    if "degree_program" in payload or "course" in payload:
        u_obj["course"] = payload.get("degree_program") or payload.get("course")
    if "wake_time" in payload or "wakeTime" in payload:
        r_obj["wakeTime"] = payload.get("wake_time") or payload.get("wakeTime")
    if "sleep_time" in payload or "sleepTime" in payload:
        r_obj["sleepTime"] = payload.get("sleep_time") or payload.get("sleepTime")
    if "college_start" in payload or "collegeStart" in payload:
        r_obj["collegeStart"] = payload.get("college_start") or payload.get("collegeStart")
    if "college_end" in payload or "collegeEnd" in payload:
        r_obj["collegeEnd"] = payload.get("college_end") or payload.get("collegeEnd")
    if "daily_study_hours" in payload or "studyHours" in payload:
        r_obj["studyHours"] = payload.get("daily_study_hours") or payload.get("studyHours")
    s_obj["onboardingCompleted"] = True
    storage.save_data(data, uid)
    return get_profile(user=user)

# ----------------- HOLIDAY MANAGEMENT -----------------
@app.get("/api/holidays")
def get_holidays_list(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    return {
        "status": "success",
        "holidays": data.get("holidays", []),
        "working_days": storage.get_working_days(uid)
    }

@app.post("/api/holidays")
def add_new_holiday(req: HolidayCreate, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    name = req.name.strip()
    date_val = req.date.strip()
    if not name or not date_val:
        raise HTTPException(status_code=400, detail="Holiday name and date are required.")
    res = tools.add_holiday(name=name, date=date_val, description=req.description or "", user_id=uid)
    return res

@app.put("/api/holidays/{holiday_id}")
def edit_holiday(holiday_id: str, updates: HolidayUpdate, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    for h in data.get("holidays", []):
        if h.get("id") == holiday_id:
            if updates.name is not None:
                h["name"] = updates.name.strip()
            if updates.date is not None:
                h["date"] = updates.date.strip()
            if updates.description is not None:
                h["description"] = updates.description.strip()
            storage.save_data(data, uid)
            storage.log_activity("update_holiday", f"Updated holiday '{h.get('name')}'", user_id=uid)
            return {"status": "success", "holiday": h}
    raise HTTPException(status_code=404, detail="Holiday not found.")

@app.delete("/api/holidays/{holiday_id}")
def delete_holiday_item(holiday_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    res = tools.delete_holiday(holiday_id, user_id=uid)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

@app.get("/api/holidays/check")
def check_holiday_status(date: str, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    is_h, reason = storage.is_holiday(date, user_id=uid)
    return {
        "date": date,
        "is_holiday": is_h,
        "reason": reason if is_h else "Working day"
    }

# ----------------- AI AGENT & PLANNING -----------------
@app.post("/api/agent")
@app.post("/api/agent/")
@app.post("/api/agent/chat")
async def chat_with_agent(req: AgentRequest, user: Dict[str, Any] = Depends(get_current_user)):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    uid = user["id"]
    result = await agent.process_agent_message(req.message, user_id=uid)
    return result

@app.get("/api/agent/summary")
async def get_daily_summary(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    summary_text = await agent.generate_ai_daily_summary(user_id=uid)
    return {"summary": summary_text}

@app.post("/api/calendar/generate")
async def generate_calendar(req: CalendarGenerateRequest, user: Dict[str, Any] = Depends(get_current_user)):
    target_date = req.date.strip()
    if not target_date:
        raise HTTPException(status_code=400, detail="Date is required for calendar generation.")
    uid = user["id"]
    try:
        res = await agent.generate_calendar_for_date(target_date, user_id=uid)
        return res
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate schedule: {str(e)}")

@app.post("/api/agent/plan")
async def create_plan(req: PlanRequest, user: Dict[str, Any] = Depends(get_current_user)):
    target_date = req.date or date.today().isoformat()
    uid = user["id"]
    try:
        return await agent.generate_calendar_for_date(target_date, user_id=uid)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate schedule: {str(e)}")

# ----------------- TASKS CRUD -----------------
@app.get("/api/tasks")
def get_all_tasks(status: Optional[str] = None, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    return {"tasks": tools.get_tasks(status=status, user_id=uid)}

@app.post("/api/tasks")
def create_task(task_data: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    title = task_data.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Task title is required.")
    res = tools.add_task(
        title=title,
        deadline=task_data.get("deadline", ""),
        priority=task_data.get("priority", "medium"),
        subject=task_data.get("subject", ""),
        description=task_data.get("description", ""),
        user_id=uid
    )
    return res

@app.put("/api/tasks/{task_id}")
def edit_task(task_id: str, updates: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    res = tools.update_task(task_id, updates, user_id=uid)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    res = tools.delete_task(task_id, user_id=uid)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

# ----------------- SCHEDULE / EVENTS CRUD (UNIFIED CALENDAR) -----------------
@app.get("/api/events")
def get_events(date: Optional[str] = None, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    return {"status": "success", "events": tools.get_calendar_events(date, user_id=uid)}

@app.post("/api/events")
def create_event(event_data: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    title = event_data.get("title", "").strip()
    date_str = event_data.get("date", "").strip()
    if not title or not date_str:
        raise HTTPException(status_code=400, detail="Event title and date are required.")
    res = tools.create_calendar_event(
        title=title,
        date=date_str,
        startTime=event_data.get("startTime", "18:00"),
        endTime=event_data.get("endTime", "19:00"),
        type=event_data.get("type", "work"),
        description=event_data.get("description", ""),
        source=event_data.get("source", "user"),
        isAllDay=event_data.get("isAllDay", False),
        user_id=uid
    )
    return res

@app.put("/api/events/{event_id}")
def edit_event(event_id: str, updates: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    res = tools.update_calendar_event(event_id, updates, user_id=uid)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

@app.delete("/api/events/{event_id}")
def remove_event(event_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    res = tools.delete_calendar_event(event_id, user_id=uid)
    if res.get("status") == "error":
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res

# ----------------- WORKING DAYS SETTINGS -----------------
@app.get("/api/settings/working-days")
def get_working_days(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    return {"workingDays": storage.get_working_days(uid)}

@app.post("/api/settings/working-days")
def set_working_days(req: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    days = req.get("workingDays")
    if not isinstance(days, list):
        raise HTTPException(status_code=400, detail="workingDays must be a list of weekday names.")
    data = storage.get_data(uid)
    data.setdefault("settings", {})["workingDays"] = days
    storage.save_data(data, uid)
    storage.log_activity("update_working_days", f"Updated working days to {days}", user_id=uid)
    return {"status": "success", "workingDays": days}

# ----------------- SUBJECTS CRUD -----------------
# ----------------- SUBJECTS & ACADEMIC CRUD -----------------
@app.get("/api/academic")
def get_academic_profile(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    return tools.get_academic_data(user_id=uid)

@app.get("/api/subjects")
def get_all_subjects(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    academic = tools.get_academic_data(user_id=uid)
    return {"subjects": academic.get("subjects", [])}

@app.post("/api/subjects")
def create_subject(sub_data: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    target_uid = uid or data.get("id")
    name = sub_data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Subject name required.")
    new_sub = {
        "id": str(uuid.uuid4())[:8],
        "user_id": target_uid,
        "name": name,
        "teacher": sub_data.get("teacher", ""),
        "credits": int(sub_data.get("credits", 3)),
        "progress": int(sub_data.get("progress", 0)),
        "importantTopics": sub_data.get("importantTopics", []),
        "examDate": sub_data.get("examDate", ""),
        "examTime": sub_data.get("examTime", ""),
        "assignments": sub_data.get("assignments", [])
    }
    data.setdefault("subjects", []).append(new_sub)
    storage.save_data(data, uid)
    storage.log_activity("add_subject", f"Added subject '{name}'", user_id=uid)
    return {"status": "success", "subject": new_sub}

@app.put("/api/subjects/{subject_id}")
def update_subject(subject_id: str, updates: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    for s in data.get("subjects", []):
        if s.get("id") == subject_id:
            s.update(updates)
            storage.save_data(data, uid)
            return {"status": "success", "subject": s}
    raise HTTPException(status_code=404, detail="Subject not found.")

@app.delete("/api/subjects/{subject_id}")
def remove_subject(subject_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    data["subjects"] = [s for s in data.get("subjects", []) if s.get("id") != subject_id]
    storage.save_data(data, uid)
    return {"status": "success", "message": "Subject removed."}

# ----------------- GOALS CRUD -----------------
@app.get("/api/goals")
def get_all_goals(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    return {"goals": tools.get_goals(user_id=uid)}

@app.post("/api/goals")
def create_goal(goal_data: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    target_uid = uid or data.get("id")
    title = goal_data.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="Goal title is required.")
    new_goal = {
        "id": str(uuid.uuid4())[:8],
        "user_id": target_uid,
        "title": title,
        "description": goal_data.get("description", ""),
        "deadline": goal_data.get("deadline", ""),
        "progress": int(goal_data.get("progress", 0)),
        "category": goal_data.get("category", "Academic"),
        "createdAt": datetime.now().isoformat()
    }
    data.setdefault("goals", []).append(new_goal)
    storage.save_data(data, uid)
    return {"status": "success", "goal": new_goal}

@app.put("/api/goals/{goal_id}")
def update_goal(goal_id: str, updates: Dict[str, Any] = Body(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    for g in data.get("goals", []):
        if g.get("id") == goal_id:
            g.update(updates)
            storage.save_data(data, uid)
            return {"status": "success", "goal": g}
    raise HTTPException(status_code=404, detail="Goal not found.")

@app.delete("/api/goals/{goal_id}")
def remove_goal(goal_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    data["goals"] = [g for g in data.get("goals", []) if g.get("id") != goal_id]
    storage.save_data(data, uid)
    return {"status": "success", "message": "Goal removed."}

# ----------------- DOCUMENTS & SIMPLE RAG -----------------
@app.get("/api/documents")
@app.get("/api/documents/")
def get_all_documents(query: Optional[str] = None, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    docs = tools.search_documents(query or "", user_id=uid)
    formatted = []
    for d in docs:
        d_copy = dict(d)
        d_copy["filename"] = d.get("filename") or d.get("name") or "Document"
        d_copy["name"] = d_copy["filename"]
        d_copy["file_type"] = (d.get("file_type") or d.get("fileType") or "txt").lower()
        d_copy["fileType"] = d_copy["file_type"].upper()
        d_copy["size_bytes"] = d.get("size_bytes") or d.get("fileSize") or 0
        d_copy["fileSize"] = d_copy["size_bytes"]
        d_copy["uploaded_at"] = d.get("uploaded_at") or d.get("uploadDate") or datetime.now().isoformat()
        d_copy["uploadDate"] = d_copy["uploaded_at"]
        d_copy["status"] = d.get("status", "ready")
        formatted.append(d_copy)
    return {"status": "success", "documents": formatted}

@app.post("/api/documents/upload")
@app.post("/api/documents/upload/")
async def upload_document(file: UploadFile = File(...), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]

    allowed_exts = [".pdf", ".txt", ".docx"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_exts:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload PDF, TXT, or DOCX.")

    doc_id = str(uuid.uuid4())[:8]
    storage.ensure_directories()
    save_path = os.path.join(storage.DOCS_DIR, f"{doc_id}_{file.filename}")

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    extracted_text = ""
    try:
        if file_ext == ".txt":
            extracted_text = content.decode("utf-8", errors="ignore")
        elif file_ext == ".pdf":
            import pypdf
            reader = pypdf.PdfReader(save_path)
            for page in reader.pages[:15]:
                extracted_text += page.extract_text() or ""
        elif file_ext == ".docx":
            import docx
            doc = docx.Document(save_path)
            extracted_text = "\n".join([p.text for p in doc.paragraphs if p.text])
    except Exception as e:
        extracted_text = f"Text extraction warning: {str(e)}"

    data = storage.get_data(uid)
    target_uid = uid or data.get("id")
    file_size = len(content)
    now_iso = datetime.now().isoformat()
    doc_metadata = {
        "id": doc_id,
        "user_id": target_uid,
        "filename": file.filename,
        "name": file.filename,
        "file_type": file_ext.replace(".", "").lower(),
        "fileType": file_ext.replace(".", "").upper(),
        "size_bytes": file_size,
        "fileSize": file_size,
        "uploaded_at": now_iso,
        "uploadDate": now_iso,
        "filePath": save_path,
        "textSnippet": extracted_text[:8000],
        "extractedLength": len(extracted_text),
        "status": "ready"
    }

    data.setdefault("documents", []).append(doc_metadata)
    storage.save_data(data, uid)
    storage.log_activity("upload_document", f"Uploaded {file.filename}", user_id=uid)

    return {
        "status": "success",
        "success": True,
        "id": doc_id,
        "filename": file.filename,
        "document": doc_metadata
    }

@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    data = storage.get_data(uid)
    docs = data.get("documents", [])
    target = next((d for d in docs if str(d.get("id")) == str(doc_id)), None)
    if not target:
        raise HTTPException(status_code=404, detail="Document not found.")

    file_path = target.get("filePath")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    data["documents"] = [d for d in docs if str(d.get("id")) != str(doc_id)]
    storage.save_data(data, uid)
    storage.log_activity("delete_document", f"Deleted {target.get('name')}", user_id=uid)
    return {"status": "success", "success": True, "message": "Document deleted."}

@app.post("/api/documents/qa")
@app.post("/api/documents/qa/")
@app.post("/api/documents/query")
@app.post("/api/documents/query/")
async def document_qa(req: Optional[Dict[str, Any]] = Body(None), user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    req = req or {}
    q_str = req.get("question") or req.get("query") or ""
    doc_id = req.get("doc_id")
    res = await agent.answer_document_question(doc_id, q_str, user_id=uid)
    if isinstance(res, dict):
        res.setdefault("status", "success")
        return res
    return {"status": "success", "answer": str(res)}

# ----------------- AI STATUS & CONTEXT -----------------
@app.get("/api/ai/context")
def get_complete_ai_context(user: Dict[str, Any] = Depends(get_current_user)):
    uid = user["id"]
    return agent.get_ai_context(uid)

@app.get("/api/ai/status")
async def get_ai_status():
    status = await gemini.get_model_status()
    is_ok = bool(status.get("connected") or gemini.is_api_key_configured())
    return {
        "ok": is_ok,
        "connected": is_ok,
        "active_model": status.get("active_model", "gemini-3.1-flash-lite"),
        "fallback_enabled": status.get("fallback_enabled", True)
    }

@app.get("/api/ai/health")
@app.post("/api/ai/health")
@app.get("/api/ai/test")
@app.post("/api/ai/test")
async def test_ai_connection():
    res = await gemini.test_connection()
    if res.get("connected"):
        return {
            "ok": True,
            "status": "success",
            "connected": True,
            "message": "AI connection successful."
        }
    else:
        return {
            "ok": False,
            "status": "error",
            "connected": False,
            "message": "Gemini connection unavailable"
        }

# ----------------- SETTINGS & API KEY -----------------
@app.post("/api/settings/key")
async def update_api_key(req: ApiKeyUpdate):
    key = req.api_key.strip()
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        set_key(env_path, "GEMINI_API_KEY", key)
        os.environ["GEMINI_API_KEY"] = key
        gemini.reset_model_cache()
        test_res = await gemini.test_connection()
        return {
            "status": "success",
            "message": "API key saved successfully.",
            "test_result": test_res
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update .env: {str(e)}")

@app.get("/api/settings/key/status")
async def get_key_status():
    status = await gemini.get_model_status()
    return status
