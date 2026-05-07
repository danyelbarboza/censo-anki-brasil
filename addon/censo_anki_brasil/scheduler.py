from __future__ import annotations
from datetime import date, datetime, timedelta
from aqt.qt import QTimer, QMessageBox
from aqt import mw
from .storage import load_config, mark_reminder, was_reminder_shown, has_sent, mark_sent, mark_pending
from .payload_builder import build_payload
from .sender import submit_payload
from .i18n import t


def current_survey_for_day(today: date | None = None):
    today = today or date.today()
    y = today.year
    windows = [
        (f"censo-anki-brasil-{y}-1", date(y, 6, 1), date(y, 6, 10)),
        (f"censo-anki-brasil-{y}-2", date(y, 12, 10), date(y, 12, 20)),
    ]
    for sid, start, end in windows:
        if start <= today <= end:
            return {"survey_id": sid, "start": start, "end": end, "phase": "collection"}
        if start - timedelta(days=10) <= today < start:
            return {"survey_id": sid, "start": start, "end": end, "phase": "pre_reminder"}
    # next survey for panel
    future = [(sid,start,end) for sid,start,end in windows if today <= end]
    if not future:
        return {"survey_id": f"censo-anki-brasil-{y+1}-1", "start": date(y+1,6,1), "end": date(y+1,6,10), "phase": "none"}
    sid,start,end = future[0]
    return {"survey_id": sid, "start": start, "end": end, "phase": "none"}

def show_profile_reminder(phase_info):
    cfg = load_config()
    lang = cfg.get("language", "pt_BR")
    sid = phase_info["survey_id"]
    phase = phase_info["phase"]
    if was_reminder_shown(sid, phase):
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
    mark_reminder(sid, phase)
    if box.clickedButton() == open_btn:
        from .ui.main_window import show_main_window
        show_main_window(initial_tab="profile")

def silent_submit_if_needed(phase_info):
    cfg = load_config()
    if cfg.get("participation_paused"):
        return
    if phase_info.get("phase") != "collection":
        return
    sid = phase_info["survey_id"]
    if has_sent(sid):
        return
    try:
        payload = build_payload(sid, mode="real")
        result = submit_payload(payload)
        if result.get("ok"):
            mark_sent(sid)
        else:
            mark_pending(sid, result.get("error", "Erro desconhecido"))
    except Exception as e:
        mark_pending(sid, e)

def run_startup_tasks():
    info = current_survey_for_day()
    if info["phase"] in ("pre_reminder", "collection"):
        show_profile_reminder(info)
    # delay submission a bit so Anki finishes startup
    QTimer.singleShot(3000, lambda: silent_submit_if_needed(info))
