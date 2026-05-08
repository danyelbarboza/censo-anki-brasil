"""Privacy helpers exposed by the reusable client."""

from __future__ import annotations

from typing import Any, Dict


def build_privacy_summary(config: Dict[str, Any]) -> Dict[str, Any]:
    """Build a plain summary that embedders can show in their own settings UI."""
    return {
        "project_name": "Anki Census",
        "project_scope": "Global Anki usage and add-on adoption statistics.",
        "participation_paused": bool(config.get("participation_paused", False)),
        "notice_seen": bool(config.get("notice_seen", False)),
        "fields_not_collected": [
            "card_content",
            "note_content",
            "deck_names",
            "tag_names",
            "field_names",
            "note_type_names",
            "media_file_names",
            "email",
            "real_name",
            "ankiweb_login",
            "local_collection_paths",
        ],
    }
