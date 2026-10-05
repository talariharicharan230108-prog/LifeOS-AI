import os
import json
import time
import httpx
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables from backend/.env explicitly
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(ENV_FILE)

# Track active model and fallback state
_active_model: Optional[str] = None
_fallback_occurred: bool = False
_discovered_models: List[str] = []
_last_discovery_time: float = 0.0

def get_api_key() -> str:
    # Always read fresh in case updated at runtime
    load_dotenv(ENV_FILE)
    return os.getenv("GEMINI_API_KEY", "").strip().strip("'").strip('"')

def is_api_key_configured() -> bool:
    key = get_api_key()
    return bool(key and len(key) > 10 and not key.startswith("YOUR_"))

def get_configured_model() -> str:
    load_dotenv(ENV_FILE)
    return os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()

def get_configured_fallback_models() -> List[str]:
    load_dotenv(ENV_FILE)
    raw = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash-lite,gemini-3.6-flash,gemini-flash-lite-latest,gemini-3.8-flash,gemini-3.5-flash").strip()
    return [m.strip() for m in raw.split(",") if m.strip()]

def get_active_model() -> str:
    global _active_model
    return _active_model or get_configured_model()

def has_fallback_occurred() -> bool:
    return _fallback_occurred

def reset_model_cache():
    global _active_model, _fallback_occurred, _discovered_models, _last_discovery_time
    _active_model = None
    _fallback_occurred = False
    _discovered_models = []
    _last_discovery_time = 0.0

async def discover_available_models(key: str) -> List[str]:
    """
    Safely queries Gemini models listing endpoint and filters for
    active text-generation models supporting 'generateContent'.
    Excludes image-only, tts, embedding, and non-general models.
    """
    global _discovered_models, _last_discovery_time
    # Cache discovery for 5 minutes
    if _discovered_models and (time.time() - _last_discovery_time < 300):
        return _discovered_models

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    print("[Gemini] Discovering available generateContent models from Gemini API...")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                raw_models = resp.json().get("models", [])
                valid_models = []

                for m in raw_models:
                    methods = m.get("supportedGenerationMethods", [])
                    name = m.get("name", "").replace("models/", "").strip()

                    # Must support generateContent
                    if "generateContent" not in methods:
                        continue

                    # Exclude specialized non-text generation models
                    lower_name = name.lower()
                    if any(bad in lower_name for bad in [
                        "-tts", "-image", "clip", "transcribe", "embedding",
                        "computer-use", "robotics", "banana", "customtools"
                    ]):
                        continue

                    valid_models.append(name)

                # Prioritize flash models first, then pro/others
                flash_models = [m for m in valid_models if "flash" in m.lower()]
                other_models = [m for m in valid_models if "flash" not in m.lower()]
                ordered = flash_models + other_models

                _discovered_models = ordered
                _last_discovery_time = time.time()
                print(f"[Gemini] Discovered {len(ordered)} compatible models: {ordered[:5]}...")
                return ordered
            else:
                print(f"[Gemini] Model discovery failed ({resp.status_code})")
    except Exception as e:
        print(f"[Gemini] Model discovery exception: {str(e)}")

    return _discovered_models

def build_model_candidates(discovered: List[str] = None) -> List[str]:
    """
    Constructs the ordered model priority list:
    1. Active working model (if already discovered)
    2. Configured model from .env (e.g. gemini-2.5-flash)
    3. Default priority: gemini-2.5-flash, gemini-2.5-flash-lite
    4. Configured fallbacks from .env (e.g. gemini-3.8-flash, gemini-3.5-flash)
    5. Discovered models from API
    """
    configured = get_configured_model()
    fallbacks = get_configured_fallback_models()
    discovered_list = discovered or _discovered_models

    candidates: List[str] = []

    # If an active model was already verified and working, try it first
    if _active_model and _active_model not in candidates:
        candidates.append(_active_model)

    if configured and configured not in candidates:
        candidates.append(configured)

    for m in ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.6-flash"]:
        if m not in candidates:
            candidates.append(m)

    for m in fallbacks:
        if m not in candidates:
            candidates.append(m)

    for m in discovered_list:
        if m not in candidates:
            candidates.append(m)

    return candidates

