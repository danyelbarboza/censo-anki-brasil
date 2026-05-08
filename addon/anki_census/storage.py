from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from aqt import mw

from .constants import ADDON_VERSION, DEFAULT_API_BASE_URL
from .censo_client.config import load_global_config, save_global_config
from .censo_client.identity import utc_now_iso

ADDON_MODULE_NAME = None

GLOBAL_KEYS = {
    "anonymous_user_id",
    "participation_paused",
    "notice_seen",
    "first_notice_at",
    "first_send_allowed_after",
    "registered_sources",
    "last_submission",
    "client_version",
}

DEFAULT_CONFIG = {
    "api_base_url": DEFAULT_API_BASE_URL,
    "language": "en",
    "addon_version": ADDON_VERSION,
    "participation_paused": False,
    "user_id": "",
    "profile": {},
    "profile_updated_at": {},
    "local_state": {
        "first_run_completed": False,
        "sent_surveys": {},
        "pending_surveys": {},
        "reminders_shown": {},
        "last_error": "",
    },
}


def set_addon_module_name(name: str) -> None:
    """Store the add-on module name used by Anki's AddonManager config API."""
    global ADDON_MODULE_NAME
    ADDON_MODULE_NAME = name


def _merge(default: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge helper that preserves unknown user keys."""
    result = deepcopy(default)
    for key, value in (actual or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _addon_load() -> Dict[str, Any]:
    """Load per-add-on config, returning empty dict when unavailable."""
    if not ADDON_MODULE_NAME:
        return {}
    cfg = mw.addonManager.getConfig(ADDON_MODULE_NAME)
    return cfg if isinstance(cfg, dict) else {}


def _addon_save(cfg: Dict[str, Any]) -> None:
    """Persist per-add-on config safely when module name is already known."""
    if ADDON_MODULE_NAME:
        mw.addonManager.writeConfig(ADDON_MODULE_NAME, cfg)


def load_config() -> Dict[str, Any]:
    """Load merged config using per-add-on fields plus shared global census fields."""
    local_cfg = _merge(DEFAULT_CONFIG, _addon_load())
    global_cfg = load_global_config()

    # Keep backward compatibility for legacy code that expects `user_id`.
    local_cfg["user_id"] = global_cfg.get("anonymous_user_id", "")

    for key in GLOBAL_KEYS:
        local_cfg[key] = deepcopy(global_cfg.get(key))
    return local_cfg


def save_config(cfg: Dict[str, Any]) -> None:
    """Save both config layers, routing shared keys to global shared storage."""
    cfg = cfg or {}
    addon_payload = {}
    for key, value in cfg.items():
        if key not in GLOBAL_KEYS and key != "user_id":
            addon_payload[key] = value

    merged_addon_payload = _merge(DEFAULT_CONFIG, addon_payload)
    merged_addon_payload["user_id"] = cfg.get("user_id") or merged_addon_payload.get("user_id") or ""
    _addon_save(merged_addon_payload)

    global_cfg = load_global_config()
    for key in GLOBAL_KEYS:
        if key in cfg:
            global_cfg[key] = deepcopy(cfg[key])

    if cfg.get("user_id"):
        global_cfg["anonymous_user_id"] = cfg["user_id"]
    save_global_config(global_cfg)


def update_profile(new_profile: Dict[str, Any]) -> Dict[str, Any]:
    """Update optional profile fields and keep per-field update timestamps."""
    cfg = load_config()
    profile = cfg.setdefault("profile", {})
    updated = cfg.setdefault("profile_updated_at", {})
    now = utc_now_iso()
    for key, value in new_profile.items():
        if profile.get(key) != value:
            profile[key] = value
            updated[key] = now
    if profile.get("country") != "Brazil" and profile.get("state") is not None:
        profile["state"] = None
        updated["state"] = now
    save_config(cfg)
    return cfg


def mark_first_run_completed() -> None:
    """Store that the first-run dialog has already been shown."""
    cfg = load_config()
    cfg.setdefault("local_state", {})["first_run_completed"] = True
    cfg["notice_seen"] = True
    cfg.setdefault("first_notice_at", utc_now_iso())
    cfg.setdefault("first_send_allowed_after", utc_now_iso())
    save_config(cfg)


def mark_reminder(survey_id: str, phase: str) -> None:
    """Record reminder display to avoid showing the same reminder multiple times."""
    cfg = load_config()
    cfg.setdefault("local_state", {}).setdefault("reminders_shown", {})[f"{survey_id}:{phase}"] = utc_now_iso()
    save_config(cfg)


def was_reminder_shown(survey_id: str, phase: str) -> bool:
    """Return True when a reminder for the same survey+phase was already displayed."""
    cfg = load_config()
    return f"{survey_id}:{phase}" in cfg.get("local_state", {}).get("reminders_shown", {})


def mark_sent(survey_id: str) -> None:
    """Mark successful submission in both local and shared config layers."""
    cfg = load_config()
    state = cfg.setdefault("local_state", {})
    state.setdefault("sent_surveys", {})[survey_id] = utc_now_iso()
    state.setdefault("pending_surveys", {}).pop(survey_id, None)
    state["last_error"] = ""
    cfg.setdefault("last_submission", {})[survey_id] = {
        "submitted_at": utc_now_iso(),
        "source_addon_id": "anki-census-standalone",
    }
    save_config(cfg)


def mark_pending(survey_id: str, reason: str) -> None:
    """Mark failed submission attempt with a safe truncated error message."""
    cfg = load_config()
    state = cfg.setdefault("local_state", {})
    state.setdefault("pending_surveys", {})[survey_id] = {
        "last_attempt": utc_now_iso(),
        "reason": str(reason)[:500],
    }
    state["last_error"] = str(reason)[:500]
    save_config(cfg)


def has_sent(survey_id: str) -> bool:
    """Return True when the survey was already sent in local or shared submission state."""
    cfg = load_config()
    return survey_id in cfg.get("local_state", {}).get("sent_surveys", {}) or survey_id in cfg.get("last_submission", {})
