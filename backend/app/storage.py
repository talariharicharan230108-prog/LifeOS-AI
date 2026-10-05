import json
import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DATA_FILE = os.path.join(DATA_DIR, "lifeos_data.json")
DOCS_DIR = os.path.join(DATA_DIR, "documents")

DEFAULT_ROUTINE = {
    "wakeTime": "07:00",
    "sleepTime": "23:00",
    "collegeStart": "09:00",
    "collegeEnd": "16:00",
    "studyHours": 3,
    "breakPreference": "15 mins per 45 mins",
    "preferredSubjects": []
}

DEFAULT_SETTINGS = {
    "workingDays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
}

# ----------------- PASSWORD HASHING (PBKDF2-HMAC-SHA256) -----------------
def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hashes password with PBKDF2-HMAC-SHA256 using 100,000 iterations."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return key.hex(), salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifies candidate password against stored hash using constant-time comparison."""
    key, _ = hash_password(password, salt)
    return secrets.compare_digest(key, stored_hash)

# ----------------- DIRECTORY & STORAGE MANAGEMENT -----------------
def ensure_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    if not os.path.exists(DATA_FILE):
        initial = {
            "users": [],
            "sessions": {}
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=2, ensure_ascii=False)

def get_raw_storage() -> Dict[str, Any]:
    ensure_directories()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "users" not in data:
                data["users"] = []
            if "sessions" not in data:
                data["sessions"] = {}
            return data
    except Exception as e:
        print(f"Error reading {DATA_FILE}: {e}")
        return {"users": [], "sessions": {}}

def save_raw_storage(data: Dict[str, Any]) -> Dict[str, Any]:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return data

# ----------------- USER TEMPLATE & AUTH -----------------
def get_default_user_data(user_id: str, name: str, email: str, password_hash: str, salt: str) -> Dict[str, Any]:
    return {
        "id": user_id,
        "name": name,
        "email": email.lower().strip(),
        "password_hash": password_hash,
        "salt": salt,
        "createdAt": datetime.now().isoformat(),
        "user": {
            "name": name,
            "college": "",
            "course": "B.Tech AI / Computer Science",
            "onboarded": False
        },
        "routine": DEFAULT_ROUTINE.copy(),
        "settings": DEFAULT_SETTINGS.copy(),
        "tasks": [],
        "subjects": [],
        "events": [],
        "goals": [],
        "documents": [],
        "activity": [],
        "holidays": []
    }

def create_session(user_id: str) -> str:
    data = get_raw_storage()
    token = secrets.token_hex(24)
    expiry = (datetime.now() + timedelta(days=7)).isoformat()
    data.setdefault("sessions", {})[token] = {"user_id": user_id, "expiry": expiry}
    save_raw_storage(data)
    return token

def get_user_id_by_token(token: str) -> Optional[str]:
    data = get_raw_storage()
    session = data.get("sessions", {}).get(token)
    if isinstance(session, dict):
        try:
            expiry = datetime.fromisoformat(session.get("expiry", ""))
            if datetime.now() > expiry:
                delete_session(token)
                return None
            return session.get("user_id")
        except:
            return None
    elif isinstance(session, str):
        return session
    return None

def delete_session(token: str) -> bool:
    data = get_raw_storage()
    if token in data.get("sessions", {}):
        del data["sessions"][token]
        save_raw_storage(data)
        return True
    return False

def register_user(name: str, email: str, password: str) -> Tuple[Dict[str, Any], str]:
    data = get_raw_storage()
    email_clean = email.lower().strip()
    users = data.setdefault("users", [])
    for u in users:
        if u.get("email", "").lower().strip() == email_clean:
            raise ValueError("An account with this email address already exists.")

    pwd_hash, salt = hash_password(password)
    user_id = "user-" + str(uuid.uuid4())[:8]
    user_record = get_default_user_data(user_id, name.strip(), email_clean, pwd_hash, salt)
    users.append(user_record)
    save_raw_storage(data)

    token = create_session(user_id)
    safe_user = {
        "id": user_id,
        "name": user_record["name"],
        "email": user_record["email"]
    }
    return safe_user, token

