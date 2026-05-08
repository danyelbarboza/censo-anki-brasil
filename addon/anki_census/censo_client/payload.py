"""Payload helpers for reusable Anki Census metadata and embedded debug previews."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import re
import sys
from copy import deepcopy
from datetime import date, datetime, timedelta
from typing import Any, Dict

try:
    from aqt import appVersion, mw
except Exception:  # pragma: no cover - used only outside Anki runtime.
    appVersion = ""
    mw = None

from .identity import utc_now_iso
from .version import CLIENT_VERSION, PROJECT_KEY, PUBLIC_PROJECT_NAME, SCHEMA_VERSION

IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff"}
AUD_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac", ".opus"}
VID_EXT = {".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v"}


def enrich_payload(base_payload: Dict[str, Any], global_config: Dict[str, Any], survey_id: str, primary_source: str) -> Dict[str, Any]:
    """Inject mandatory backend fields and shared census metadata into a payload built by any host add-on."""
    payload = dict(base_payload or {})
    payload["survey_id"] = survey_id
    payload["schema_version"] = SCHEMA_VERSION
    payload["addon_version"] = CLIENT_VERSION
    payload.setdefault("submitted_at_client", utc_now_iso())
    payload.setdefault("mode", "embedded_preview")
    payload["user_id"] = str(global_config.get("user_id", "") or "")

    # Keep global-project keys for local preview and debugging screens.
    payload["project"] = PROJECT_KEY
    payload["project_display_name"] = PUBLIC_PROJECT_NAME
    payload["anonymous_user_id"] = global_config.get("anonymous_user_id", "")
    payload["source_addons_detected"] = sorted((global_config.get("registered_sources") or {}).keys())
    payload["primary_source"] = primary_source
    payload["censo_client_version"] = CLIENT_VERSION
    return payload


def current_survey_id() -> str:
    """Return survey id using the same semester-window routing used by the standalone add-on scheduler."""
    today = date.today()
    year = today.year
    windows = [
        (f"census-anki-{year}-1", date(year, 6, 1), date(year, 6, 10)),
        (f"census-anki-{year}-2", date(year, 12, 10), date(year, 12, 20)),
    ]
    for survey_id, start, end in windows:
        if start <= today <= end:
            return survey_id
        if start - timedelta(days=10) <= today < start:
            return survey_id
    future = [(survey_id, start, end) for survey_id, start, end in windows if today <= end]
    if not future:
        return f"census-anki-{year + 1}-1"
    return future[0][0]


def _safe_scalar(sql: str, *args: Any, default: int = 0) -> int:
    """Run a scalar SQL query safely and return integer fallback on any runtime failure."""
    if not mw or not getattr(mw, "col", None):
        return default
    try:
        return int(mw.col.db.scalar(sql, *args) or 0)
    except Exception:
        return default


def _collect_environment() -> Dict[str, Any]:
    """Collect runtime environment metadata comparable to standalone collection but without personal identifiers."""
    qt_version = ""
    qt_major = "unknown"
    try:
        from aqt.qt import QT_VERSION_STR

        qt_version = str(QT_VERSION_STR)
        qt_major = str(QT_VERSION_STR).split(".")[0]
    except Exception:
        pass

    return {
        "anki_version": str(appVersion or ""),
        "qt_version": qt_version,
        "platform": (platform.system() or "unknown").lower(),
        "platform_release": platform.release() or "unknown",
        "python_major_version": str(sys.version_info.major),
        "qt_major_version": qt_major,
        "machine": platform.machine() or "unknown",
    }


def _collect_profile_optional(global_config: Dict[str, Any]) -> Dict[str, Any]:
    """Expose optional profile metadata structure so embedded payload shape matches standalone expectations."""
    values = deepcopy(global_config.get("profile") or {})
    updated_at = deepcopy(global_config.get("profile_updated_at") or {})
    return {"values": values, "updated_at": updated_at}


def _addons_dir() -> str:
    """Resolve the add-ons base directory with compatibility fallbacks across Anki versions."""
    if not mw or not getattr(mw, "addonManager", None):
        return ""
    manager = mw.addonManager
    for attr in ("addonsFolder",):
        try:
            path = getattr(manager, attr)()
            if path and os.path.isdir(path):
                return path
        except Exception:
            pass
    try:
        path = mw.pm.addonFolder()
        if path and os.path.isdir(path):
            return path
    except Exception:
        pass
    return ""


def _read_json_file(path: str) -> Dict[str, Any]:
    """Read a JSON file safely and return an empty dict on parse or IO errors."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _collect_addons() -> Dict[str, Any]:
    """Collect add-on inventory metadata using AddonManager with robust compatibility fallbacks."""
    if not mw or not getattr(mw, "addonManager", None):
        return {"count": 0, "items": []}

    manager = mw.addonManager
    base_dir = _addons_dir()
    addon_folders = []
    try:
        addon_folders = manager.allAddons() if hasattr(manager, "allAddons") else []
    except Exception:
        addon_folders = []

    items = []
    for folder in addon_folders or []:
        folder_name = str(folder)
        if folder_name.startswith("__"):
            continue

        enabled = True
        try:
            if hasattr(manager, "addonEnabled"):
                enabled = bool(manager.addonEnabled(folder_name))
        except Exception:
            enabled = True

        manifest = {}
        try:
            manifest = manager.addonManifest(folder_name) if hasattr(manager, "addonManifest") else {}
        except Exception:
            manifest = {}

        manifest_fs = _read_json_file(os.path.join(base_dir, folder_name, "manifest.json")) if base_dir else {}
        meta_fs = _read_json_file(os.path.join(base_dir, folder_name, "meta.json")) if base_dir else {}
        display_name = str(
            (manifest or {}).get("name")
            or manifest_fs.get("name")
            or meta_fs.get("name")
            or folder_name
        )
        version = str((manifest or {}).get("version") or "")
        items.append(
            {
                "id": folder_name,
                "name": display_name,
                "version": version,
                "enabled": bool(enabled),
            }
        )

    return {"count": len(items), "items": items}


