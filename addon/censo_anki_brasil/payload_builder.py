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

def build_payload(survey_id: str, mode: str = "real") -> dict:
    return {
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