def authenticate_user(email: str, password: str) -> Optional[Tuple[Dict[str, Any], str]]:
    data = get_raw_storage()
    email_clean = email.lower().strip()
    users = data.get("users", [])
    for u in users:
        if u.get("email", "").lower().strip() == email_clean:
            if verify_password(password, u.get("password_hash", ""), u.get("salt", "")):
                token = create_session(u["id"])
                user_name = u.get("name") or (u.get("user") if isinstance(u.get("user"), dict) else {}).get("name") or "Student"
                safe_user = {
                    "id": u["id"],
                    "name": user_name,
                    "email": u.get("email", email_clean)
                }
                return safe_user, token
            return None
    return None

def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    user_id = get_user_id_by_token(token)
    if not user_id:
        return None
    data = get_raw_storage()
    for u in data.get("users", []):
        if u.get("id") == user_id:
            user_name = u.get("name") or (u.get("user") if isinstance(u.get("user"), dict) else {}).get("name") or "Student"
            return {
                "id": u["id"],
                "name": user_name,
                "email": u.get("email", "")
            }
    return None

def change_password(user_id: str, current_password: str, new_password: str) -> bool:
    data = get_raw_storage()
    for u in data.get("users", []):
        if u.get("id") == user_id:
            if not verify_password(current_password, u.get("password_hash", ""), u.get("salt", "")):
                raise ValueError("Current password is incorrect.")
            new_hash, new_salt = hash_password(new_password)
            u["password_hash"] = new_hash
            u["salt"] = new_salt
            save_raw_storage(data)
            return True
    raise ValueError("User not found.")

def update_user_name(user_id: str, new_name: str) -> Dict[str, Any]:
    data = get_raw_storage()
    for u in data.get("users", []):
        if u.get("id") == user_id:
            u["name"] = new_name.strip()
            if "user" in u and isinstance(u["user"], dict):
                u["user"]["name"] = new_name.strip()
            save_raw_storage(data)
            return {"id": u["id"], "name": u["name"], "email": u["email"]}
    raise ValueError("User not found.")

