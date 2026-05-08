from __future__ import annotations

from datetime import date, datetime, timedelta

from aqt import mw
from aqt.qt import QMessageBox, QTimer

from .i18n import t
from .payload_builder import build_payload
from .sender import submit_payload
from .storage import has_sent, load_config, mark_pending, mark_reminder, mark_sent, was_reminder_shown


def current_survey_for_day(today: date | None = None):
    """Return survey window metadata for the current day."""
    today = today or date.today()
    year = today.year
    windows = [
        (f"census-anki-{year}-1", date(year, 6, 1), date(year, 6, 10)),
        (f"census-anki-{year}-2", date(year, 12, 10), date(year, 12, 20)),
    ]
    for survey_id, start, end in windows:
        if start <= today <= end:
            return {"survey_id": survey_id, "start": start, "end": end, "phase": "collection"}
        if start - timedelta(days=10) <= today < start:
            return {"survey_id": survey_id, "start": start, "end": end, "phase": "pre_reminder"}
    future = [(survey_id, start, end) for survey_id, start, end in windows if today <= end]
    if not future:
        return {"survey_id": f"census-anki-{year + 1}-1", "start": date(year + 1, 6, 1), "end": date(year + 1, 6, 10), "phase": "none"}
    survey_id, start, end = future[0]
    return {"survey_id": survey_id, "start": start, "end": end, "phase": "none"}


def show_profile_reminder(phase_info):
    """Show reminder dialogs before and during survey windows."""
    cfg = load_config()
    lang = cfg.get("language", "en")
    survey_id = phase_info["survey_id"]
    phase = phase_info["phase"]
    if was_reminder_shown(survey_id, phase):
        return
    if phase == "pre_reminder":
        title, text = t("profile_reminder_title", lang), t("profile_reminder_text", lang)
    else:
        title, text = t("collection_start_title", lang), t("collection_start_text", lang)
    box = QMessageBox(mw)
    box.setWindowTitle(title)
    box.setText(text)
    open_btn = box.addButton(t("open_profile", lang), QMessageBox.ButtonRole.AcceptRole)
    box.addButton(t("close", lang), QMessageBox.ButtonRole.RejectRole)
    box.exec()
    mark_reminder(survey_id, phase)
    if box.clickedButton() == open_btn:
        from .ui.main_window import show_main_window

        show_main_window(initial_tab="profile")


def _notice_allows_submission(cfg: dict) -> bool:
    """Block submission until first notice metadata is available."""
    if not cfg.get("notice_seen"):
        return False
    first_allowed = cfg.get("first_send_allowed_after")
    if not first_allowed:
        return False
    try:
        return datetime.fromisoformat(first_allowed.replace("Z", "+00:00")) <= datetime.utcnow().astimezone()
    except Exception:
        return False


def silent_submit_if_needed(phase_info):
    """Submit only once per survey when participation is active and notice allows it."""
    cfg = load_config()
    if cfg.get("participation_paused"):
        return
    if not _notice_allows_submission(cfg):
        return
    if phase_info.get("phase") != "collection":
        return
    survey_id = phase_info["survey_id"]
    if has_sent(survey_id):
        return
    try:
        payload = build_payload(survey_id, mode="real")
        result = submit_payload(payload)
        if result.get("ok"):
            mark_sent(survey_id)
        else:
            mark_pending(survey_id, result.get("error", "Unknown error"))
    except Exception as exc:
        mark_pending(survey_id, exc)


def run_startup_tasks():
    """Run lightweight startup tasks after Anki startup settles."""
    info = current_survey_for_day()
    if info["phase"] in ("pre_reminder", "collection"):
        show_profile_reminder(info)
    QTimer.singleShot(3000, lambda: silent_submit_if_needed(info))

