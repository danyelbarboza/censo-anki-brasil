from aqt.qt import QLabel, QVBoxLayout, QWidget

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
<p><b>Versão:</b> {ADDON_VERSION}<br><b>Autor:</b> {AUTHOR}</p>
<p>Este addon participa automaticamente do Anki Census durante as janelas semestrais de coleta, exceto se a participação estiver pausada nas configurações.</p>
<p><b>O que não é enviado:</b> conteúdo de cards, notas, campos, tags, nomes de decks, nomes de arquivos de mídia, e-mail, nome real, login AnkiWeb ou caminho local da coleção.</p>
<p><b>O que é enviado:</b> dados agregados em faixas, lista de addons, informações de ambiente, perfil opcional e estatísticas gerais da coleção local sincronizada.</p>
"""
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        layout.addStretch(1)
