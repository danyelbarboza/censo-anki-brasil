from aqt.qt import QWidget, QVBoxLayout, QFormLayout, QComboBox, QCheckBox, QLineEdit, QPushButton, QLabel
from ..storage import load_config, save_config


class SettingsTab(QWidget):
    """Render settings controls shared by standalone and embedded usage."""

    def __init__(self, parent=None):
        """Create settings widgets and bind save action."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.api_url = QLineEdit()
        self.lang = QComboBox()
        self.lang.addItems(["en", "pt_BR"])
        self.paused = QCheckBox("Pause participation in Anki Census")

        form.addRow("API URL", self.api_url)
        form.addRow("Language", self.lang)
        form.addRow(self.paused)
        layout.addLayout(form)

        note = QLabel("The API URL comes from your Cloudflare Worker deployment. Changing this does not alter add-on source code.")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.save_btn = QPushButton("Save settings")
        self.save_btn.clicked.connect(self.save)
        layout.addWidget(self.save_btn)
        layout.addStretch(1)
        self.load()

    def load(self):
        """Load existing settings values into controls."""
        cfg = load_config()
        self.api_url.setText(cfg.get("api_base_url", ""))
        i = self.lang.findText(cfg.get("language", "en"))
        self.lang.setCurrentIndex(i if i >= 0 else 0)
        self.paused.setChecked(bool(cfg.get("participation_paused")))

    def save(self):
        """Persist settings values to add-on config."""
        cfg = load_config()
        cfg["api_base_url"] = self.api_url.text().strip().rstrip("/")
        cfg["language"] = self.lang.currentText()
        cfg["participation_paused"] = self.paused.isChecked()
        save_config(cfg)
