from aqt import mw
from aqt.qt import QDialog, QVBoxLayout, QTabWidget
from .summary_tab import SummaryTab
from .profile_tab import ProfileTab
from .collected_data_tab import CollectedDataTab
from .addons_tab import AddonsTab
from .settings_tab import SettingsTab
from .developer_tab import DeveloperTab
from .about_tab import AboutTab

_window = None

class MainWindow(QDialog):
    def __init__(self, parent=None, initial_tab=None):
        super().__init__(parent)
        self.setWindowTitle("Censo Anki Brasil")
        self.resize(920, 680)
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.summary = SummaryTab(); self.profile = ProfileTab(); self.data = CollectedDataTab(); self.addons = AddonsTab(); self.settings = SettingsTab(); self.dev = DeveloperTab(); self.about = AboutTab()
        self.tabs.addTab(self.summary, "Resumo")
        self.tabs.addTab(self.profile, "Perfil")
        self.tabs.addTab(self.data, "Dados coletados")
        self.tabs.addTab(self.addons, "Addons")
        self.tabs.addTab(self.settings, "Configurações")
        self.tabs.addTab(self.dev, "Desenvolvedor")
        self.tabs.addTab(self.about, "Sobre / Privacidade")
        layout.addWidget(self.tabs)
        if initial_tab:
            names = {"summary":0,"profile":1,"data":2,"addons":3,"settings":4,"developer":5,"about":6}
            self.tabs.setCurrentIndex(names.get(initial_tab, 0))

def show_main_window(initial_tab=None):
    global _window
    _window = MainWindow(mw, initial_tab=initial_tab)
    _window.show()
    return _window
