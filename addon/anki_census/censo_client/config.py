"""Global shared config for Anki Census across standalone and embedded add-ons."""

from __future__ import annotations

import json
import os
import secrets
import tempfile
from copy import deepcopy
from typing import Any, Dict

try:
    from aqt import mw
except Exception:  # pragma: no cover - used only outside Anki runtime.
    mw = None

from ..constants import USER_ID_ALPHABET, USER_ID_LENGTH
from .identity import normalize_source_id, utc_now_iso
from .version import CLIENT_VERSION

NEW_CONFIG_DIRNAME = "anki_census"
OLD_CONFIG_DIRNAME = "anki_census_legacy"
CONFIG_FILENAME = "config.json"

DEFAULT_GLOBAL_CONFIG: Dict[str, Any] = {
    "schema_version": 1,
    "anonymous_user_id": "",
    "participation_paused": False,
    "notice_seen": False,
    "first_notice_at": None,
    "first_send_allowed_after": None,
    "registered_sources": {},
    "last_submission": {},
    "client_version": CLIENT_VERSION,
}


def _safe_profile_folder() -> str:
    """Return the active Anki profile folder, with a temp fallback for tests."""
    if mw and getattr(mw, "pm", None) and hasattr(mw.pm, "profileFolder"):
        try:
            folder = mw.pm.profileFolder()
            if folder:
                return folder
        except Exception:
            pass
    return tempfile.gettempdir()


def _shared_dir_candidates() -> tuple[str, str]:
    """Return the new and legacy shared config directories."""
    base = os.path.join(_safe_profile_folder(), "addon_data")
    return (
        os.path.join(base, NEW_CONFIG_DIRNAME),
        os.path.join(base, OLD_CONFIG_DIRNAME),
    )


def _config_path_for(dir_path: str) -> str:
    """Return the full config path for a given config directory."""
    return os.path.join(dir_path, CONFIG_FILENAME)


def _merge(default: Dict[str, Any], actual: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge values while preserving unknown user keys."""
    result = deepcopy(default)
    for key, value in (actual or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_json(path: str) -> Dict[str, Any] | None:
    """Read JSON safely and return None on missing/corrupted content."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
    """Write JSON atomically to avoid partial/corrupted writes."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix="anki-census-", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def _ensure_anonymous_id(config: Dict[str, Any]) -> None:
    """Guarantee a stable anonymous id for all participants sharing this profile."""
    if config.get("anonymous_user_id"):
        return
    config["anonymous_user_id"] = "".join(secrets.choice(USER_ID_ALPHABET) for _ in range(USER_ID_LENGTH))


def get_shared_config_path() -> str:
    """Resolve the active shared config path, preferring the new directory with migration."""
    new_dir, old_dir = _shared_dir_candidates()
    new_path = _config_path_for(new_dir)
    old_path = _config_path_for(old_dir)
    if os.path.exists(new_path):
        return new_path
    if os.path.exists(old_path):
        os.makedirs(new_dir, exist_ok=True)
        old_payload = _read_json(old_path) or {}
        merged = _merge(DEFAULT_GLOBAL_CONFIG, old_payload)
        _ensure_anonymous_id(merged)
        _atomic_write_json(new_path, merged)
        return new_path
    return new_path


def load_global_config() -> Dict[str, Any]:
    """Load and normalize shared global config with safe fallback on corruption."""
    config_path = get_shared_config_path()
    payload = _read_json(config_path) or {}
    merged = _merge(DEFAULT_GLOBAL_CONFIG, payload)
    _ensure_anonymous_id(merged)
    if merged.get("client_version") != CLIENT_VERSION:
        merged["client_version"] = CLIENT_VERSION
    return merged


def save_global_config(config: Dict[str, Any]) -> None:
    """Persist global config atomically."""
    normalized = _merge(DEFAULT_GLOBAL_CONFIG, config or {})
    _ensure_anonymous_id(normalized)
    normalized["client_version"] = CLIENT_VERSION
    _atomic_write_json(get_shared_config_path(), normalized)


def register_source(config: Dict[str, Any], source_addon_id: str, source_addon_name: str, source_addon_version: str) -> Dict[str, Any]:
    """Upsert source metadata so all embedder add-ons are tracked in one global file."""
    now = utc_now_iso()
    source_id = normalize_source_id(source_addon_id)
    sources = config.setdefault("registered_sources", {})
    entry = sources.get(source_id) or {
        "name": source_addon_name or source_id,
        "version": source_addon_version or "0.0.0",
        "first_seen_at": now,
        "last_seen_at": now,
    }
    entry["name"] = source_addon_name or entry.get("name") or source_id
    entry["version"] = source_addon_version or entry.get("version") or "0.0.0"
    entry["last_seen_at"] = now
    entry.setdefault("first_seen_at", now)
    sources[source_id] = entry
    return config
