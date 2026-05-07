import json
from aqt.qt import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLineEdit, QLabel, QFileDialog, QApplication, QMessageBox
from ..constants import DEV_PASSWORD
from ..scheduler import current_survey_for_day
from ..payload_builder import build_payload
from ..sender import submit_debug_payload
from ..storage import load_config, save_config

class DeveloperTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.unlocked = False
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.pass_input = QLineEdit(); self.pass_input.setEchoMode(QLineEdit.EchoMode.Password); self.pass_input.setPlaceholderText("Senha de 4 dígitos")
        self.unlock_btn = QPushButton("Desbloquear")
        self.unlock_btn.clicked.connect(self.unlock)
        row.addWidget(QLabel("Área de desenvolvedor:")); row.addWidget(self.pass_input); row.addWidget(self.unlock_btn); row.addStretch(1)
        layout.addLayout(row)
        self.text = QTextEdit(); self.text.setReadOnly(True); self.text.setEnabled(False)
        layout.addWidget(self.text)
        buttons = QHBoxLayout()
        self.refresh_btn = QPushButton("Ver JSON")
        self.copy_btn = QPushButton("Copiar JSON")
        self.save_btn = QPushButton("Salvar JSON")
        self.debug_btn = QPushButton("Enviar teste")
        self.reset_btn = QPushButton("Resetar status local de envio")
        for b in [self.refresh_btn,self.copy_btn,self.save_btn,self.debug_btn,self.reset_btn]:
            b.setEnabled(False); buttons.addWidget(b)
        buttons.addStretch(1); layout.addLayout(buttons)
        self.refresh_btn.clicked.connect(self.refresh)
        self.copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.text.toPlainText()))
        self.save_btn.clicked.connect(self.export)
        self.debug_btn.clicked.connect(self.send_debug)
        self.reset_btn.clicked.connect(self.reset_status)
    def unlock(self):
        if self.pass_input.text() == DEV_PASSWORD:
            self.unlocked = True
            self.text.setEnabled(True)
            for b in [self.refresh_btn,self.copy_btn,self.save_btn,self.debug_btn,self.reset_btn]: b.setEnabled(True)
            self.refresh()
        else:
            QMessageBox.warning(self, "Senha incorreta", "Senha de desenvolvedor incorreta.")
    def _payload(self):
        return build_payload(current_survey_for_day()["survey_id"], mode="developer_test")
    def refresh(self):
        if self.unlocked:
            self.text.setPlainText(json.dumps(self._payload(), ensure_ascii=False, indent=2))
    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar JSON", "censo-anki-brasil-dev.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f: f.write(self.text.toPlainText())
    def send_debug(self):
        try:
            result = submit_debug_payload(self._payload())
            QMessageBox.information(self, "Teste enviado", json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            QMessageBox.warning(self, "Erro no envio de teste", str(e))
    def reset_status(self):
        cfg = load_config()
        cfg.setdefault("local_state", {})["sent_surveys"] = {}
        cfg.setdefault("local_state", {})["pending_surveys"] = {}
        cfg.setdefault("local_state", {})["last_error"] = ""
        save_config(cfg)
        QMessageBox.information(self, "Reset concluído", "Status local de envio resetado.")
