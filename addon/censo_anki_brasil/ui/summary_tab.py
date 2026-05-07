from aqt.qt import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QApplication
from ..storage import load_config
from ..scheduler import current_survey_for_day
from ..ids import ensure_user_id

class SummaryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.label = QLabel("")
        self.label.setWordWrap(True)
        self.layout.addWidget(self.label)
        row = QHBoxLayout()
        self.copy_btn = QPushButton("Copiar ID anônimo")
        self.copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(ensure_user_id()))
        row.addWidget(self.copy_btn)
        row.addStretch(1)
        self.layout.addLayout(row)
        self.layout.addStretch(1)
        self.refresh()
    def refresh(self):
        cfg = load_config(); st = cfg.get("local_state", {})
        info = current_survey_for_day()
        sid = info["survey_id"]
        sent = st.get("sent_surveys", {}).get(sid)
        pending = st.get("pending_surveys", {}).get(sid)
        status = "Coleta pausada" if cfg.get("participation_paused") else "Ativa"
        if sent:
            send_status = f"Enviado com sucesso em {sent}"
        elif pending:
            send_status = f"Ainda não enviado. Última tentativa: {pending.get('last_attempt')}. Possível motivo: {pending.get('reason')}"
        else:
            send_status = "Ainda não enviado para este censo. Se estiver dentro da janela, o addon tentará automaticamente na próxima abertura do Anki."
        self.label.setText(f"""
<b>Censo Anki Brasil</b><br><br>
<b>ID anônimo:</b> {ensure_user_id()}<br>
<b>Participação:</b> {status}<br>
<b>Censo atual/próximo:</b> {sid}<br>
<b>Janela:</b> {info['start']} a {info['end']}<br>
<b>Fase atual:</b> {info['phase']}<br><br>
<b>Status de envio:</b><br>{send_status}<br><br>
Os dados técnicos são enviados automaticamente durante a janela de coleta, exceto se a participação estiver pausada.
""")
