"""Transport guard helpers for once-per-survey submission semantics."""

from __future__ import annotations

from .identity import utc_now_iso


def can_submit_survey(global_config: dict, survey_id: str) -> bool:
    """Return True only when this profile has not submitted this survey yet."""
    submissions = global_config.get("last_submission") or {}
    return survey_id not in submissions


def mark_submitted(global_config: dict, survey_id: str, source_addon_id: str) -> dict:
    """Store survey submission marker with timestamp and source metadata."""
    submissions = global_config.setdefault("last_submission", {})
    submissions[survey_id] = {
        "submitted_at": utc_now_iso(),
        "source_addon_id": source_addon_id,
    }
    return global_config
