from aqt import mw
from aqt.qt import QAction, QTimer
from . import storage
from .constants import ADDON_NAME
from .ids import ensure_user_id
from .storage import load_config, mark_first_run_completed
from .i18n import t


def _welcome_if_needed():
    from aqt.qt import QMessageBox
    from .ui.main_window import show_main_window
    cfg = load_config()
    if cfg.get("local_state", {}).get("first_run_completed"):
        return False
    lang = cfg.get("language", "pt_BR")
    QMessageBox.information(mw, t("welcome_title", lang), t("welcome_text", lang))
    mark_first_run_completed()
    show_main_window(initial_tab="profile")
    return True

def init(addon_module_name: str):
    storage.set_addon_module_name(addon_module_name)
    ensure_user_id()
    action = QAction(ADDON_NAME, mw)
    action.triggered.connect(lambda: __import__("censo_anki_brasil.ui.main_window", fromlist=["show_main_window"]).show_main_window())
    mw.form.menuTools.addAction(action)
    def later():
        first = _welcome_if_needed()
        if not first:
            from .scheduler import run_startup_tasks
            run_startup_tasks()
    QTimer.singleShot(1500, later)