# ----------------- MULTI-USER DATA ACCESS -----------------
def ensure_user_id_on_items(user_record: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Ensures tasks, events, goals, subjects, documents in user_record are explicitly tagged with user_id."""
    if not user_record or not user_id:
        return user_record
    for key in ("tasks", "events", "goals", "subjects", "documents"):
        for item in user_record.get(key, []):
            if isinstance(item, dict) and item.get("user_id") != user_id:
                item["user_id"] = user_id
    return user_record

def get_user_record(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieves full user data store strictly isolated for a specific user_id."""
    raw = get_raw_storage()
    users = raw.get("users", [])
    if user_id:
        for u in users:
            if u.get("id") == user_id:

                # Ensure settings always has valid working days.
                if not isinstance(u.get("settings"), dict):
                    u["settings"] = {}

                working_days = u["settings"].get("workingDays")

                # An empty list means no valid working-day configuration.
                # Use the LifeOS default: Monday-Saturday.
                if not isinstance(working_days, list) or len(working_days) == 0:
                    u["settings"]["workingDays"] = [
                        "Monday",
                        "Tuesday",
                        "Wednesday",
                        "Thursday",
                        "Friday",
                        "Saturday"
                    ]

                return ensure_user_id_on_items(u, user_id)
        # If specific user_id is requested but not found, return fresh isolated record
        fresh_user = {
            "id": user_id,
            "name": "User",
            "email": "",
            "user": {"name": "User", "college": "", "course": "Student", "onboarded": False},
            "routine": DEFAULT_ROUTINE.copy(),
            "settings": DEFAULT_SETTINGS.copy(),
            "tasks": [],
            "subjects": [],
            "events": [],
            "goals": [],
            "documents": [],
            "activity": [],
            "holidays": []
        }
        users.append(fresh_user)
        save_raw_storage(raw)
        return fresh_user

    # If user_id not specified, check if there is an explicit 'default' user
    for u in users:
        if u.get("id") == "default":
            return ensure_user_id_on_items(u, "default")

    if users:
        # Fallback for single-user local mode
        return ensure_user_id_on_items(users[0], users[0].get("id", "default"))

    # Fallback default empty template if no user yet registered
    return {
        "id": "default",
        "name": "Student",
        "email": "student@lifeos.app",
        "user": {"name": "Student", "college": "University", "course": "Student", "onboarded": False},
        "routine": DEFAULT_ROUTINE.copy(),
        "settings": DEFAULT_SETTINGS.copy(),
        "tasks": [],
        "subjects": [],
        "events": [],
        "goals": [],
        "documents": [],
        "activity": [],
        "holidays": []
    }

def get_data(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Canonical data getter isolated per user."""
    return get_user_record(user_id)

def save_data(data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
    """Canonical data saver strictly isolated per user."""
    raw = get_raw_storage()
    # Always keep a valid working-day configuration.
    if not isinstance(data.get("settings"), dict):
        data["settings"] = {}

    working_days = data["settings"].get("workingDays")

    if not isinstance(working_days, list) or len(working_days) == 0:
        data["settings"]["workingDays"] = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday"
    ]
    users = raw.setdefault("users", [])
    target_id = user_id or data.get("id")
    if target_id:
        ensure_user_id_on_items(data, target_id)
        for idx, u in enumerate(users):
            if u.get("id") == target_id:
                data["password_hash"] = u.get("password_hash")
                data["salt"] = u.get("salt")
                data["id"] = target_id
                data["email"] = u.get("email")
                if "name" not in data or not data["name"]:
                    data["name"] = u.get("name") or (data.get("user") if isinstance(data.get("user"), dict) else {}).get("name") or "Student"
                users[idx] = data
                save_raw_storage(raw)
                return data
        users.append(data)
        save_raw_storage(raw)
        return data
    save_raw_storage(raw)
    return data

def update_section(section: str, value: Any, user_id: Optional[str] = None) -> Dict[str, Any]:
    user_data = get_data(user_id)
    user_data[section] = value
    return save_data(user_data, user_id or user_data.get("id"))

def get_working_days(user_id: Optional[str] = None) -> List[str]:
    data = get_data(user_id)
    return data.get("settings", {}).get("workingDays") or ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

def is_working_day(date_str: str, user_id: Optional[str] = None) -> bool:
    if not date_str:
        return True
    try:
        date_clean = str(date_str).split("T")[0].strip()
        dt = datetime.strptime(date_clean, "%Y-%m-%d")
        day_name = dt.strftime("%A")
        working_days = get_working_days(user_id)
        return day_name in working_days
    except Exception:
        return True

def is_holiday(date_str: str, user_id: Optional[str] = None) -> Tuple[bool, str]:
    if not date_str:
        return (False, "")
    try:
        date_clean = str(date_str).split("T")[0].strip()
        dt = datetime.strptime(date_clean, "%Y-%m-%d")
        day_name = dt.strftime("%A")

        data = get_data(user_id)
        holidays = data.get("holidays", [])
        for h in holidays:
            h_date = str(h.get("date", "")).split("T")[0].strip()
            if h_date == date_clean:
                return (True, h.get("name") or "Holiday")

        working_days = get_working_days(user_id)
        if day_name not in working_days:
            return (True, f"Non-working day ({day_name})")

        return (False, "")
    except Exception as e:
        return (False, "")

def log_activity(action: str, details: str = "", user_id: Optional[str] = None):
    data = get_data(user_id)
    act = {
        "id": str(uuid.uuid4())[:8],
        "action": action,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    data.setdefault("activity", []).insert(0, act)
    data["activity"] = data["activity"][:50]
    save_data(data, user_id or data.get("id"))

def reset_all_data(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Clears user data (tasks, subjects, events, goals, documents) for specified user."""
    data = get_data(user_id)
    data["tasks"] = []
    data["subjects"] = []
    data["events"] = []
    data["goals"] = []
    data["documents"] = []
    data["activity"] = []
    data["holidays"] = []
    return save_data(data, user_id or data.get("id"))