async def generate_content(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: float = 0.4,
    response_json: bool = False,
    max_attempts: int = 5
) -> Dict[str, Any]:
    """
    Central Gemini content generation with automated model fallback.
    Tries primary model -> fallback models -> dynamic discovered models.
    Stops immediately for authentication errors without retrying.
    """
    global _active_model, _fallback_occurred

    key = get_api_key()
    if not is_api_key_configured():
        return {
            "success": False,
            "error": "API_KEY_MISSING",
            "message": "Gemini API key is not configured. Please provide your GEMINI_API_KEY in the .env file or Settings."
        }

    # Prepare payload
    payload: Dict[str, Any] = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": 2048,
        }
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    if response_json:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    # Get model candidates
    candidates = build_model_candidates()
    configured_primary = get_configured_model()

    attempts = 0
    idx = 0

    async with httpx.AsyncClient(timeout=25.0) as client:
        while idx < len(candidates) and attempts < max_attempts:
            model = candidates[idx]
            attempts += 1
            idx += 1

            print(f"[Gemini] Trying model: {model}")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

            try:
                resp = await client.post(url, json=payload)

                # SUCCESS
                if resp.status_code == 200:
                    print(f"[Gemini] Success using: {model}")
                    _active_model = model
                    if model != configured_primary:
                        _fallback_occurred = True

                    data = resp.json()
                    candidates_list = data.get("candidates", [])
                    if candidates_list:
                        text = candidates_list[0]["content"]["parts"][0]["text"]
                        return {
                            "success": True,
                            "text": text,
                            "model": model,
                            "active_model": model,
                            "fallback_occurred": _fallback_occurred
                        }
                    return {
                        "success": False,
                        "error": "NO_CANDIDATE",
                        "message": "No response candidate received from Gemini."
                    }

                # Extract error text
                err_text = ""
                try:
                    err_json = resp.json()
                    err_text = err_json.get("error", {}).get("message", resp.text)
                except Exception:
                    err_text = resp.text

                # AUTHENTICATION / INVALID KEY ERROR - DO NOT RETRY
                err_lower = err_text.lower()
                if (
                    resp.status_code in (401, 403)
                    or "api key not valid" in err_lower
                    or "api_key_invalid" in err_lower
                    or "invalid api key" in err_lower
                ):
                    print(f"[Gemini] Authentication error ({resp.status_code}): Invalid or unauthorized API key.")
                    return {
                        "success": False,
                        "error": "AUTH_ERROR",
                        "message": "Gemini API key is invalid or unauthorized."
                    }

                print(f"[Gemini] Model failed: {model} (Status {resp.status_code}: {err_text[:75]})")
                _fallback_occurred = True

                # If candidates are exhausted, trigger dynamic discovery
                if idx >= len(candidates) and not _discovered_models:
                    discovered = await discover_available_models(key)
                    for dm in discovered:
                        if dm not in candidates:
                            candidates.append(dm)

                if idx < len(candidates) and attempts < max_attempts:
                    print(f"[Gemini] Trying fallback: {candidates[idx]}")

            except httpx.ConnectTimeout:
                print(f"[Gemini] Model failed: {model} (ConnectTimeout)")
                _fallback_occurred = True
                if idx < len(candidates) and attempts < max_attempts:
                    print(f"[Gemini] Trying fallback: {candidates[idx]}")
            except Exception as e:
                print(f"[Gemini] Model failed: {model} (Exception: {str(e)[:60]})")
                _fallback_occurred = True
                if idx < len(candidates) and attempts < max_attempts:
                    print(f"[Gemini] Trying fallback: {candidates[idx]}")

    # If all models failed
    return {
        "success": False,
        "error": "ALL_MODELS_FAILED",
        "message": "Gemini is currently unavailable. Please check your API key or try again later."
    }

# Alias for backward-compatibility
async def generate_gemini_content(
    system_instruction: Optional[str],
    prompt: str,
    temperature: float = 0.4,
    response_json: bool = False
) -> Dict[str, Any]:
    return await generate_content(
        prompt=prompt,
        system_instruction=system_instruction,
        temperature=temperature,
        response_json=response_json
    )

async def test_connection() -> Dict[str, Any]:
    """
    Tests Gemini connection by pinging preferred model and auto-falling back.
    Returns status, active working model, and fallback flag.
    """
    key = get_api_key()
    if not is_api_key_configured():
        return {
            "status": "error",
            "message": "GEMINI_API_KEY is not configured. Please set your API key in .env or Settings."
        }

    # Ping test using generate_content
    res = await generate_content(
        prompt="Respond with 'OK'.",
        temperature=0.1,
        max_attempts=4
    )

    if res.get("success"):
        return {
            "status": "connected",
            "connected": True,
            "active_model": res.get("model", get_active_model()),
            "configured_model": get_configured_model(),
            "fallback_occurred": res.get("fallback_occurred", False),
            "message": f"Connected successfully using {res.get('model')}." + (
                " (Automatically switched to fallback model)" if res.get("fallback_occurred") else ""
            )
        }
    else:
        return {
            "status": "error",
            "connected": False,
            "message": res.get("message", "Connection failed.")
        }

async def get_model_status() -> Dict[str, Any]:
    """
    Returns full AI status for GET /api/ai/status.
    Does NOT expose API key.
    """
    key = get_api_key()
    configured = is_api_key_configured()

    if not configured:
        return {
            "connected": False,
            "active_model": get_configured_model(),
            "configured_model": get_configured_model(),
            "fallback_enabled": True,
            "fallback_occurred": False,
            "available_models": build_model_candidates()
        }

    # Discover models if not yet discovered
    if not _discovered_models:
        await discover_available_models(key)

    candidates = build_model_candidates()

    return {
        "connected": True if _active_model else False,
        "active_model": get_active_model(),
        "configured_model": get_configured_model(),
        "fallback_enabled": True,
        "fallback_occurred": _fallback_occurred,
        "available_models": candidates[:8]
    }
