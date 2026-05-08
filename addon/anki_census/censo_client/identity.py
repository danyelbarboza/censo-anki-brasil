"""Utilities for source identity and timestamps."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp without microseconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_source_id(source_addon_id: str) -> str:
    """Normalize source ids so config keys remain stable across callers."""
    return (source_addon_id or "unknown-source").strip().lower()
