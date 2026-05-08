from aqt.qt import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton
from ..collectors.addons import collect_addons


class AddonsTab(QWidget):
    """Show detected add-ons from Anki runtime metadata."""

    def __init__(self, parent=None):
        """Build table and refresh action."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "ID", "Status", "Source"])
        layout.addWidget(self.table)

        btn = QPushButton("Refresh list")
        btn.clicked.connect(self.refresh)
        layout.addWidget(btn)
        self.refresh()

    def refresh(self):
        """Reload add-on list from collector output."""
        items = collect_addons().get("items", [])
        self.table.setRowCount(len(items))
        for row_index, item in enumerate(items):
            values = [
                item.get("name", ""),
                item.get("id") or item.get("folder") or "",
                "enabled" if item.get("enabled") else "disabled",
                item.get("source", ""),
            ]
            for col_index, value in enumerate(values):
                self.table.setItem(row_index, col_index, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()
