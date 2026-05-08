"""Reusable Anki Census settings tab for host add-on configuration dialogs.

This module packages the same UX pattern validated in Dynamic Deadline:
- compact privacy summary
- global opt-out checkbox
- developer unlock area
- JSON preview, save/copy, debug submit, and submission reset actions

Host add-ons can mount this widget as a dedicated tab inside any QTabWidget.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from aqt.qt import QApplication, QFileDialog, QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget, QTextEdit
from aqt.utils import showInfo, showWarning

DEV_PASSWORD = "4599"


class CensusSettingsTab(QWidget):
    """Render a reusable settings tab that controls and debugs the embedded Anki Census client.

    Parameters
    ----------
    censo_client:
        Initialized client returned by ``init_censo_client(...)``. When ``None``,
        the tab stays disabled and displays an unavailable status.
    tr:
        Optional translation callback. Signature must be ``tr(key: str) -> str``.
        When omitted, built-in English strings are used.
    parent:
        Optional Qt parent widget.
    """

    def __init__(self, censo_client: Any = None, tr=None, parent: Optional[QWidget] = None) -> None:
        """Build all controls and wire actions while keeping host add-on failures isolated."""
        super().__init__(parent)
        self._client = censo_client
        self._tr = tr or self._default_tr
        self._debug_unlocked = False
        self._build_ui()
        self._apply_texts()
        self.refresh_state()

    def _default_tr(self, key: str) -> str:
        """Return default English labels for all tab controls and messages."""
        labels = {
            "census_brief": "Anki Census helps improve add-ons with privacy-conscious community insights.",
            "census_pause": "Pause participation globally",
            "census_status_on": "Status: active",
            "census_status_off": "Status: paused",
            "census_status_unavailable": "Status: embedded client unavailable",
            "census_view": "View census status",
            "census_preview_title": "Anki Census status",
            "census_developer_area": "Developer area:",
            "census_password_placeholder": "4-digit password",
            "census_unlock": "Unlock",
            "census_wrong_password_title": "Wrong password",
            "census_wrong_password_text": "Developer password is incorrect.",
            "census_view_json": "View JSON",
            "census_copy_json": "Copy JSON",
            "census_save_json": "Save JSON",
            "census_send_test": "Send test",
            "census_reset_state": "Reset local submission state",
            "census_save_json_title": "Save JSON",
            "census_save_json_default": "anki-census-dev.json",
            "census_debug_sent_title": "Test sent",
            "census_debug_error_title": "Debug submit error",
            "census_reset_done_title": "Reset complete",
            "census_reset_done_text": "Local submission state has been reset.",
        }
        return labels.get(key, key)

    def _build_ui(self) -> None:
        """Create and compose all widgets for summary, opt-out, and developer actions."""
        layout = QVBoxLayout(self)

        self.brief_label = QLabel("")
        self.brief_label.setWordWrap(True)
        self.pause_checkbox = QCheckBox("")
        self.pause_checkbox.clicked.connect(self._save_pause_state)
        self.status_label = QLabel("")

        self.view_button = QPushButton("")
        self.view_button.clicked.connect(self._show_census_status)

        row = QHBoxLayout()
        self.dev_label = QLabel("")
        self.dev_password = QLineEdit()
        self.dev_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.unlock_button = QPushButton("")
        self.unlock_button.clicked.connect(self._unlock_debug)
        row.addWidget(self.dev_label)
        row.addWidget(self.dev_password)
        row.addWidget(self.unlock_button)
        row.addStretch(1)

        self.debug_text = QTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setEnabled(False)

        buttons = QHBoxLayout()
        self.view_json_button = QPushButton("")
        self.copy_json_button = QPushButton("")
        self.save_json_button = QPushButton("")
        self.send_test_button = QPushButton("")
        self.reset_state_button = QPushButton("")

        self.view_json_button.clicked.connect(self._refresh_debug_json)
        self.copy_json_button.clicked.connect(lambda: QApplication.clipboard().setText(self.debug_text.toPlainText()))
        self.save_json_button.clicked.connect(self._save_debug_json)
        self.send_test_button.clicked.connect(self._send_debug_payload)
        self.reset_state_button.clicked.connect(self._reset_submission_state)

        for btn in [self.view_json_button, self.copy_json_button, self.save_json_button, self.send_test_button, self.reset_state_button]:
            btn.setEnabled(False)
            buttons.addWidget(btn)
        buttons.addStretch(1)

        layout.addWidget(self.brief_label)
        layout.addWidget(self.pause_checkbox)
        layout.addWidget(self.status_label)
        layout.addWidget(self.view_button)
        layout.addLayout(row)
        layout.addWidget(self.debug_text)
        layout.addLayout(buttons)
        layout.addStretch(1)

    def _apply_texts(self) -> None:
        """Apply translatable text labels to all controls in one place."""
        self.brief_label.setText(self._tr("census_brief"))
        self.pause_checkbox.setText(self._tr("census_pause"))
        self.view_button.setText(self._tr("census_view"))
        self.dev_label.setText(self._tr("census_developer_area"))
        self.dev_password.setPlaceholderText(self._tr("census_password_placeholder"))
        self.unlock_button.setText(self._tr("census_unlock"))
        self.view_json_button.setText(self._tr("census_view_json"))
        self.copy_json_button.setText(self._tr("census_copy_json"))
        self.save_json_button.setText(self._tr("census_save_json"))
        self.send_test_button.setText(self._tr("census_send_test"))
        self.reset_state_button.setText(self._tr("census_reset_state"))

    def refresh_state(self) -> None:
        """Sync UI enabled state and status text with the current client availability and pause flag."""
        if self._client is None:
            self.pause_checkbox.setChecked(False)
            self.pause_checkbox.setEnabled(False)
            self.view_button.setEnabled(False)
            self.unlock_button.setEnabled(False)
            self.dev_password.setEnabled(False)
            self.status_label.setText(self._tr("census_status_unavailable"))
            return

        self.pause_checkbox.setEnabled(True)
        self.view_button.setEnabled(True)
        self.unlock_button.setEnabled(True)
        self.dev_password.setEnabled(True)
        paused = bool(self._client.is_participation_paused())
        self.pause_checkbox.setChecked(paused)
        self.status_label.setText(self._tr("census_status_off") if paused else self._tr("census_status_on"))

    def _save_pause_state(self) -> None:
        """Persist global opt-out immediately when the checkbox toggles."""
        if self._client is None:
            return
        try:
            self._client.set_participation_paused(bool(self.pause_checkbox.isChecked()))
            self.refresh_state()
        except Exception:
            pass

    def _show_census_status(self) -> None:
        """Show a compact JSON summary with pause flag, privacy summary, and payload preview."""
        if self._client is None:
            showWarning(self._tr("census_status_unavailable"), title=self._tr("census_preview_title"))
            return
        try:
            payload = {
                "participation_paused": bool(self._client.is_participation_paused()),
                "summary": self._client.get_privacy_summary(),
                "payload_preview": self._client.get_current_survey_payload(),
            }
            showInfo(json.dumps(payload, ensure_ascii=False, indent=2), title=self._tr("census_preview_title"))
        except Exception as exc:
            showWarning(str(exc), title=self._tr("census_preview_title"))

    def _unlock_debug(self) -> None:
        """Unlock developer actions when the standard developer password is correct."""
        if self.dev_password.text().strip() != DEV_PASSWORD:
            showWarning(self._tr("census_wrong_password_text"), title=self._tr("census_wrong_password_title"))
            return
        self._debug_unlocked = True
        self.debug_text.setEnabled(True)
        for btn in [self.view_json_button, self.copy_json_button, self.save_json_button, self.send_test_button, self.reset_state_button]:
            btn.setEnabled(True)
        self._refresh_debug_json()

    def _refresh_debug_json(self) -> None:
        """Render the current full survey payload JSON into the debug text box."""
        if not self._debug_unlocked or self._client is None:
            return
        payload = self._client.get_current_survey_payload()
        self.debug_text.setPlainText(json.dumps(payload, ensure_ascii=False, indent=2))

    def _save_debug_json(self) -> None:
        """Export the JSON currently rendered in the debug area to a user-selected file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._tr("census_save_json_title"),
            self._tr("census_save_json_default"),
            "JSON (*.json)",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(self.debug_text.toPlainText())

    def _send_debug_payload(self) -> None:
        """Submit developer payload to the debug endpoint and show parsed response JSON."""
        if self._client is None:
            return
        try:
            result = self._client.send_debug_payload()
            showInfo(json.dumps(result, ensure_ascii=False, indent=2), title=self._tr("census_debug_sent_title"))
        except Exception as exc:
            showWarning(str(exc), title=self._tr("census_debug_error_title"))

    def _reset_submission_state(self) -> None:
        """Clear local submission markers to enable manual end-to-end re-testing."""
        if self._client is None:
            return
        self._client.reset_local_submission_state()
        showInfo(self._tr("census_reset_done_text"), title=self._tr("census_reset_done_title"))


class CensusTabAdapter:
    """Thin helper for hosts that prefer explicit lifecycle methods over direct widget usage.

    This adapter keeps host integration explicit and easy to test while wrapping
    the reusable ``CensusSettingsTab`` widget.
    """

    def __init__(self, censo_client: Any, tr=None) -> None:
        """Create adapter and internal tab widget with optional translation callback."""
        self.widget = CensusSettingsTab(censo_client=censo_client, tr=tr)

    def as_widget(self) -> QWidget:
        """Return the underlying QWidget ready to be added to a QTabWidget."""
        return self.widget

    def refresh(self) -> None:
        """Refresh runtime status and control states when host dialog is re-opened or language changes."""
        self.widget.refresh_state()
