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

USAGE_FINGERPRINT_VERSION = "1.1"


def _canonical_json(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash_to_code(data: dict, length: int = 10) -> str:
    digest = hashlib.sha256(_canonical_json(data).encode("utf-8")).digest()
    return base64.b32encode(digest).decode("ascii").rstrip("=")[:length]


def _percent_label_to_float(value):
    if not isinstance(value, str):
        return None
    text = value.strip().replace(",", ".")
    if not text.endswith("%"):
        return None
    text = text[:-1].strip()
    # Exact percentages look like "92.37%" or "92%". Bucket labels such as
    # "90–95%" or ">0–5%" must stay untouched.
    if "–" in text or "-" in text or text.startswith(">") or text.startswith("<"):
        return None
    try:
        return float(text)
    except Exception:
        return None


def _stable_percent_bucket(value):
    pct = _percent_label_to_float(value)
    if pct is None:
        return value
    if pct <= 0:
        return "0%"
    if pct > 100:
        pct = 100
    upper = 5
    while upper < 100:
        if pct <= upper:
            lower = upper - 5
            if lower == 0:
                return ">0–5%"
            return f"{lower}–{upper}%"
        upper += 5
    return "95–100%"


def _coarse_count_label_for_hash(value):
    """Normalize volatile count buckets inside the fingerprint only.

    The public payload remains granular. This function prevents unstable fields
    such as due_today/learning cards from changing the deduplication hash just
    because two desktops were opened a few days apart.
    """
    if not isinstance(value, str):
        return value
    if value in {"unknown", "sem limite"}:
        return value
    if value == "0":
        return "0"
    # Extract the largest numeric value present in a label like "4.001–5.000".
    import re
    nums = re.findall(r"\d+(?:\.\d+)?", value)
    if not nums:
        return value
    parsed = []
    for n in nums:
        try:
            parsed.append(int(n.replace(".", "")))
        except Exception:
            pass
    if not parsed:
        return value
    high = max(parsed)
    if high <= 100:
        return "1–100"
    if high <= 500:
        return "101–500"
    if high <= 1000:
        return "501–1.000"
    if high <= 2500:
        return "1.001–2.500"
    if high <= 5000:
        return "2.501–5.000"
    if high <= 10000:
        return "5.001–10.000"
    if high <= 25000:
        return "10.001–25.000"
    if high <= 50000:
        return "25.001–50.000"
    if high <= 100000:
        return "50.001–100.000"
    return "100.001+"


def _stabilize_fingerprint_source(source: dict) -> dict:
    stable = deepcopy(source)

    # Exact retention values are excellent for analysis but too sensitive for
    # a cross-device deduplication hash. Keep exact values in the payload and
    # use 5-point buckets only inside the fingerprint source.
    scheduling = stable.get("scheduling") or {}
    if "desired_retention_bucket" in scheduling:
        scheduling["desired_retention_bucket"] = _stable_percent_bucket(scheduling.get("desired_retention_bucket"))

    for period in (stable.get("activity") or {}).values():
        if isinstance(period, dict) and "retention_bucket" in period:
            period["retention_bucket"] = _stable_percent_bucket(period.get("retention_bucket"))
        if isinstance(period, dict) and "study_days_bucket" in period:
            period["study_days_bucket"] = _coarse_count_label_for_hash(period.get("study_days_bucket"))

    # These collection fields can legitimately drift between two desktops opened
    # days apart. They still enter the hash, but in a coarser/stable form.
    collection = stable.get("collection") or {}
    for key in ("due_today_bucket", "learning_cards_bucket"):
        if key in collection:
            collection[key] = _coarse_count_label_for_hash(collection.get(key))

    return stable


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
    activity.pop("semester_months", None)

    source = {
        "collection": deepcopy(payload.get("collection") or {}),
        "scheduling": deepcopy(payload.get("scheduling") or {}),
        "activity": activity,
        "templates": deepcopy(payload.get("templates") or {}),
        "media": deepcopy(payload.get("media") or {}),
    }
    return _stabilize_fingerprint_source(source)


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
