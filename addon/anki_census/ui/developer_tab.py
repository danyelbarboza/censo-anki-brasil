import json
from aqt.qt import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLineEdit, QLabel, QFileDialog, QApplication, QMessageBox
from ..constants import DEV_PASSWORD
from ..scheduler import current_survey_for_day
from ..payload_builder import build_payload
from ..sender import submit_debug_payload
from ..storage import load_config, save_config


class DeveloperTab(QWidget):
    """Developer tools for payload inspection and debug submission."""

    def __init__(self, parent=None):
        """Build developer panel and lock-sensitive actions by default."""
        super().__init__(parent)
        self.unlocked = False
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("4-digit password")
        self.unlock_btn = QPushButton("Unlock")
        self.unlock_btn.clicked.connect(self.unlock)
        row.addWidget(QLabel("Developer area:"))
        row.addWidget(self.pass_input)
        row.addWidget(self.unlock_btn)
        row.addStretch(1)
        layout.addLayout(row)

        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setEnabled(False)
        layout.addWidget(self.text)

        buttons = QHBoxLayout()
        self.refresh_btn = QPushButton("View JSON")
        self.copy_btn = QPushButton("Copy JSON")
        self.save_btn = QPushButton("Save JSON")
        self.debug_btn = QPushButton("Send test")
        self.reset_btn = QPushButton("Reset local submission state")
        for button in [self.refresh_btn, self.copy_btn, self.save_btn, self.debug_btn, self.reset_btn]:
            button.setEnabled(False)
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.refresh_btn.clicked.connect(self.refresh)
        self.copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.text.toPlainText()))
        self.save_btn.clicked.connect(self.export)
        self.debug_btn.clicked.connect(self.send_debug)
        self.reset_btn.clicked.connect(self.reset_status)

    def unlock(self):
        """Unlock developer actions when password is valid."""
        if self.pass_input.text() == DEV_PASSWORD:
            self.unlocked = True
            self.text.setEnabled(True)
            for button in [self.refresh_btn, self.copy_btn, self.save_btn, self.debug_btn, self.reset_btn]:
                button.setEnabled(True)
            self.refresh()
        else:
            QMessageBox.warning(self, "Wrong password", "Developer password is incorrect.")

    def _payload(self):
        """Build developer payload for current survey id."""
        return build_payload(current_survey_for_day()["survey_id"], mode="developer_test")

    def refresh(self):
        """Render current developer payload to editor."""
        if self.unlocked:
            self.text.setPlainText(json.dumps(self._payload(), ensure_ascii=False, indent=2))

    def export(self):
        """Save developer payload JSON to disk."""
        path, _ = QFileDialog.getSaveFileName(self, "Save JSON", "anki-census-dev.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.text.toPlainText())

    def send_debug(self):
        """Submit developer payload to debug endpoint."""
        try:
            result = submit_debug_payload(self._payload())
            QMessageBox.information(self, "Test sent", json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as exc:
            QMessageBox.warning(self, "Debug submit error", str(exc))

    def reset_status(self):
        """Clear local submission markers for manual retesting."""
        cfg = load_config()
        cfg.setdefault("local_state", {})["sent_surveys"] = {}
        cfg.setdefault("local_state", {})["pending_surveys"] = {}
        cfg.setdefault("local_state", {})["last_error"] = ""
        save_config(cfg)
        QMessageBox.information(self, "Reset complete", "Local submission state has been reset.")
