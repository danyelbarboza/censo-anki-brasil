import base64
import hashlib
import json
from copy import deepcopy

from .constants import ADDON_VERSION, SCHEMA_VERSION
from .ids import ensure_user_id
from .storage import utc_now_iso
from .collectors.environment import collect_environment
from .collectors.addons import collect_addons
from .collectors.collection import collect_collection
from .collectors.scheduling import collect_scheduling
from .collectors.activity import collect_activity
from .collectors.media import collect_media
from .collectors.templates import collect_templates
from .collectors.profile import collect_profile

USAGE_FINGERPRINT_VERSION = "1.0"


def _canonical_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_to_code(data: dict, length: int = 10) -> str:
    digest = hashlib.sha256(_canonical_json(data).encode("utf-8")).digest()
    return base64.b32encode(digest).decode("ascii").rstrip("=")[:length]


def _build_usage_fingerprint_source(payload: dict) -> dict:
    """
    Fingerprint rules requested for deduplication across multiple desktops.

    Excluded:
    - survey_id
    - profile_optional / profile, including updated_at
    - activity.last_30_days
    - user_id, submitted_at_client, mode
    - addon_version, schema_version
    - environment
    - addons
    - analysis

    Included:
    - collection
    - scheduling
    - activity without last_30_days, currently last_180_days
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


def _build_analysis(payload: dict) -> dict:
    source = _build_usage_fingerprint_source(payload)
    return {
        "usage_fingerprint_version": USAGE_FINGERPRINT_VERSION,
        "usage_fingerprint": _hash_to_code(source, length=10),
    }


def build_payload(survey_id: str, mode: str = "real") -> dict:
    payload = {
        "survey_id": survey_id,
        "schema_version": SCHEMA_VERSION,
        "addon_version": ADDON_VERSION,
        "submitted_at_client": utc_now_iso(),
        "mode": mode,
        "user_id": ensure_user_id(),
        "environment": collect_environment(),
        "profile_optional": collect_profile(),
        "addons": collect_addons(),
        "collection": collect_collection(),
        "scheduling": collect_scheduling(),
        "activity": collect_activity(),
        "templates": collect_templates(),
        "media": collect_media(),
    }

    # Add this as the final step so later collector changes cannot overwrite it.
    payload["analysis"] = _build_analysis(payload)
    return payload
