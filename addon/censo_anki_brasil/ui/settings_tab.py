from aqt.qt import QWidget, QVBoxLayout, QFormLayout, QComboBox, QCheckBox, QLineEdit, QPushButton, QLabel
from ..storage import load_config, save_config

class SettingsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.api_url = QLineEdit()
        self.lang = QComboBox(); self.lang.addItems(["pt_BR", "en"])
        self.paused = QCheckBox("Pausar participação no Censo Anki Brasil")
        form.addRow("URL da API", self.api_url)
        form.addRow("Idioma", self.lang)
        form.addRow(self.paused)
        layout.addLayout(form)
        note = QLabel("A URL da API é gerada no deploy do Cloudflare Worker. Isso não altera o código do addon.")
        note.setWordWrap(True); layout.addWidget(note)
        self.save_btn = QPushButton("Salvar configurações")
        self.save_btn.clicked.connect(self.save)
        layout.addWidget(self.save_btn); layout.addStretch(1)
        self.load()
    def load(self):
        cfg = load_config()
        self.api_url.setText(cfg.get("api_base_url", ""))
        i = self.lang.findText(cfg.get("language", "pt_BR")); self.lang.setCurrentIndex(i if i >= 0 else 0)
        self.paused.setChecked(bool(cfg.get("participation_paused")))
    def save(self):
        cfg = load_config()
        cfg["api_base_url"] = self.api_url.text().strip().rstrip("/")
        cfg["language"] = self.lang.currentText()
        cfg["participation_paused"] = self.paused.isChecked()
        save_config(cfg)
