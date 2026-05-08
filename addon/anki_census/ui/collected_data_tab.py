import json
from aqt.qt import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QFileDialog, QApplication
from ..scheduler import current_survey_for_day
from ..payload_builder import build_payload

class CollectedDataTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.text = QTextEdit(); self.text.setReadOnly(True)
        self.layout.addWidget(self.text)
        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Atualizar JSON")
        self.copy_btn = QPushButton("Copiar JSON")
        self.export_btn = QPushButton("Exportar JSON")
        self.refresh_btn.clicked.connect(self.refresh)
        self.copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.text.toPlainText()))
        self.export_btn.clicked.connect(self.export)
        row.addWidget(self.refresh_btn); row.addWidget(self.copy_btn); row.addWidget(self.export_btn); row.addStretch(1)
        self.layout.addLayout(row)
        self.refresh()
    def _payload(self):
        sid = current_survey_for_day()["survey_id"]
        return build_payload(sid, mode="preview")
    def refresh(self):
        self.text.setPlainText(json.dumps(self._payload(), ensure_ascii=False, indent=2))
    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar JSON", "anki-census-preview.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.text.toPlainText())
