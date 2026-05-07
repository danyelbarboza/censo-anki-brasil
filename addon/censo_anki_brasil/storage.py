from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict
from aqt import mw
from .constants import DEFAULT_API_BASE_URL

ADDON_MODULE_NAME = None

DEFAULT_CONFIG = {
    "api_base_url": DEFAULT_API_BASE_URL,
    "language": "pt_BR",
    "participation_paused": False,
    "user_id": "",
    "profile": {},
    "profile_updated_at": {},
    "local_state": {
        "first_run_completed": False,
        "sent_surveys": {},
        "pending_surveys": {},
        "reminders_shown": {},
        "last_error": ""
    }
}

def set_addon_module_name(name: str) -> None:
    global ADDON_MODULE_NAME
    ADDON_MODULE_NAME = name

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _merge(default: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(default)
    for k, v in (actual or {}).items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _merge(result[k], v)
        else:
            result[k] = v
    return result

def load_config() -> Dict[str, Any]:
    cfg = mw.addonManager.getConfig(ADDON_MODULE_NAME) if ADDON_MODULE_NAME else None
    return _merge(DEFAULT_CONFIG, cfg or {})

def save_config(cfg: Dict[str, Any]) -> None:
    mw.addonManager.writeConfig(ADDON_MODULE_NAME, cfg)

def update_profile(new_profile: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    profile = cfg.setdefault("profile", {})
    updated = cfg.setdefault("profile_updated_at", {})
    now = utc_now_iso()
    for key, value in new_profile.items():
        if profile.get(key) != value:
            profile[key] = value
            updated[key] = now
    if profile.get("country") != "Brasil":
        if profile.get("state") is not None:
            profile["state"] = None
            updated["state"] = now
    save_config(cfg)
    return cfg

def mark_first_run_completed() -> None:
    cfg = load_config()
    cfg.setdefault("local_state", {})["first_run_completed"] = True
    save_config(cfg)

def mark_reminder(survey_id: str, phase: str) -> None:
    cfg = load_config()
    cfg.setdefault("local_state", {}).setdefault("reminders_shown", {})[f"{survey_id}:{phase}"] = utc_now_iso()
    save_config(cfg)

def was_reminder_shown(survey_id: str, phase: str) -> bool:
    cfg = load_config()
    return f"{survey_id}:{phase}" in cfg.get("local_state", {}).get("reminders_shown", {})

def mark_sent(survey_id: str) -> None:
    cfg = load_config()
    st = cfg.setdefault("local_state", {})
    st.setdefault("sent_surveys", {})[survey_id] = utc_now_iso()
    st.setdefault("pending_surveys", {}).pop(survey_id, None)
    st["last_error"] = ""
    save_config(cfg)

def mark_pending(survey_id: str, reason: str) -> None:
    cfg = load_config()
    st = cfg.setdefault("local_state", {})
    st.setdefault("pending_surveys", {})[survey_id] = {"last_attempt": utc_now_iso(), "reason": str(reason)[:500]}
    st["last_error"] = str(reason)[:500]
    save_config(cfg)

def has_sent(survey_id: str) -> bool:
    cfg = load_config()
    return survey_id in cfg.get("local_state", {}).get("sent_surveys", {})
