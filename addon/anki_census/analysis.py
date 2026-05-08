import base64
import hashlib
import json
from copy import deepcopy

USAGE_FINGERPRINT_VERSION = "1.0"


def _canonical_json(data: dict) -> str:
    """Return a stable JSON representation for hashing."""
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_to_code(data: dict, length: int = 10) -> str:
    """Return an uppercase alphanumeric code derived from SHA-256."""
    digest = hashlib.sha256(_canonical_json(data).encode("utf-8")).digest()
    return base64.b32encode(digest).decode("ascii").rstrip("=")[:length]


def build_usage_fingerprint_source(payload: dict) -> dict:
    """
    Build the exact object used to deduplicate likely duplicate submissions.

    Excluded by design:
    - survey_id
    - profile_optional / profile
    - activity.last_30_days
    - user_id, submitted_at_client, mode
    - addon_version, schema_version
    - environment
    - addons
    - profile_optional.updated_at
    - analysis

    Included by design:
    - collection
    - scheduling
    - activity.last_180_days
    - templates
    - media
    """
    activity = deepcopy(payload.get("activity") or {})
    activity.pop("last_30_days", None)

    return {
        "collection": deepcopy(payload.get("collection") or {}),
        "scheduling": deepcopy(payload.get("scheduling") or {}),
        "activity": activity,
        "templates": deepcopy(payload.get("templates") or {}),
        "media": deepcopy(payload.get("media") or {}),
    }


def build_analysis(payload: dict) -> dict:
    source = build_usage_fingerprint_source(payload)
    return {
        "usage_fingerprint_version": USAGE_FINGERPRINT_VERSION,
        "usage_fingerprint": _hash_to_code(source, length=10),
    }