def _collect_collection() -> Dict[str, Any]:
    """Collect aggregate collection counters and queue-state totals without extracting user content or names."""
    if not mw or not getattr(mw, "col", None):
        return {}

    deck_count = 0
    note_type_count = 0
    try:
        deck_count = len(mw.col.decks.all_names_and_ids(skip_empty_default=False, include_filtered=False))
    except Exception:
        try:
            deck_count = len(mw.col.decks.all())
        except Exception:
            deck_count = 0

    try:
        note_type_count = len(mw.col.models.all_names_and_ids())
    except Exception:
        try:
            note_type_count = len(mw.col.models.all())
        except Exception:
            note_type_count = 0

    today_due = 0
    try:
        sched_today = int(getattr(mw.col.sched, "today", 0) or 0)
        today_due = _safe_scalar("select count() from cards where queue = 2 and due <= ?", sched_today, default=0)
    except Exception:
        today_due = 0

    return {
        "card_count": _safe_scalar("select count() from cards"),
        "note_count": _safe_scalar("select count() from notes"),
        "deck_count": deck_count,
        "note_type_count": note_type_count,
        "tag_count": _safe_scalar("select count(distinct tag) from tags"),
        "new_cards": _safe_scalar("select count() from cards where queue = 0"),
        "learning_cards": _safe_scalar("select count() from cards where queue in (1,3)"),
        "review_cards": _safe_scalar("select count() from cards where type = 2"),
        "suspended_cards": _safe_scalar("select count() from cards where queue = -1"),
        "buried_cards": _safe_scalar("select count() from cards where queue in (-2,-3)"),
        "due_today": today_due,
    }


