from aqt.qt import QWidget, QVBoxLayout, QFormLayout, QComboBox, QPushButton, QLabel, QHBoxLayout, QCheckBox, QGroupBox
from ..constants import COUNTRIES, BRAZIL_STATES, PRIMARY_AREAS, EXPERIENCE_BUCKETS, LEVELS, AGE_BUCKETS, PLATFORMS
from ..storage import load_config, update_profile


class ProfileTab(QWidget):
    """Render optional user profile controls used in payloads."""

    def __init__(self, parent=None):
        """Initialize profile form widgets and state."""
        super().__init__(parent)
        self.secondary_boxes = []
        self.platform_checks = {}

        outer = QVBoxLayout(self)
        info = QLabel("All fields are optional. Keep your profile updated to improve aggregate census quality.")
        info.setWordWrap(True)
        outer.addWidget(info)

        self.form = QFormLayout()
        outer.addLayout(self.form)

        self.country = self._combo(COUNTRIES)
        self.country.currentTextChanged.connect(self._country_changed)
        self.state = self._combo(BRAZIL_STATES)
        self.primary_area = self._combo(PRIMARY_AREAS)
        self.primary_area.currentTextChanged.connect(self._refresh_secondary_options)
        self.experience = self._combo(EXPERIENCE_BUCKETS)
        self.level = self._combo(LEVELS)
        self.age = self._combo(AGE_BUCKETS)

        self.form.addRow(QLabel("Country"), self.country)
        self.state_label = QLabel("State")
        self.form.addRow(self.state_label, self.state)
        self.form.addRow(QLabel("Primary area"), self.primary_area)

        self.secondary_group = QGroupBox("Secondary areas")
        self.secondary_layout = QVBoxLayout(self.secondary_group)
        self.add_secondary_btn = QPushButton("+ Add secondary area")
        self.add_secondary_btn.clicked.connect(lambda: self.add_secondary_area(""))
        self.secondary_layout.addWidget(self.add_secondary_btn)
        self.form.addRow(self.secondary_group)

        self.form.addRow(QLabel("Anki experience"), self.experience)
        self.form.addRow(QLabel("Self-assessed level"), self.level)
        self.form.addRow(QLabel("Age bucket"), self.age)

        platform_box = QGroupBox("Platforms used")
        platform_layout = QVBoxLayout(platform_box)
        for platform in PLATFORMS:
            cb = QCheckBox(platform)
            self.platform_checks[platform] = cb
            platform_layout.addWidget(cb)
        self.form.addRow(platform_box)

        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Save profile")
        self.save_btn.clicked.connect(self.save)
        buttons.addStretch(1)
        buttons.addWidget(self.save_btn)
        outer.addLayout(buttons)
        outer.addStretch(1)

        self.load()

    def _combo(self, values):
        """Build a combo box from a static list of values."""
        combo = QComboBox()
        combo.addItems(values)
        return combo

    def _set_combo(self, combo, value):
        """Set combo value safely when an option exists."""
        idx = combo.findText(value or "")
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _country_changed(self):
        """Show state selector only when country is Brazil."""
        is_brazil = self.country.currentText() == "Brazil"
        self.state_label.setVisible(is_brazil)
        self.state.setVisible(is_brazil)
        self.state.setEnabled(is_brazil)
        if not is_brazil:
            self.state.setCurrentIndex(0)

    def add_secondary_area(self, value=""):
        """Append one secondary-area selector up to a capped count."""
        if len(self.secondary_boxes) >= 5:
            return
        row = QHBoxLayout()
        combo = QComboBox()
        combo.addItems(PRIMARY_AREAS)
        combo.currentTextChanged.connect(self._refresh_secondary_options)
        remove_btn = QPushButton("Remove")
        row.addWidget(combo)
        row.addWidget(remove_btn)
        self.secondary_layout.insertLayout(max(0, self.secondary_layout.count() - 1), row)
        self.secondary_boxes.append((combo, row, remove_btn))
        remove_btn.clicked.connect(lambda: self.remove_secondary(combo, row, remove_btn))
        self._set_combo(combo, value)
        self._refresh_secondary_options()

    def remove_secondary(self, combo, row, remove_btn):
        """Remove a secondary-area selector row."""
        for widget in (combo, remove_btn):
            row.removeWidget(widget)
            widget.deleteLater()
        self.secondary_boxes = [entry for entry in self.secondary_boxes if entry[0] is not combo]
        self._refresh_secondary_options()

    def _refresh_secondary_options(self):
        """Prevent duplicated area selections between primary and secondary fields."""
        primary = self.primary_area.currentText()
        selected = {combo.currentText() for combo, _, _ in self.secondary_boxes if combo.currentText()}
        for combo, _, _ in self.secondary_boxes:
            current = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            options = []
            for item in PRIMARY_AREAS:
                if item == primary and item:
                    continue
                if item in selected and item != current and item:
                    continue
                options.append(item)
            combo.addItems(options)
            idx = combo.findText(current)
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

    def load(self):
        """Load persisted profile values into form controls."""
        cfg = load_config()
        profile = cfg.get("profile", {})
        self._set_combo(self.country, profile.get("country"))
        self._set_combo(self.state, profile.get("state"))
        self._set_combo(self.primary_area, profile.get("primary_area"))
        for value in profile.get("secondary_areas", [])[:5]:
            self.add_secondary_area(value)
        self._set_combo(self.experience, profile.get("anki_experience"))
        self._set_combo(self.level, profile.get("self_assessed_level"))
        self._set_combo(self.age, profile.get("age_bucket"))
        for platform in profile.get("platforms_used", []):
            if platform in self.platform_checks:
                self.platform_checks[platform].setChecked(True)
        self._country_changed()

    def save(self):
        """Persist profile values using normalized payload-ready keys."""
        primary = self.primary_area.currentText()
        secondary = []
        seen = set()
        for combo, _, _ in self.secondary_boxes:
            value = combo.currentText()
            if value and value != primary and value not in seen:
                secondary.append(value)
                seen.add(value)
        data = {
            "country": self.country.currentText() or None,
            "state": self.state.currentText() if self.country.currentText() == "Brazil" else None,
            "primary_area": primary or None,
            "secondary_areas": secondary,
            "anki_experience": self.experience.currentText() or None,
            "self_assessed_level": self.level.currentText() or None,
            "age_bucket": self.age.currentText() or None,
            "platforms_used": [platform for platform, cb in self.platform_checks.items() if cb.isChecked()],
        }
        update_profile(data)
