"""Integration example that mirrors the Dynamic Deadline census-tab pattern.

This file is intentionally self-contained so host add-ons can copy-paste the
same integration style with minimal adjustments.
"""

from __future__ import annotations

from typing import Any

from aqt.qt import QTabWidget, QVBoxLayout, QWidget

from . import CensusSettingsTab, init_censo_client


def build_dialog_tabs(host_settings_widget: QWidget, source_addon_id: str, source_addon_name: str, source_addon_version: str) -> QTabWidget:
    """Build a tab widget with host settings and a dedicated Anki Census tab.

    Parameters
    ----------
    host_settings_widget:
        Main settings widget owned by the host add-on.
    source_addon_id:
        Stable technical id of the host add-on.
    source_addon_name:
        Public display name of the host add-on.
    source_addon_version:
        Host add-on version string.

    Returns
    -------
    QTabWidget
        Ready-to-use tabs with the host tab plus the Anki Census tab.
    """
    censo = None
    try:
        censo = init_censo_client(
            source_addon_id=source_addon_id,
            source_addon_name=source_addon_name,
            source_addon_version=source_addon_version,
        )
    except Exception:
        censo = None

    tabs = QTabWidget()
    tabs.addTab(host_settings_widget, "Settings")
    tabs.addTab(CensusSettingsTab(censo_client=censo), "Anki Census")
    return tabs


def mount_tabs_into_dialog(dialog: QWidget, tabs: QTabWidget) -> None:
    """Attach prepared tabs to a dialog container using a simple vertical layout."""
    layout = QVBoxLayout(dialog)
    layout.addWidget(tabs)
    dialog.setLayout(layout)