def _collect_scheduling() -> Dict[str, Any]:
    """Collect scheduling and deck-option aggregate values inspired by the standalone census collectors."""
    if not mw or not getattr(mw, "col", None):
        return {}

    desired_retention = None
    max_new_per_day = 0
    max_reviews_per_day = 0
    preset_count = 0
    fsrs_markers = []

    def _as_bool_marker(value: Any) -> Any:
        """Convert heterogeneous config marker values to bool when possible, otherwise return None."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            marker = value.strip().lower()
            if marker in {"true", "yes", "y", "1", "enabled", "on"}:
                return True
            if marker in {"false", "no", "n", "0", "disabled", "off"}:
                return False
        return None

    def _config_value(key: str) -> Any:
        """Read a collection config value with safe fallback."""
        try:
            return mw.col.get_config(key)
        except Exception:
            return None

    def _global_fsrs_enabled() -> Any:
        """Best-effort global FSRS detection from collection config keys."""
        for key in ("fsrs", "fsrsEnabled", "fsrs_enabled", "enable_fsrs", "enableFsrs"):
            marker = _as_bool_marker(_config_value(key))
            if marker is not None:
                return marker
        return None

    def _preset_fsrs_enabled(conf: Dict[str, Any]) -> Any:
        """Detect FSRS marker inside a deck preset, including nested scheduler sections."""
        keys = ("fsrs", "fsrsEnabled", "fsrs_enabled", "enable_fsrs", "enableFsrs", "fsrsActivated", "fsrs_activated", "use_fsrs", "useFsrs")
        for key in keys:
            if key in conf:
                marker = _as_bool_marker(conf.get(key))
                if marker is not None:
                    return marker
        for section in ("scheduler", "scheduling", "rev", "new"):
            nested = conf.get(section)
            if isinstance(nested, dict):
                for key in keys:
                    if key in nested:
                        marker = _as_bool_marker(nested.get(key))
                        if marker is not None:
                            return marker
        return None

    try:
        confs = mw.col.decks.all_config()
    except Exception:
        confs = []

    preset_count = len(confs)
    for conf in confs:
        try:
            new_per_day = int(((conf or {}).get("new") or {}).get("perDay", 0) or 0)
            max_new_per_day = max(max_new_per_day, new_per_day)
        except Exception:
            pass
        try:
            rev_per_day = int(((conf or {}).get("rev") or {}).get("perDay", 0) or 0)
            max_reviews_per_day = max(max_reviews_per_day, rev_per_day)
        except Exception:
            pass

        if desired_retention is None:
            desired_retention = (conf or {}).get("desiredRetention") or (conf or {}).get("desired_retention")

        marker = _preset_fsrs_enabled(conf or {})
        if marker is not None:
            fsrs_markers.append(bool(marker))

    global_fsrs = _global_fsrs_enabled()
    if fsrs_markers:
        fsrs_enabled_presets = sum(1 for value in fsrs_markers if value)
        fsrs_enabled = fsrs_enabled_presets > 0
        ratio = round((fsrs_enabled_presets / len(fsrs_markers)) * 100, 2)
    elif global_fsrs is not None and preset_count > 0:
        fsrs_enabled = bool(global_fsrs)
        fsrs_enabled_presets = preset_count if fsrs_enabled else 0
        ratio = 100.0 if fsrs_enabled else 0.0
    else:
        fsrs_enabled = False
        fsrs_enabled_presets = 0
        ratio = None

    return {
        "fsrs_enabled": fsrs_enabled,
        "fsrs_enabled_preset_ratio": ratio,
        "fsrs_enabled_preset_count": fsrs_enabled_presets,
        "fsrs_preset_total_count": preset_count,
        "desired_retention": desired_retention,
        "max_new_cards_per_day": max_new_per_day,
        "max_reviews_per_day": max_reviews_per_day,
        "deck_preset_count": preset_count,
    }


def _collect_activity() -> Dict[str, Any]:
    """Collect compact review activity summaries for today, last 30 days, and last 180 days."""
    if not mw or not getattr(mw, "col", None):
        return {}

    now_ms = int(datetime.utcnow().timestamp() * 1000)
    day_ms = 24 * 60 * 60 * 1000
    cutoff_30 = now_ms - (30 * day_ms)
    cutoff_180 = now_ms - (180 * day_ms)

    def _summary(cutoff: int) -> Dict[str, Any]:
        """Aggregate revlog rows from the cutoff timestamp to now."""
        try:
            rows = mw.col.db.all("select id, ease, time from revlog where id >= ?", cutoff)
        except Exception:
            rows = []

        total = len(rows)
        if total == 0:
            return {
                "reviews": 0,
                "study_days": 0,
                "study_time_minutes": 0,
                "avg_answer_seconds": 0,
                "again_rate": 0,
                "hard_rate": 0,
                "good_rate": 0,
                "easy_rate": 0,
            }

        days = set(datetime.fromtimestamp(int(r[0]) / 1000).date().isoformat() for r in rows)
        total_time_ms = sum(max(int(r[2] or 0), 0) for r in rows)
        ease_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for row in rows:
            ease = int(row[1] or 0)
            ease_counts[ease] = ease_counts.get(ease, 0) + 1

        return {
            "reviews": total,
            "study_days": len(days),
            "study_time_minutes": round(total_time_ms / 60000, 2),
            "avg_answer_seconds": round((total_time_ms / 1000) / total, 2),
            "again_rate": round((ease_counts.get(1, 0) / total) * 100, 2),
            "hard_rate": round((ease_counts.get(2, 0) / total) * 100, 2),
            "good_rate": round((ease_counts.get(3, 0) / total) * 100, 2),
            "easy_rate": round((ease_counts.get(4, 0) / total) * 100, 2),
        }

    today_cutoff = now_ms - day_ms
    return {
        "reviews_today": _safe_scalar("select count() from revlog where id >= ?", today_cutoff, default=0),
        "last_30_days": _summary(cutoff_30),
        "last_180_days": _summary(cutoff_180),
    }


def _collect_templates() -> Dict[str, Any]:
    """Collect note-type and template usage indicators without exposing template contents."""
    if not mw or not getattr(mw, "col", None):
        return {}

    has_cloze = False
    model_count = 0
    card_template_count = 0
    has_css = False
    has_js = False

    try:
        models = mw.col.models.all()
    except Exception:
        models = []

    model_count = len(models)
    for model in models:
        is_cloze = int((model or {}).get("type", 0) or 0) == 1 or "cloze" in str((model or {}).get("name", "")).lower()
        if is_cloze:
            has_cloze = True
        css = str((model or {}).get("css", "") or "")
        if len(css.strip()) > 20:
            has_css = True
        for tmpl in (model or {}).get("tmpls", []) or []:
            card_template_count += 1
            content = (str((tmpl or {}).get("qfmt", "") or "") + "\n" + str((tmpl or {}).get("afmt", "") or "")).lower()
            if "<script" in content or "javascript:" in content:
                has_js = True

    return {
        "uses_cloze": has_cloze,
        "note_type_count": model_count,
        "card_template_count": card_template_count,
        "uses_css_customization": has_css,
        "uses_javascript_in_templates": has_js,
    }


def _collect_media() -> Dict[str, Any]:
    """Collect media-folder aggregate signals and note-level media-presence ratios with safe fallbacks."""
    if not mw or not getattr(mw, "col", None):
        return {}

    total = images = audio = video = size_bytes = 0
    media_dir = None
    try:
        media_dir = mw.col.media.dir()
    except Exception:
        media_dir = None

    if media_dir and os.path.isdir(media_dir):
        for root, _dirs, files in os.walk(media_dir):
            for filename in files:
                if filename.startswith("_"):
                    continue
                total += 1
                ext = os.path.splitext(filename)[1].lower()
                if ext in IMG_EXT:
                    images += 1
                elif ext in AUD_EXT:
                    audio += 1
                elif ext in VID_EXT:
                    video += 1
                try:
                    size_bytes += os.path.getsize(os.path.join(root, filename))
                except Exception:
                    pass

    note_rows = []
    try:
        note_rows = mw.col.db.all("select flds from notes limit ?", 20000)
    except Exception:
        note_rows = []

    notes_total = len(note_rows)
    notes_with_images = 0
    notes_with_audio = 0
    notes_with_video = 0
    for (flds,) in note_rows:
        text = str(flds or "").lower()
        if "<img" in text or re.search(r"\.(jpg|jpeg|png|gif|webp|svg|bmp)", text):
            notes_with_images += 1
        if "[sound:" in text or re.search(r"\.(mp3|wav|ogg|m4a|flac|aac|opus)", text):
            notes_with_audio += 1
        if re.search(r"\.(mp4|webm|mov|avi|mkv|m4v)", text):
            notes_with_video += 1

    def _pct(part: int, whole: int) -> float:
        """Return percentage with two decimals or zero when denominator is zero."""
        if whole <= 0:
            return 0.0
        return round((part / whole) * 100, 2)

    return {
        "media_file_count": total,
        "media_folder_size_mb": round(size_bytes / (1024 * 1024), 2),
        "image_file_ratio": _pct(images, total),
        "audio_file_ratio": _pct(audio, total),
        "video_file_ratio": _pct(video, total),
        "notes_with_images_ratio": _pct(notes_with_images, notes_total),
        "notes_with_audio_ratio": _pct(notes_with_audio, notes_total),
        "notes_with_video_ratio": _pct(notes_with_video, notes_total),
    }


def _build_analysis(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a stable analysis fingerprint compatible with standalone-style analytics workflows."""
    source = {
        "collection": deepcopy(payload.get("collection") or {}),
        "scheduling": deepcopy(payload.get("scheduling") or {}),
        "activity": deepcopy(payload.get("activity") or {}),
        "templates": deepcopy(payload.get("templates") or {}),
        "media": deepcopy(payload.get("media") or {}),
    }
    canonical = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).digest()
    code = base64.b32encode(digest).decode("ascii").rstrip("=")[:10]
    return {
        "usage_fingerprint_version": "embedded-1.0",
        "usage_fingerprint": code,
    }


def build_payload_preview(global_config: Dict[str, Any], survey_id: str, primary_source: str) -> Dict[str, Any]:
    """Return a detailed preview payload shaped like standalone output for embedded debug and troubleshooting."""
    base_payload = {
        "environment": _collect_environment(),
        "profile_optional": _collect_profile_optional(global_config),
        "addons": _collect_addons(),
        "collection": _collect_collection(),
        "scheduling": _collect_scheduling(),
        "activity": _collect_activity(),
        "templates": _collect_templates(),
        "media": _collect_media(),
        "stats": {},
    }
    payload = enrich_payload(base_payload, global_config, survey_id=survey_id, primary_source=primary_source)
    payload["analysis"] = _build_analysis(payload)
    return payload
