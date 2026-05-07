from aqt.qt import QWidget, QVBoxLayout, QFormLayout, QComboBox, QPushButton, QLabel, QHBoxLayout, QCheckBox, QGroupBox
from ..constants import COUNTRIES, BRAZIL_STATES, PRIMARY_AREAS, EXPERIENCE_BUCKETS, LEVELS, AGE_BUCKETS, PLATFORMS
from ..storage import load_config, update_profile


class ProfileTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.secondary_boxes = []
        self.platform_checks = {}

        outer = QVBoxLayout(self)
        info = QLabel("Todos os campos são opcionais. Mantenha seu perfil atualizado para melhorar a qualidade dos resultados do censo.")
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

        self.country_label = QLabel("País")
        self.state_label = QLabel("Estado")
        self.primary_area_label = QLabel("Área principal")
        self.experience_label = QLabel("Tempo de uso do Anki")
        self.level_label = QLabel("Nível autodeclarado")
        self.age_label = QLabel("Faixa etária")

        self.form.addRow(self.country_label, self.country)
        self.form.addRow(self.state_label, self.state)
        self.form.addRow(self.primary_area_label, self.primary_area)

        self.secondary_group = QGroupBox("Áreas secundárias")
        self.secondary_layout = QVBoxLayout(self.secondary_group)
        self.add_secondary_btn = QPushButton("+ Adicionar área secundária")
        self.add_secondary_btn.clicked.connect(lambda: self.add_secondary_area(""))
        self.secondary_layout.addWidget(self.add_secondary_btn)
        self.form.addRow(self.secondary_group)

        self.form.addRow(self.experience_label, self.experience)
        self.form.addRow(self.level_label, self.level)
        self.form.addRow(self.age_label, self.age)

        platform_box = QGroupBox("Plataformas usadas")
        platform_layout = QVBoxLayout(platform_box)
        for p in PLATFORMS:
            cb = QCheckBox(p)
            self.platform_checks[p] = cb
            platform_layout.addWidget(cb)
        self.form.addRow(platform_box)

        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Salvar perfil")
        self.save_btn.clicked.connect(self.save)
        buttons.addStretch(1)
        buttons.addWidget(self.save_btn)
        outer.addLayout(buttons)
        outer.addStretch(1)

        self.load()

    def _combo(self, values):
        c = QComboBox()
        c.addItems(values)
        return c

    def _set_combo(self, combo, value):
        i = combo.findText(value or "")
        combo.setCurrentIndex(i if i >= 0 else 0)

    def _country_changed(self):
        is_br = self.country.currentText() == "Brasil"
        self.state_label.setVisible(is_br)
        self.state.setVisible(is_br)
        self.state.setEnabled(is_br)
        if not is_br:
            self.state.setCurrentIndex(0)

    def add_secondary_area(self, value=""):
        if len(self.secondary_boxes) >= 5:
            return
        row = QHBoxLayout()
        combo = QComboBox()
        combo.addItems(PRIMARY_AREAS)
        combo.currentTextChanged.connect(self._refresh_secondary_options)
        rm = QPushButton("Remover")
        row.addWidget(combo)
        row.addWidget(rm)
        self.secondary_layout.insertLayout(max(0, self.secondary_layout.count() - 1), row)
        self.secondary_boxes.append((combo, row, rm))
        rm.clicked.connect(lambda: self.remove_secondary(combo, row, rm))
        self._set_combo(combo, value)
        self._refresh_secondary_options()

    def remove_secondary(self, combo, row, rm):
        for w in (combo, rm):
            row.removeWidget(w)
            w.deleteLater()
        self.secondary_boxes = [x for x in self.secondary_boxes if x[0] is not combo]
        self._refresh_secondary_options()

    def _refresh_secondary_options(self):
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
        cfg = load_config()
        p = cfg.get("profile", {})
        self._set_combo(self.country, p.get("country"))
        self._set_combo(self.state, p.get("state"))
        self._set_combo(self.primary_area, p.get("primary_area"))
        for val in p.get("secondary_areas", [])[:5]:
            self.add_secondary_area(val)
        self._set_combo(self.experience, p.get("anki_experience"))
        self._set_combo(self.level, p.get("self_assessed_level"))
        self._set_combo(self.age, p.get("age_bucket"))
        for plat in p.get("platforms_used", []):
            if plat in self.platform_checks:
                self.platform_checks[plat].setChecked(True)
        self._country_changed()

    def save(self):
        primary = self.primary_area.currentText()
        secondary = []
        seen = set()
        for combo, _, _ in self.secondary_boxes:
            v = combo.currentText()
            if v and v != primary and v not in seen:
                secondary.append(v)
                seen.add(v)
        data = {
            "country": self.country.currentText() or None,
            "state": self.state.currentText() if self.country.currentText() == "Brasil" else None,
            "primary_area": primary or None,
            "secondary_areas": secondary,
            "anki_experience": self.experience.currentText() or None,
            "self_assessed_level": self.level.currentText() or None,
            "age_bucket": self.age.currentText() or None,
            "platforms_used": [p for p, cb in self.platform_checks.items() if cb.isChecked()],
        }
        update_profile(data)
