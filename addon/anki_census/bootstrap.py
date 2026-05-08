from aqt import mw
from aqt.qt import QAction, QTimer
from . import storage
from .constants import ADDON_NAME
from .storage import load_config, mark_first_run_completed
from .i18n import t
from .censo_client import init_censo_client


def _open_main_window(initial_tab=None):
    """Open the main window using a relative import compatible with Anki add-on folders."""
    from .ui.main_window import show_main_window
    show_main_window(initial_tab=initial_tab)


def _welcome_if_needed():
    """Show the first-run notice once and guide the user to the profile tab."""
    from aqt.qt import QMessageBox

    cfg = load_config()
    if cfg.get("local_state", {}).get("first_run_completed"):
        return False
    lang = cfg.get("language", "en")
    QMessageBox.information(mw, t("welcome_title", lang), t("welcome_text", lang))
    mark_first_run_completed()
    _open_main_window(initial_tab="profile")
    return True


def init(addon_module_name: str):
    """Initialize standalone mode while delegating singleton and global config to censo_client."""
    storage.set_addon_module_name(addon_module_name)

    action = QAction(ADDON_NAME, mw)
    action.triggered.connect(lambda: _open_main_window())
    mw.form.menuTools.addAction(action)

    def startup():
        def later():
            first = _welcome_if_needed()
            if not first:
                from .scheduler import run_startup_tasks

                run_startup_tasks()

        QTimer.singleShot(1500, later)

    init_censo_client(
        source_addon_id="anki-census-standalone",
        source_addon_name=ADDON_NAME,
        source_addon_version=storage.load_config().get("addon_version", "0.1.12"),
        startup_callback=startup,
    )

