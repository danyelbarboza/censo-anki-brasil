from aqt.qt import QWidget, QVBoxLayout, QLabel
from ..constants import ADDON_NAME, ADDON_VERSION, AUTHOR

class AboutTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        text = QLabel(f"""
<h2>{ADDON_NAME}</h2>
<p><b>Versão:</b> {ADDON_VERSION}<br><b>Autor:</b> {AUTHOR}</p>
<p>Este addon participa automaticamente do Censo Anki Brasil durante as janelas semestrais de coleta, exceto se a participação estiver pausada nas configurações.</p>
<p><b>O que não é enviado:</b> conteúdo de cards, notas, campos, tags, nomes de decks, nomes de arquivos de mídia, e-mail, nome real ou caminho local da coleção.</p>
<p><b>O que é enviado:</b> dados agregados em faixas, lista de addons, informações de ambiente, perfil opcional e estatísticas gerais da coleção local sincronizada.</p>
<p>Os dados históricos vêm do que já existe na coleção local do Anki Desktop. O addon não consegue recuperar addons desinstalados antes da instalação nem dados que nunca foram sincronizados para este computador.</p>
""")
        text.setWordWrap(True)
        layout.addWidget(text); layout.addStretch(1)
