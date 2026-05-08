"""Transport helpers for once-per-survey semantics and debug submission compatibility."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict

from .identity import utc_now_iso

DEFAULT_API_BASE_URL = "https://anki-census-api.danyelbarboza.workers.dev"
CLIENT_NAME = "AnkiCensusAddon"


def _survey_id_candidates(survey_id: str) -> list[str]:
    """Return compatibility candidates for survey id migration across backend versions."""
    sid = str(survey_id or "").strip()
    candidates: list[str] = []
    if sid:
        candidates.append(sid)
        if sid.startswith("census-anki-"):
            suffix = sid[len("census-anki-") :]
            candidates.append("anki-census-" + suffix)
            candidates.append("censo-anki-brasil-" + suffix)
        elif sid.startswith("anki-census-"):
            suffix = sid[len("anki-census-") :]
            candidates.append("censo-anki-brasil-" + suffix)
            candidates.append("census-anki-" + suffix)
    # Keep order while deduplicating.
    seen = set()
    ordered = []
    for candidate in candidates:
        if candidate not in seen:
            seen.add(candidate)
            ordered.append(candidate)
    return ordered


def _post_json(path: str, payload: Dict[str, Any], api_base_url: str, timeout: int) -> Dict[str, Any]:
    """Send payload to a census endpoint and parse JSON response."""
    base = str(api_base_url or "").strip().rstrip("/")
    if not base:
        raise RuntimeError("API URL is not configured")

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        base + path,
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"{CLIENT_NAME}/{payload.get('addon_version', 'unknown')}",
            "X-Census-Client": "anki-census-addon",
            "X-Census-Schema": str(payload.get("schema_version", "")),
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=int(timeout)) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw or "{}")


def can_submit_survey(global_config: dict, survey_id: str) -> bool:
    """Return True only when this profile has not submitted this survey (including alias ids) yet."""
    submissions = global_config.get("last_submission") or {}
    for candidate in _survey_id_candidates(survey_id):
        if candidate in submissions:
            return False
    return True


def mark_submitted(global_config: dict, survey_id: str, source_addon_id: str) -> dict:
    """Store survey submission marker with timestamp and source metadata for all compatible survey-id aliases."""
    submissions = global_config.setdefault("last_submission", {})
    marker = {
        "submitted_at": utc_now_iso(),
        "source_addon_id": source_addon_id,
    }
    for candidate in _survey_id_candidates(survey_id):
        submissions[candidate] = marker
    return global_config


def submit_debug_payload(payload: Dict[str, Any], api_base_url: str = DEFAULT_API_BASE_URL, timeout: int = 20) -> Dict[str, Any]:
    """Submit a debug payload with survey-id migration fallback across backend versions."""
    candidates = _survey_id_candidates(str(payload.get("survey_id", "") or ""))
    last_error = ""
    for index, survey_id in enumerate(candidates):
        trial = dict(payload)
        trial["survey_id"] = survey_id
        try:
            data = _post_json("/debug-submit", trial, api_base_url, timeout)
            if index > 0:
                data.setdefault("survey_id_fallback_used", survey_id)
            return data
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            last_error = f"Server returned error {exc.code}: {raw[:500]}"
            if not (exc.code == 400 and "invalid_survey_id" in raw):
                raise RuntimeError(last_error) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc
    raise RuntimeError(last_error or "Survey submission failed")


def submit_payload(payload: Dict[str, Any], api_base_url: str = DEFAULT_API_BASE_URL, timeout: int = 20) -> Dict[str, Any]:
    """Submit a real census payload with survey-id migration fallback across backend versions."""
    candidates = _survey_id_candidates(str(payload.get("survey_id", "") or ""))
    last_error = ""
    for index, survey_id in enumerate(candidates):
        trial = dict(payload)
        trial["survey_id"] = survey_id
        try:
            data = _post_json("/submit", trial, api_base_url, timeout)
            if index > 0:
                data.setdefault("survey_id_fallback_used", survey_id)
            return data
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            last_error = f"Server returned error {exc.code}: {raw[:500]}"
            if not (exc.code == 400 and "invalid_survey_id" in raw):
                raise RuntimeError(last_error) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc.reason}") from exc
    raise RuntimeError(last_error or "Survey submission failed")
