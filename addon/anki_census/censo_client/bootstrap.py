"""Bootstrap entrypoint for reusable, global-safe Anki Census initialization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict

try:
    from aqt import mw
except Exception:  # pragma: no cover - used only outside Anki runtime.
    mw = None

from .collector import GlobalCollector
from .config import load_global_config, register_source, save_global_config
from .identity import normalize_source_id
from .payload import build_payload_preview
from .privacy import build_privacy_summary
from .version import (
    NEW_GLOBAL_COLLECTOR_ATTR,
    NEW_GLOBAL_STATE_ATTR,
    OLD_GLOBAL_COLLECTOR_ATTR,
    OLD_GLOBAL_STATE_ATTR,
)

STANDALONE_ADDON_IDS = {"1777300027", "anki-census"}
STANDALONE_MARKERS = {"anki_census"}


@dataclass
class CensoClient:
    """Public runtime facade for embedded add-ons and the standalone package."""

    source_addon_id: str

    def is_participation_paused(self) -> bool:
        """Return whether global participation is currently paused in shared config."""
        return bool(load_global_config().get("participation_paused", False))

    def set_participation_paused(self, paused: bool) -> None:
        """Set the global participation flag respected by all embedded/standalone clients."""
        config = load_global_config()
        config["participation_paused"] = bool(paused)
        save_global_config(config)

    def get_privacy_summary(self) -> Dict[str, Any]:
        """Return a user-facing privacy summary from the shared global config."""
        return build_privacy_summary(load_global_config())

    def get_current_payload_preview(self, survey_id: str = "anki-census-preview") -> Dict[str, Any]:
        """Return a minimal payload preview with source and project metadata."""
        config = load_global_config()
        collector = _get_global_collector()
        primary_source = collector.primary_source if collector else self.source_addon_id
        return build_payload_preview(config, survey_id=survey_id, primary_source=primary_source)


def _get_mw() -> Any:
    """Return Anki main window object when available."""
    return mw


def _get_runtime_attr(*names: str) -> Any:
    """Return the first existing runtime attribute from `aqt.mw`."""
    anki_mw = _get_mw()
    if not anki_mw:
        return None
    for name in names:
        if hasattr(anki_mw, name):
            return getattr(anki_mw, name)
    return None


def _set_runtime_alias(value: Any, *names: str) -> None:
    """Write a value to all runtime attribute aliases for old/new compatibility."""
    anki_mw = _get_mw()
    if not anki_mw:
        return
    for name in names:
        setattr(anki_mw, name, value)


def _get_global_collector() -> GlobalCollector | None:
    """Get existing collector from new/legacy runtime markers."""
    existing = _get_runtime_attr(NEW_GLOBAL_COLLECTOR_ATTR, OLD_GLOBAL_COLLECTOR_ATTR)
    if existing:
        _set_runtime_alias(existing, NEW_GLOBAL_COLLECTOR_ATTR, OLD_GLOBAL_COLLECTOR_ATTR)
    return existing


def _detect_standalone_installed() -> bool:
    """Best-effort standalone detection using AddonManager across Anki versions."""
    anki_mw = _get_mw()
    manager = getattr(anki_mw, "addonManager", None) if anki_mw else None
    if not manager:
        return False

    for addon_id in STANDALONE_ADDON_IDS:
        try:
            if hasattr(manager, "isAddonInstalled") and manager.isAddonInstalled(addon_id):
                return True
        except Exception:
            pass

    try:
        addon_folders = manager.allAddons() if hasattr(manager, "allAddons") else []
    except Exception:
        addon_folders = []

    for folder in addon_folders or []:
        folder_text = str(folder).lower()
        if folder_text in STANDALONE_ADDON_IDS or folder_text in STANDALONE_MARKERS:
            return True
        try:
            manifest = manager.addonManifest(str(folder)) if hasattr(manager, "addonManifest") else None
            name_text = str((manifest or {}).get("name", "")).lower()
            package_text = str((manifest or {}).get("package", "")).lower()
            if any(marker in name_text or marker in package_text for marker in STANDALONE_MARKERS):
                return True
        except Exception:
            continue
    return False


def _ensure_collector(source_id: str) -> GlobalCollector:
    """Create or reuse global collector and preserve old/new runtime aliases."""
    existing = _get_global_collector()
    if existing:
        existing.register_source(source_id)
        return existing

    collector = GlobalCollector(primary_source=source_id)
    collector.register_source(source_id)
    _set_runtime_alias(collector, NEW_GLOBAL_COLLECTOR_ATTR, OLD_GLOBAL_COLLECTOR_ATTR)
    _set_runtime_alias(
        {
            "created_by": source_id,
            "standalone_detected": _detect_standalone_installed(),
        },
        NEW_GLOBAL_STATE_ATTR,
        OLD_GLOBAL_STATE_ATTR,
    )
    return collector


def init_censo_client(
    source_addon_id: str,
    source_addon_name: str,
    source_addon_version: str,
    startup_callback: Callable[[], None] | None = None,
) -> CensoClient:
    """Initialize Anki Census idempotently and register the caller as a source addon."""
    source_id = normalize_source_id(source_addon_id)
    collector = _ensure_collector(source_id)

    global_config = load_global_config()
    register_source(global_config, source_id, source_addon_name, source_addon_version)
    save_global_config(global_config)

    collector.run_startup_once(startup_callback)
    return CensoClient(source_addon_id=source_id)
