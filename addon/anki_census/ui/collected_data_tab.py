import json
from aqt.qt import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QFileDialog, QApplication
from ..scheduler import current_survey_for_day
from ..payload_builder import build_payload


class CollectedDataTab(QWidget):
    """Preview collected payload as formatted JSON."""

    def __init__(self, parent=None):
        """Build JSON preview widgets and actions."""
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.layout.addWidget(self.text)

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh JSON")
        self.copy_btn = QPushButton("Copy JSON")
        self.export_btn = QPushButton("Export JSON")
        self.refresh_btn.clicked.connect(self.refresh)
        self.copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.text.toPlainText()))
        self.export_btn.clicked.connect(self.export)
        row.addWidget(self.refresh_btn)
        row.addWidget(self.copy_btn)
        row.addWidget(self.export_btn)
        row.addStretch(1)
        self.layout.addLayout(row)
        self.refresh()

    def _payload(self):
        """Build preview payload using current survey window id."""
        survey_id = current_survey_for_day()["survey_id"]
        return build_payload(survey_id, mode="preview")

    def refresh(self):
        """Update JSON preview text."""
        self.text.setPlainText(json.dumps(self._payload(), ensure_ascii=False, indent=2))

    def export(self):
        """Export preview JSON to a user-selected file."""
        path, _ = QFileDialog.getSaveFileName(self, "Export JSON", "anki-census-preview.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(self.text.toPlainText())
