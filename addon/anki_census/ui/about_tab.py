from aqt.qt import QWidget, QVBoxLayout, QLabel
from ..constants import ADDON_NAME, ADDON_VERSION, AUTHOR


class AboutTab(QWidget):
    """Render project summary and privacy highlights."""

    def __init__(self, parent=None):
        """Build About tab layout with compact HTML content."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        text = QLabel(
            f"""
<h2>{ADDON_NAME}</h2>
<p><b>Version:</b> {ADDON_VERSION}<br><b>Author:</b> {AUTHOR}</p>
<p>This add-on participates automatically in Anki Census during semester collection windows, unless participation is paused in settings.</p>
<p><b>Not sent:</b> card content, note content, field names, tag names, deck names, media file names, email, real name, AnkiWeb login, or local collection path.</p>
<p><b>Sent:</b> aggregated bucketed stats, installed add-ons, environment metadata, optional profile values, and high-level collection usage stats.</p>
"""
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch(1)
