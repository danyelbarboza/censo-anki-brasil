"""Payload helpers for reusable Anki Census metadata."""

from __future__ import annotations

from typing import Any, Dict

from .version import CLIENT_VERSION, PROJECT_KEY, PUBLIC_PROJECT_NAME


def enrich_payload(base_payload: Dict[str, Any], global_config: Dict[str, Any], survey_id: str, primary_source: str) -> Dict[str, Any]:
    """Inject global census metadata into a payload built by the host add-on."""
    payload = dict(base_payload or {})
    payload["project"] = PROJECT_KEY
    payload["project_display_name"] = PUBLIC_PROJECT_NAME
    payload["survey_id"] = survey_id
    payload["anonymous_user_id"] = global_config.get("anonymous_user_id", "")
    payload["source_addons_detected"] = sorted((global_config.get("registered_sources") or {}).keys())
    payload["primary_source"] = primary_source
    payload["censo_client_version"] = CLIENT_VERSION
    return payload


def build_payload_preview(global_config: Dict[str, Any], survey_id: str, primary_source: str) -> Dict[str, Any]:
    """Return a minimal payload preview that embedders can expose in settings/debug screens."""
    return enrich_payload({"stats": {}}, global_config, survey_id=survey_id, primary_source=primary_source)
