from aqt.qt import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
from ..collectors.addons import collect_addons

class AddonsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nome", "ID", "Status", "Origem"])
        layout.addWidget(self.table)
        btn = QPushButton("Atualizar lista")
        btn.clicked.connect(self.refresh)
        layout.addWidget(btn)
        self.refresh()
    def refresh(self):
        items = collect_addons().get("items", [])
        self.table.setRowCount(len(items))
        for r, item in enumerate(items):
            vals = [item.get("name",""), item.get("id") or item.get("folder") or "", "ativo" if item.get("enabled") else "desativado", item.get("source","")]
            for c, val in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))
        self.table.resizeColumnsToContents()
