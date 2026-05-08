import hashlib
import math
import re
import webbrowser

from aqt.qt import (
    QApplication,
    QColor,
    QFileDialog,
    QFont,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QImage,
    QLinearGradient,
    QLabel,
    QPainter,
    QPdfWriter,
    QPen,
    QPixmap,
    QProgressBar,
    QPushButton,
    QRect,
    QScrollArea,
    QSizePolicy,
    Qt,
    QVBoxLayout,
    QWidget,
)

from ..ids import ensure_user_id
from ..payload_builder import build_payload
from ..scheduler import current_survey_for_day
from ..sender import fetch_public_results
from ..storage import load_config, save_config

REGION_BY_STATE = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}


def _clean(text):
    return str(text or "Não informado")


def _numbers(text):
    if text is None:
        return []
    return [float(n.replace(".", "").replace(",", ".")) for n in re.findall(r"\d+(?:[\.,]\d+)?", str(text))]


def _extract_first_number(label):
    if label is None:
        return -1
    if str(label) == "sem limite":
        return 10**12
    if str(label).startswith(">0"):
        return 0.1
    nums = _numbers(label)
    return nums[0] if nums else -1


def _extract_max_number(label):
    if label is None:
        return -1
    if str(label) == "sem limite":
        return 10**12
    nums = _numbers(label)
    return nums[-1] if nums else -1


def _parse_percent(value):
    if value is None:
        return None
    text = str(value).replace(",", ".").replace("%", "")
    if "–" in text or "-" in text:
        vals = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
        if len(vals) >= 2:
            return (vals[0] + vals[1]) / 2
    if text.startswith(">"):
        vals = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
        return vals[-1] / 2 if vals else None
    try:
        return float(text)
    except Exception:
        return None


def _parse_time_bucket_hours(text):
    if not text:
        return None
    s = str(text).lower().replace(" ", "")
    vals = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[\.,]\d+)?", s)]
    if not vals:
        return None
    mid = (vals[0] + vals[-1]) / 2 if len(vals) > 1 else vals[0]
    return mid / 60 if "min" in s else mid


def _bucket_mid_numeric(text):
    if not text:
        return None
    s = str(text)
    if "%" in s:
        return _parse_percent(s)
    if "h" in s.lower() or "min" in s.lower():
        return _parse_time_bucket_hours(s)
    lo = _extract_first_number(s)
    hi = _extract_max_number(s)
    if lo < 0 and hi < 0:
        return None
    if hi >= 10**12:
        return lo
    if hi < 0:
        return lo
    return (lo + hi) / 2


def _items_to_map(items):
    out = {}
    for item in items or []:
        name = item.get("name")
        count = int(item.get("count") or 0)
        if name:
            out[name] = count
    return out


def _ordered_distribution(items):
    data = []
    for item in items or []:
        label = item.get("name")
        count = int(item.get("count") or 0)
        if not label:
            continue
        val = _bucket_mid_numeric(label)
        data.append((val if val is not None else 10**15, label, count))
    data.sort(key=lambda x: x[0])
    return [{"name": label, "count": count} for _, label, count in data]


def _top_percent_for_bucket(user_bucket, items):
    dist = _items_to_map(items)
    total = sum(dist.values())
    if not user_bucket or not total or user_bucket not in dist:
        return None
    user_rank = _extract_first_number(user_bucket)
    above_or_same = sum(count for bucket, count in dist.items() if _extract_first_number(bucket) >= user_rank)
    return max(1, round(100 * above_or_same / total))


def _percentile_for_percent(user_value, items):
    dist = _items_to_map(items)
    total = sum(dist.values())
    user_pct = _parse_percent(user_value)
    if user_pct is None or not total:
        return None
    lower_or_equal = 0
    for bucket, count in dist.items():
        val = _parse_percent(bucket)
        if val is not None and val <= user_pct:
            lower_or_equal += count
    return max(1, min(99, round(100 * lower_or_equal / total)))


def _avg_text(value, suffix="%"):
    if value is None:
        return "sem dados"
    try:
        return f"{float(value):.2f}{suffix}".replace(".", ",")
    except Exception:
        return str(value)


def _mix(c1, c2, ratio=0.5):
    return QColor(
        int(c1.red() * (1 - ratio) + c2.red() * ratio),
        int(c1.green() * (1 - ratio) + c2.green() * ratio),
        int(c1.blue() * (1 - ratio) + c2.blue() * ratio),
    )


def _theme_tokens():
    pal = QApplication.palette()
    window = pal.window().color()
    base = pal.base().color()
    text = pal.text().color()
    accent = pal.highlight().color()
    dark = window.lightness() < 128
    if dark:
        card = _mix(base, window, 0.38)
        hero = _mix(base, pal.highlight().color(), 0.12)
        border = _mix(text, window, 0.76)
        muted = _mix(text, window, 0.38)
        soft = _mix(accent, window, 0.78)
        community = QColor("#d88c4a")
    else:
        card = _mix(base, window, 0.10)
        hero = _mix(base, pal.highlight().color(), 0.08)
        border = _mix(text, window, 0.86)
        muted = _mix(text, window, 0.55)
        soft = _mix(accent, window, 0.84)
        community = QColor("#c56a2d")
    return {
        "dark": dark,
        "window": window.name(),
        "base": base.name(),
        "card": card.name(),
        "hero": hero.name(),
        "border": border.name(),
        "text": text.name(),
        "muted": muted.name(),
        "accent": accent.name(),
        "soft": soft.name(),
        "community": community.name(),
    }


class MetricCard(QFrame):
    def __init__(self, title, value, note="", parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setMinimumHeight(116)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        for text, obj in [(title, "cardTitle"), (value, "cardValue"), (note, "cardNote")]:
            lbl = QLabel(str(text))
            lbl.setObjectName(obj)
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
        layout.addStretch(1)


class InsightCard(QFrame):
    def __init__(self, title, body, progress=None, parent=None):
        super().__init__(parent)
        self.setObjectName("insightCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        t = QLabel(title)
        t.setObjectName("insightTitle")
        b = QLabel(body)
        b.setObjectName("insightBody")
        b.setWordWrap(True)
        layout.addWidget(t)
        layout.addWidget(b)
        if progress is not None:
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(max(0, min(100, int(progress))))
            bar.setTextVisible(False)
            bar.setFixedHeight(10)
            layout.addWidget(bar)


class BadgeLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setObjectName("badgeLabel")


class DistributionChart(QWidget):
    def __init__(self, items=None, user_value=None, title="", parent=None):
        super().__init__(parent)
        self.items = _ordered_distribution(items or [])
        self.user_value = user_value
        self.title = title
        self.setMinimumHeight(172)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = QApplication.palette()
        text = pal.text().color()
        accent = pal.highlight().color()
        window = pal.window().color()
        muted = _mix(text, window, 0.5)
        grid = _mix(text, window, 0.84)
        rect = self.rect().adjusted(10, 8, -10, -12)
        painter.setPen(text)
        painter.setFont(QFont(painter.font().family(), 9, QFont.Weight.DemiBold))
        painter.drawText(rect.left(), rect.top() + 4, self.title)
        if not self.items:
            painter.setPen(muted)
            painter.drawText(rect.adjusted(0, 20, 0, 0), int(Qt.AlignmentFlag.AlignCenter), "Distribuição disponível após a coleta")
            return
        items = self.items[:9]
        max_count = max((it["count"] for it in items), default=1)
        left = rect.left() + 6
        bottom = rect.bottom() - 26
        top = rect.top() + 28
        width = rect.width()
        usable_h = max(30, bottom - top)
        gap = 7
        bar_w = max(16, (width - (len(items) - 1) * gap) / max(1, len(items)))
        painter.setPen(grid)
        painter.drawLine(left, bottom, rect.right(), bottom)
        user_index = next((i for i, it in enumerate(items) if str(it["name"]) == str(self.user_value)), -1)
        for idx, it in enumerate(items):
            x = left + idx * (bar_w + gap)
            h = int(usable_h * (it["count"] / max_count)) if max_count else 0
            y = bottom - h
            color = accent if idx == user_index else _mix(accent, window, 0.72)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(max(7, h)), 5, 5)
            painter.setPen(text if idx == user_index else muted)
            label = str(it["name"])
            short = label if len(label) <= 9 else label[:8] + "…"
            painter.save()
            painter.translate(x + bar_w / 2, bottom + 6)
            painter.rotate(-35)
            painter.drawText(0, 0, short)
            painter.restore()


class HorizontalPercentChart(QWidget):
    def __init__(self, title, rows, community=None, legend_text=None, parent=None):
        super().__init__(parent)
        self.title = title
        self.rows = rows or []
        self.community = community or {}
        self.legend_text = legend_text
        dual = bool(self.rows and len(self.rows[0]) >= 3)
        if dual:
            self.setMinimumHeight(44 + len(self.rows) * 56 + 18)
        else:
            self.setMinimumHeight(40 + len(self.rows) * 34 + 20)

    def _comm_value(self, key, period):
        value = self.community.get(key)
        if isinstance(value, dict):
            return value.get(period)
        return value

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        pal = QApplication.palette()
        text = pal.text().color()
        accent = pal.highlight().color()
        window = pal.window().color()
        muted = _mix(text, window, 0.48)
        track = _mix(text, window, 0.78)
        community_color = QColor("#d88c4a") if window.lightness() < 128 else QColor("#c56a2d")
        rect = self.rect().adjusted(12, 10, -12, -10)
        y = rect.top()
        if self.title:
            painter.setPen(text)
            painter.setFont(QFont(painter.font().family(), 10, QFont.Weight.DemiBold))
            painter.drawText(rect.left(), y, self.title)
            y += 20
        dual = bool(self.rows and len(self.rows[0]) >= 3)
        if dual:
            label_w = 78
            period_w = 34
            value_w = 72
            x = rect.left() + label_w + period_w
            bar_w = max(120, rect.width() - label_w - period_w - value_w - 12)
            painter.setFont(QFont(painter.font().family(), 8, QFont.Weight.DemiBold))
            painter.setPen(accent)
            painter.drawText(x, y, "azul = você")
            painter.setPen(community_color)
            painter.drawText(x + 86, y, "laranja = média")
            painter.setPen(muted)
            painter.drawText(x + 205, y, "30d e 180d")
            y += 14
            for label, value30, value180 in self.rows:
                gy = y + 8
                painter.setPen(text)
                painter.setFont(QFont(painter.font().family(), 9, QFont.Weight.DemiBold))
                painter.drawText(rect.left(), gy + 14, label)
                for idx, (period, value_text) in enumerate((("30d", value30), ("180d", value180))):
                    yy = gy + idx * 22
                    user = _parse_percent(value_text) or 0
                    comm = self._comm_value(label, period)
                    painter.setPen(muted)
                    painter.setFont(QFont(painter.font().family(), 8))
                    painter.drawText(rect.left() + label_w - 28, yy + 4, period)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(track)
                    painter.drawRoundedRect(x, yy - 7, bar_w, 10, 5, 5)
                    if comm is not None:
                        painter.setBrush(community_color)
                        painter.drawRoundedRect(x, yy - 7, int(bar_w * min(100, max(0, float(comm))) / 100), 10, 5, 5)
                    painter.setBrush(accent)
                    painter.drawRoundedRect(x, yy - 7, int(bar_w * min(100, user) / 100), 10, 5, 5)
                    painter.setPen(muted)
                    painter.setFont(QFont(painter.font().family(), 8))
                    painter.drawText(x + bar_w + 8, yy + 4, value_text or 'sem dados')
                y += 50
        else:
            label_w = 110
            value_w = 72
            x = rect.left() + label_w
            bar_w = max(120, rect.width() - label_w - value_w - 10)
            for label, value_text in self.rows:
                user = _parse_percent(value_text) or 0
                comm = self._comm_value(label, '30d')
                painter.setPen(text)
                painter.setFont(QFont(painter.font().family(), 9))
                painter.drawText(rect.left(), y + 10, label)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(track)
                painter.drawRoundedRect(x, y, bar_w, 12, 6, 6)
                if comm is not None:
                    painter.setBrush(community_color)
                    painter.drawRoundedRect(x, y, int(bar_w * min(100, max(0, float(comm))) / 100), 12, 6, 6)
                painter.setBrush(accent)
                painter.drawRoundedRect(x, y, int(bar_w * min(100, user) / 100), 12, 6, 6)
                painter.setPen(muted)
                painter.drawText(x + bar_w + 8, y + 10, value_text or 'sem dados')
                y += 34
            legend = self.legend_text
            if legend is None:
                legend = 'Azul: você · Laranja: média da comunidade' if self.community else 'Azul: você · média da comunidade após a coleta'
            painter.setPen(muted)
            painter.setFont(QFont(painter.font().family(), 8))
            painter.drawText(x, rect.bottom(), legend)


class CollectionBarsChart(QWidget):
    def __init__(self, rows, title, parent=None):
        super().__init__(parent)
        self.rows = rows or []
        self.title = title
        self.setMinimumHeight(190 + max(0, len(self.rows) - 4) * 34)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = QApplication.palette()
        text = pal.text().color()
        accent = pal.highlight().color()
        window = pal.window().color()
        muted = _mix(text, window, 0.48)
        track = _mix(text, window, 0.78)
        rect = self.rect().adjusted(12, 12, -12, -12)
        painter.setPen(text)
        painter.setFont(QFont(painter.font().family(), 10, QFont.Weight.DemiBold))
        painter.drawText(rect.left(), rect.top(), self.title)
        max_value = max((_bucket_mid_numeric(v) or 0 for _, v in self.rows), default=1) or 1
        y = rect.top() + 38
        label_w = 102
        bar_w = max(120, rect.width() - label_w - 120)
        for label, value in self.rows:
            val = _bucket_mid_numeric(value) or 0
            x = rect.left() + label_w
            painter.setPen(text)
            painter.setFont(QFont(painter.font().family(), 9))
            painter.drawText(rect.left(), y + 5, label)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(track)
            painter.drawRoundedRect(x, y - 4, bar_w, 13, 6, 6)
            painter.setBrush(accent)
            painter.drawRoundedRect(x, y - 4, int(bar_w * min(1, val / max_value)), 13, 6, 6)
            painter.setPen(muted)
            painter.drawText(x + bar_w + 10, y + 5, value or "sem dados")
            y += 42


class SemesterEvolutionChart(QWidget):
    def __init__(self, months, parent=None):
        super().__init__(parent)
        self.months = months or []
        self.setMinimumHeight(260)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        pal = QApplication.palette()
        text = pal.text().color()
        accent = pal.highlight().color()
        window = pal.window().color()
        muted = _mix(text, window, 0.5)
        grid = _mix(text, window, 0.84)
        line_color = QColor('#d88c4a') if window.lightness() < 128 else QColor('#c56a2d')
        rect = self.rect().adjusted(12, 10, -12, -18)
        if not self.months:
            painter.setPen(muted)
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), 'Sem dados mensais')
            return
        # description
        painter.setPen(muted)
        painter.setFont(QFont(painter.font().family(), 8))
        painter.drawText(rect.left(), rect.top() + 4, 'Barras = reviews por mês (eixo esquerdo). Linha = retenção mensal (eixo direito).')
        chart = rect.adjusted(0, 22, 0, -8)
        labels = [m.get('month_label', '') for m in self.months]
        reviews = [int(m.get('reviews') or 0) for m in self.months]
        rets = [m.get('retention') for m in self.months]
        max_rev = max(reviews) or 1
        min_ret = min([float(r) for r in rets if r is not None] or [80.0])
        max_ret = max([float(r) for r in rets if r is not None] or [100.0])
        min_ret = min(min_ret, 80.0)
        max_ret = max(max_ret, 100.0)
        if max_ret - min_ret < 8:
            pad = (8 - (max_ret - min_ret)) / 2
            min_ret -= pad; max_ret += pad
        left_axis_w = 52
        right_axis_w = 44
        bottom_axis_h = 26
        chart_left = chart.left() + left_axis_w
        chart_right = chart.right() - right_axis_w
        chart_bottom = chart.bottom() - bottom_axis_h
        chart_top = chart.top() + 8
        height = max(30, chart_bottom - chart_top)
        width = max(60, chart_right - chart_left)
        # horizontal grid and y labels
        painter.setFont(QFont(painter.font().family(), 8))
        for i in range(5):
            frac = i / 4
            y = chart_bottom - int(height * frac)
            painter.setPen(grid)
            painter.drawLine(chart_left, y, chart_right, y)
            painter.setPen(muted)
            rev_val = int(max_rev * frac)
            painter.drawText(chart.left(), y + 4, str(rev_val))
            ret_val = min_ret + (max_ret - min_ret) * frac
            painter.drawText(chart_right + 8, y + 4, f"{ret_val:.0f}%")
        painter.setPen(muted)
        painter.drawText(chart.left(), chart_top - 2, 'reviews')
        painter.drawText(chart_right + 8, chart_top - 2, 'retenção')
        gap = 16
        bar_w = max(18, (width - gap * (len(reviews) - 1)) / max(1, len(reviews)))
        points = []
        for i, rev in enumerate(reviews):
            x = chart_left + i * (bar_w + gap)
            h = int(height * rev / max_rev)
            y = chart_bottom - h
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_mix(accent, window, 0.35))
            painter.drawRoundedRect(int(x), int(y), int(bar_w), int(max(5, h)), 5, 5)
            ret = rets[i]
            if ret is not None:
                ret_float = float(ret)
                py = chart_bottom - int(height * ((ret_float - min_ret) / max(0.0001, (max_ret - min_ret))))
                points.append((int(x + bar_w / 2), py))
            painter.setPen(muted)
            painter.drawText(int(x - 2), chart_bottom + 16, labels[i].split('/')[0])
        if len(points) >= 2:
            painter.setPen(QPen(line_color, 3))
            for a, b in zip(points, points[1:]):
                painter.drawLine(a[0], a[1], b[0], b[1])
            painter.setBrush(line_color)
            painter.setPen(Qt.PenStyle.NoPen)
            for x, y in points:
                painter.drawEllipse(x - 4, y - 4, 8, 8)


BADGE_RULES = [
    ("Arquiteto de Decks", {"Coleção gigante", "Muitos decks", "Muitos tipos", "Templates customizados", "Automação"}),
    ("Engenheiro do FSRS", {"FSRS ativo", "FSRS quase total", "Retenção alta", "Baixo Again", "Consistente"}),
    ("Bibliotecário Caótico", {"Coleção gigante", "Muitos decks", "Muitas tags", "Muitos novos", "Suspensos altos"}),
    ("Monge da Retenção", {"Retenção alta", "Baixo Again", "Consistente", "FSRS ativo", "Rápido"}),
    ("DJ do TTS", {"Áudio forte", "Muitos arquivos", "Idiomas", "HyperTTS", "TTS/voz"}),
    ("Cientista do Anki", {"Ciência de dados", "Técnico", "Automação", "IA", "AnkiConnect"}),
    ("Mestre dos Addons", {"Muitos addons", "FSRS Helper", "Review Heatmap", "AnkiConnect", "Automação"}),
    ("Velocista Cognitivo", {"Rápido", "Muitos reviews", "Easy alto", "Retenção alta", "Consistente"}),
    ("Maratonista de Revisões", {"Muitos reviews", "Muito tempo", "Consistente", "180 dias forte", "Retenção alta"}),
    ("Curador de Biblioteca", {"Muitos novos", "Suspensos altos", "Muitas tags", "Coleção gigante", "Muitos tipos"}),
    ("Professor Pardal do Anki", {"Técnico", "JavaScript", "CSS", "Templates customizados", "Automação"}),
    ("Explorador Multilíngue", {"Idiomas", "Áudio forte", "TTS/voz", "AnkiDroid", "Consistente"}),
    ("Treinador de Algoritmo", {"FSRS ativo", "FSRS Helper", "Retenção alta", "Baixo Again", "Hard controlado"}),
    ("Acumulador Profissional", {"Coleção gigante", "Muitos novos", "Suspensos altos", "Muitos decks", "Muitos arquivos"}),
    ("Usuário Turbo", {"Muitos reviews", "Rápido", "Easy alto", "Muito tempo", "Consistente"}),
    ("Ninja do AnkiDroid", {"AnkiDroid", "Consistente", "Muitos reviews", "Retenção alta", "FSRS ativo"}),
    ("Operador de Pipeline", {"AnkiConnect", "Automação", "Mass creation", "Delimitadores", "IA"}),
    ("Estudante de Ferro", {"Consistente", "Muito tempo", "Muitos reviews", "Carga alta", "Retenção alta"}),
    ("Minerador de Cards", {"Muitos novos", "Mass creation", "Delimitadores", "Automação", "Coleção gigante"}),
    ("Colecionador Supremo", {"Coleção gigante", "Muitos arquivos", "Muitos decks", "Muitas tags", "Muitos tipos"}),
    ("Anki Sommelier", {"Easy alto", "Retenção alta", "Baixo Again", "FSRS ativo", "Rápido"}),
    ("Mago dos Templates", {"Templates customizados", "JavaScript", "CSS", "Muitos tipos", "Técnico"}),
    ("Radar de Consistência", {"Consistente", "180 dias forte", "Retenção alta", "Review Heatmap", "Baixo Again"}),
    ("Domador de Backlog", {"Carga alta", "Muitos reviews", "Suspensos altos", "Muitos novos", "FSRS ativo"}),
    ("Laboratório de IA", {"IA", "TTS/voz", "AnkiExplain", "Gemini", "Técnico"}),
    ("Minimalista Improvável", {"Baixos enterrados", "Baixo Again", "Retenção alta", "FSRS ativo", "Rápido"}),
    ("General dos Presets", {"FSRS quase total", "Muitos presets", "Muitos decks", "FSRS ativo", "Técnico"}),
    ("Historiador do Revlog", {"180 dias forte", "Muitos reviews", "Muito tempo", "Consistente", "Retenção alta"}),
    ("Construtor de Império", {"Coleção gigante", "Muitos decks", "Muitos novos", "Muitos arquivos", "Automação"}),
    ("Anki Wrapped Material", {"Muitos reviews", "Top comunidade", "Retenção alta", "Muitos addons", "Consistente"}),
]


class SummaryTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.payload = None
        self.results = None
        self.error = None
        self.tokens = _theme_tokens()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        root.addWidget(self.scroll)
        self.container = QWidget()
        self.container.setObjectName("summaryContainer")
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(18, 18, 18, 18)
        self.layout.setSpacing(14)
        self.scroll.setWidget(self.container)
        self._apply_styles()
        self.refresh()

    def _apply_styles(self):
        t = self.tokens
        self.setStyleSheet(f"""
            QWidget {{ font-size: 13px; color: {t['text']}; }}
            QWidget#summaryContainer, QScrollArea {{ background: {t['window']}; }}
            QLabel {{ background-color: transparent; color: {t['text']}; }}
            QLabel#heroTitle {{ font-size: 28px; font-weight: 800; }}
            QLabel#heroSubtitle {{ color: {t['muted']}; font-size: 14px; }}
            QLabel#metaText {{ color: {t['muted']}; font-size: 12px; }}
            QLabel#sectionTitle {{ font-size: 19px; font-weight: 760; margin-top: 8px; }}
            QFrame#heroBox, QFrame#metricCard, QFrame#insightCard, QFrame#shareBox, QFrame#profileBox, QFrame#chartCard {{
                background-color: {t['card']}; border: 1px solid {t['border']}; border-radius: 16px;
            }}
            QFrame#heroBox {{ background-color: {t['hero']}; }}
            QLabel#cardTitle, QLabel#insightTitle, QLabel#profileEyebrow {{ color: {t['muted']}; font-weight: 650; }}
            QLabel#cardValue {{ font-size: 21px; font-weight: 800; }}
            QLabel#cardNote, QLabel#insightBody, QLabel#profileBody {{ color: {t['muted']}; }}
            QLabel#profileTitle {{ font-size: 22px; font-weight: 800; }}
            QLabel#badgeLabel {{ background-color: {t['soft']}; border: 1px solid {t['border']}; border-radius: 999px; padding: 4px 10px; font-weight: 650; }}
            QPushButton {{ padding: 8px 12px; border-radius: 10px; border: 1px solid {t['border']}; background: {t['card']}; color: {t['text']}; }}
            QPushButton:hover {{ background: {t['soft']}; }}
            QProgressBar {{ border: 0; border-radius: 5px; background: {t['border']}; }}
            QProgressBar::chunk {{ border-radius: 5px; background: {t['accent']}; }}
        """)

    def _clear(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def refresh(self):
        self.tokens = _theme_tokens()
        self._apply_styles()
        self._clear()
        info = current_survey_for_day()
        try:
            self.payload = build_payload(info["survey_id"], mode="preview")
        except Exception as exc:
            self.error = str(exc)
            self.payload = None
        try:
            data = fetch_public_results()
            self.results = (data or {}).get("results", {})
        except Exception:
            self.results = None
        self._render()

    def _survey_results(self):
        if not self.results or not self.payload:
            return None
        return self.results.get(self.payload.get("survey_id")) or next(iter(self.results.values()), None)

    def _comparison_group(self, kind, key):
        res = self._survey_results() or {}
        comp = res.get("community_comparison") or {}
        return (comp.get(kind) or {}).get(key)

    def _global_comparison(self):
        res = self._survey_results() or {}
        return ((res.get("community_comparison") or {}).get("global") or {}) if res else {}

    def _add_section_title(self, text):
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        self.layout.addWidget(label)

    def _render(self):
        if self.error or not self.payload:
            self.layout.addWidget(QLabel(f"Não foi possível montar o resumo local: {self.error}"))
            return
        p = self.payload
        collection = p.get("collection", {})
        scheduling = p.get("scheduling", {})
        a30 = p.get("activity", {}).get("last_30_days", {})
        media = p.get("media", {})
        addons = p.get("addons", {})
        info = current_survey_for_day()
        cfg = load_config()
        sent = cfg.get("local_state", {}).get("sent_surveys", {}).get(info["survey_id"])
        status = "pausada" if cfg.get("participation_paused") else "ativa"

        hero = QFrame(); hero.setObjectName("heroBox")
        h = QVBoxLayout(hero); h.setContentsMargins(18, 16, 18, 16)
        title = QLabel("Meu Anki"); title.setObjectName("heroTitle")
        subtitle = QLabel("Sua retrospectiva do Anki: ritmo de estudo, retenção, setup, comunidade e os dados que entram no Censo Anki Brasil.")
        subtitle.setObjectName("heroSubtitle"); subtitle.setWordWrap(True)
        meta = QLabel(f"Coleta <b>{status}</b> · Janela <b>{info['start']} a {info['end']}</b> · Último envio <b>{sent or 'ainda não enviado'}</b>")
        meta.setObjectName("metaText"); meta.setWordWrap(True)
        h.addWidget(title); h.addWidget(subtitle); h.addSpacing(6); h.addWidget(meta)
        self.layout.addWidget(hero)

        global_comp = self._global_comparison()
        dist = global_comp.get("distributions", {})
        top_cards = _top_percent_for_bucket(collection.get("card_count_bucket"), dist.get("card_count_buckets"))
        top_reviews = _top_percent_for_bucket(a30.get("reviews_bucket"), dist.get("reviews_last_30_days"))
        top_study = _top_percent_for_bucket(a30.get("study_time_bucket"), dist.get("study_time_last_30_days"))
        top_addons = _top_percent_for_bucket(addons.get("enabled_addon_count_bucket"), dist.get("enabled_addon_count_buckets"))
        top_consistency = _top_percent_for_bucket(a30.get("study_days_bucket"), dist.get("study_days_last_30_days"))
        ret_pct = _percentile_for_percent(a30.get("retention_bucket"), dist.get("retention_last_30_days"))

        self._add_section_title("Destaques")
        grid = QGridLayout(); grid.setSpacing(12)
        cards = [
            ("Cards", _clean(collection.get("card_count_bucket")), f"tamanho da coleção{f' · top {top_cards}%' if top_cards else ''}"),
            ("Reviews em 31 dias", _clean(a30.get("reviews_bucket")), f"ritmo recente{f' · top {top_reviews}%' if top_reviews else ''}"),
            ("Retenção recente", _clean(a30.get("retention_bucket")), f"{f'acima de {ret_pct}% da comunidade' if ret_pct else 'precisão recente'}"),
            ("Dias estudados", _clean(a30.get("study_days_bucket")), "janela recente"),
            ("Tempo de estudo", _clean(a30.get("study_time_bucket")), f"janela recente{f' · top {top_study}%' if top_study else ''}"),
            ("Addons ativos", _clean(addons.get("enabled_addon_count_bucket")), f"sem contar o Censo{f' · top {top_addons}%' if top_addons else ''}"),
            ("FSRS", "Ativado" if scheduling.get("fsrs_enabled") else "Desativado", _clean(scheduling.get("fsrs_enabled_preset_ratio_bucket"))),
            ("Áudio", _clean(media.get("notes_with_audio_ratio_bucket")), "notas com áudio"),
        ]
        for i, c in enumerate(cards):
            grid.addWidget(MetricCard(*c), i // 4, i % 4)
        self.layout.addLayout(grid)

        self._add_section_title("Você está no top X%")
        self._render_top_percent_cards(top_reviews, top_study, top_cards, ret_pct, top_addons, top_consistency)

        self._add_section_title("Seu perfil de uso")
        self.layout.addWidget(self._profile_box(p))

        self._add_section_title("Comparação com a comunidade")
        self._render_community_cards(p)

        self._add_section_title(self._semester_title())
        self._render_semester_cards(p)

        self._add_section_title("Sua área, região e setup")
        self._render_area_region_addons(p)

        self._add_section_title("Compartilhar")
        self.layout.addWidget(self._share_box())
        self.layout.addStretch(1)

    def _render_top_percent_cards(self, top_reviews, top_study, top_cards, ret_pct, top_addons, top_consistency):
        grid = QGridLayout(); grid.setSpacing(12)
        specs = [
            ("Reviews", f"Top {top_reviews}%" if top_reviews else "Após coleta", "posição em reviews recentes"),
            ("Tempo", f"Top {top_study}%" if top_study else "Após coleta", "posição em tempo de estudo"),
            ("Cards", f"Top {top_cards}%" if top_cards else "Após coleta", "tamanho da coleção"),
            ("Retenção", f"Acima de {ret_pct}%" if ret_pct else "Após coleta", "comparação por retenção"),
            ("Addons", f"Top {top_addons}%" if top_addons else "Após coleta", "setup de addons ativos"),
            ("Consistência", f"Top {top_consistency}%" if top_consistency else "Após coleta", "dias estudados na janela recente"),
        ]
        for i, s in enumerate(specs):
            grid.addWidget(MetricCard(*s), i // 3, i % 3)
        self.layout.addLayout(grid)

    def _semester_title(self):
        sid = (self.payload or {}).get("survey_id") or ""
        m = re.search(r"(20\d{2})-(\d)$", sid)
        return f"Seu semestre no Anki · {m.group(2)}º semestre de {m.group(1)}" if m else "Seu semestre no Anki"

    def _score_traits(self, p):
        c = p.get("collection", {}); m = p.get("media", {}); s = p.get("scheduling", {})
        a30 = p.get("activity", {}).get("last_30_days", {}); a180 = p.get("activity", {}).get("last_180_days", {})
        templates = p.get("templates", {}); profile = p.get("profile_optional", {}).get("values", {})
        addons = p.get("addons", {}).get("items", [])
        addon_names = " ".join((ad.get("name") or "") for ad in addons).lower()
        traits = []
        def add(name, score, desc):
            if score > 0: traits.append((score, name, desc))
        add("Coleção gigante", 95 if _extract_first_number(c.get("card_count_bucket")) >= 100000 else 0, "coleção muito acima do comum")
        add("Muitos decks", 85 if _extract_first_number(c.get("deck_count_bucket")) >= 100 else 0, "organização bem fragmentada")
        add("Muitas tags", 70 if _extract_first_number(c.get("tag_count_bucket")) >= 500 else 0, "uso forte de tags")
        add("Muitos novos", 90 if _extract_first_number(c.get("new_cards_bucket")) >= 25000 else 0, "grande estoque de cards novos")
        add("Suspensos altos", 65 if _extract_first_number(c.get("suspended_cards_bucket")) >= 5000 else 0, "muito material suspenso/curado")
        add("Carga alta", 70 if _extract_first_number(c.get("due_today_bucket")) >= 1000 else 0, "fila diária pesada")
        add("FSRS ativo", 75 if s.get("fsrs_enabled") else 0, "agendamento moderno")
        add("FSRS quase total", 80 if (_parse_percent(s.get("fsrs_enabled_preset_ratio_bucket")) or 0) >= 90 else 0, "FSRS em quase todos os presets")
        add("Muitos presets", 50 if _extract_first_number(s.get("deck_preset_count_bucket")) >= 6 else 0, "vários presets de deck")
        add("Retenção alta", 70 if (_parse_percent(a30.get("retention_bucket")) or 0) >= 90 else 0, "retenção recente forte")
        add("Baixo Again", 60 if (_parse_percent(a30.get("again_rate_bucket")) or 100) <= 10 else 0, "poucos erros recentes")
        add("Hard controlado", 40 if (_parse_percent(a30.get("hard_rate_bucket")) or 100) <= 15 else 0, "baixa taxa de Hard")
        add("Easy alto", 55 if (_parse_percent(a30.get("easy_rate_bucket")) or 0) >= 30 else 0, "muitos cards fáceis")
        add("Consistente", 80 if _extract_first_number(a30.get("study_days_bucket")) >= 25 else 55 if _extract_first_number(a30.get("study_days_bucket")) >= 20 else 0, "boa frequência recente")
        add("180 dias forte", 75 if _extract_first_number(a180.get("study_days_bucket")) >= 140 else 0, "consistência longa")
        add("Muitos reviews", 80 if _extract_first_number(a30.get("reviews_bucket")) >= 5000 else 0, "alto volume recente")
        add("Muito tempo", 60 if (_parse_time_bucket_hours(a30.get("study_time_bucket")) or 0) >= 7.5 else 0, "tempo de estudo relevante")
        add("Rápido", 70 if _extract_first_number(a30.get("avg_answer_time_bucket")) <= 7 else 0, "respostas muito rápidas")
        add("Áudio forte", 85 if (_parse_percent(m.get("notes_with_audio_ratio_bucket")) or 0) >= 25 else 0, "muitas notas com áudio")
        add("Muitos arquivos", 75 if _extract_first_number(m.get("media_file_count_bucket")) >= 50000 else 0, "pasta de mídia enorme")
        add("Visual", 45 if (_parse_percent(m.get("notes_with_images_ratio_bucket")) or 0) >= 10 else 0, "uso relevante de imagens")
        add("Técnico", 65 if profile.get("self_assessed_level") in {"Usuário técnico", "Crio templates/scripts/addons"} else 0, "perfil técnico declarado")
        add("Templates customizados", 60 if _extract_first_number(templates.get("card_template_count_bucket")) >= 50 else 0, "muitos modelos de card")
        add("JavaScript", 65 if templates.get("uses_javascript_in_templates") else 0, "JavaScript em templates")
        add("CSS", 55 if templates.get("uses_css_customization") else 0, "CSS customizado")
        add("Muitos tipos", 55 if _extract_first_number(templates.get("note_type_count_bucket")) >= 30 else 0, "muitos tipos de nota")
        add("Idiomas", 55 if any(x in str(profile.get("secondary_areas", [])) for x in ["Inglês", "Espanhol", "Francês", "Idiomas"]) or profile.get("primary_area") in {"Idiomas", "Inglês", "Espanhol", "Francês"} else 0, "uso ligado a idiomas")
        add("Ciência de dados", 50 if profile.get("primary_area") == "Ciência de dados" else 0, "área de dados")
        add("AnkiDroid", 40 if "AnkiDroid" in (profile.get("platforms_used") or []) else 0, "usa também no Android")
        add("AnkiConnect", 55 if "ankiconnect" in addon_names else 0, "integração externa")
        add("Review Heatmap", 40 if "heatmap" in addon_names else 0, "acompanha sequência")
        add("FSRS Helper", 45 if "fsrs helper" in addon_names else 0, "usa ferramentas FSRS extras")
        add("Automação", 60 if any(x in addon_names for x in ["connect", "mass", "delimitadores"]) else 0, "sinais de automação/importação")
        add("Mass creation", 45 if "mass deck" in addon_names else 0, "criação em massa")
        add("Delimitadores", 40 if "delimit" in addon_names or "delimitadores" in addon_names else 0, "importação por delimitadores")
        add("IA", 60 if any(x in addon_names for x in ["gemini", "explain", "gpt", "ai"]) else 0, "uso de IA")
        add("AnkiExplain", 45 if "ankiexplain" in addon_names else 0, "explicação automática")
        add("Gemini", 45 if "gemini" in addon_names else 0, "Gemini no fluxo")
        add("TTS/voz", 60 if any(x in addon_names for x in ["tts", "speak"]) else 0, "voz/áudio no estudo")
        add("Top comunidade", 50 if (self._global_comparison() and _top_percent_for_bucket(a30.get("reviews_bucket"), self._global_comparison().get("distributions", {}).get("reviews_last_30_days"))) else 0, "comparável com comunidade")
        add("Baixos enterrados", 25 if c.get("buried_cards_bucket") == "0" else 0, "sem cards enterrados no momento")
        traits.sort(key=lambda x: (-x[0], x[1]))
        return [{"name": name, "score": score, "description": desc} for score, name, desc in traits]

    def _choose_badge(self, trait_names, fingerprint):
        names = set(trait_names)
        matches = [(badge, keys) for badge, keys in BADGE_RULES if len(names & keys) >= 3]
        if not matches:
            return "Perfil em Formação"
        seed = fingerprint or ensure_user_id()
        idx = int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16) % len(matches)
        return matches[idx][0]

    def _profile_cache(self, p):
        sid = p.get("survey_id") or current_survey_for_day()["survey_id"]
        cfg = load_config(); st = cfg.setdefault("local_state", {}); cache = st.setdefault("wrapped_profile_cache", {})
        if sid in cache and cache[sid].get("traits") and cache[sid].get("badge"):
            return cache[sid]
        traits = self._score_traits(p)[:5]
        names = [t["name"] for t in traits]
        badge = self._choose_badge(names + [t["name"] for t in self._score_traits(p)], p.get("analysis", {}).get("usage_fingerprint"))
        cache[sid] = {"traits": traits, "badge": badge}
        save_config(cfg)
        return cache[sid]

    def _profile_box(self, p):
        prof = self._profile_cache(p)
        box = QFrame(); box.setObjectName("profileBox")
        layout = QVBoxLayout(box); layout.setContentsMargins(18, 16, 18, 16)
        eyebrow = QLabel("Perfil fixado até o próximo ciclo do censo"); eyebrow.setObjectName("profileEyebrow")
        title = QLabel(prof.get("badge", "Perfil")); title.setObjectName("profileTitle")
        body = QLabel("Este é seu perfil estilo Wrapped: as 5 características mais fortes do seu Anki, geradas a partir dos dados agregados da coleção.")
        body.setObjectName("profileBody"); body.setWordWrap(True)
        layout.addWidget(eyebrow); layout.addWidget(title); layout.addWidget(body)
        row = QHBoxLayout()
        for t in prof.get("traits", [])[:5]:
            row.addWidget(BadgeLabel(t.get("name", "")))
        row.addStretch(1); layout.addLayout(row)
        for t in prof.get("traits", [])[:5]:
            lbl = QLabel(f"• {t.get('name')}: {t.get('description')}")
            lbl.setObjectName("insightBody"); lbl.setWordWrap(True); layout.addWidget(lbl)
        return box

    def _render_community_cards(self, p):
        res = self._survey_results(); global_comp = self._global_comparison(); dist = global_comp.get("distributions", {})
        if not res or not res.get("total_responses"):
            self.layout.addWidget(InsightCard("Comparações disponíveis após a coleta", "Quando houver respostas públicas, esta área mostrará percentis, médias por área, estado/região e distribuição da comunidade.", None))
        else:
            a30 = p.get("activity", {}).get("last_30_days", {}); c = p.get("collection", {}); addons = p.get("addons", {})
            grid = QGridLayout(); grid.setSpacing(12)
            specs = [
                ("Tempo de estudo", a30.get("study_time_bucket"), dist.get("study_time_last_30_days"), "top {x}% em tempo de estudo"),
                ("Reviews", a30.get("reviews_bucket"), dist.get("reviews_last_30_days"), "top {x}% em reviews recentes"),
                ("Cards totais", c.get("card_count_bucket"), dist.get("card_count_buckets"), "top {x}% em tamanho da coleção"),
                ("Addons ativos", addons.get("enabled_addon_count_bucket"), dist.get("enabled_addon_count_buckets"), "top {x}% em addons ativos"),
            ]
            for i, (title, value, d, tpl) in enumerate(specs):
                top = _top_percent_for_bucket(value, d)
                body = f"Você ficou aproximadamente no {tpl.format(x=top)}. Valor: {value}." if top else f"Seu valor: {value or 'sem dados'}."
                grid.addWidget(InsightCard(title, body, 100 - top if top else None), i // 2, i % 2)
            self.layout.addLayout(grid)

        charts = QGridLayout(); charts.setSpacing(12)
        a30 = p.get("activity", {}).get("last_30_days", {})
        a180 = p.get("activity", {}).get("last_180_days", {})
        m = p.get("media", {})
        avgs = (global_comp.get("averages") or {})
        avg_rates30 = avgs.get("last_30_rates") or {}
        avg_rates180 = avgs.get("last_180_rates") or {}
        button_chart = HorizontalPercentChart("", [
            ("Again", a30.get("again_rate_bucket"), a180.get("again_rate_bucket")),
            ("Hard", a30.get("hard_rate_bucket"), a180.get("hard_rate_bucket")),
            ("Good", a30.get("good_rate_bucket"), a180.get("good_rate_bucket")),
            ("Easy", a30.get("easy_rate_bucket"), a180.get("easy_rate_bucket")),
        ], {
            "Again": {"30d": avg_rates30.get("again"), "180d": avg_rates180.get("again")},
            "Hard": {"30d": avg_rates30.get("hard"), "180d": avg_rates180.get("hard")},
            "Good": {"30d": avg_rates30.get("good"), "180d": avg_rates180.get("good")},
            "Easy": {"30d": avg_rates30.get("easy"), "180d": avg_rates180.get("easy")},
        })
        charts.addWidget(self._chart_card("Botões de resposta", button_chart), 0, 0, 1, 2)
        media_chart = HorizontalPercentChart("", [
            ("Áudio", m.get("audio_file_ratio_bucket")), ("Imagens", m.get("image_file_ratio_bucket")), ("Vídeo", m.get("video_file_ratio_bucket")), ("Notas c/ áudio", m.get("notes_with_audio_ratio_bucket")), ("Notas c/ imagem", m.get("notes_with_images_ratio_bucket")),
        ], legend_text='Azul: você · Laranja: média da comunidade após a coleta')
        media_chart.setMinimumHeight(max(media_chart.minimumHeight(), 210))
        charts.addWidget(self._chart_card("Composição da mídia", media_chart), 1, 0, 1, 2)
        self.layout.addLayout(charts)

        if dist:
            dgrid = QGridLayout(); dgrid.setSpacing(12)
            dgrid.addWidget(self._chart_card("Distribuição de reviews", DistributionChart(dist.get("reviews_last_30_days"), a30.get("reviews_bucket"), "Reviews em 31 dias")), 0, 0)
            dgrid.addWidget(self._chart_card("Distribuição de tempo", DistributionChart(dist.get("study_time_last_30_days"), a30.get("study_time_bucket"), "Tempo de estudo")), 0, 1)
            dgrid.addWidget(self._chart_card("Distribuição de cards", DistributionChart(dist.get("card_count_buckets"), c.get("card_count_bucket"), "Cards totais")), 1, 0)
            dgrid.addWidget(self._chart_card("Distribuição de retenção", DistributionChart(dist.get("retention_last_30_days"), a30.get("retention_bucket"), "Retenção recente")), 1, 1)
            self.layout.addLayout(dgrid)

    def _chart_card(self, title, widget):
        card = QFrame(); card.setObjectName("chartCard")
        layout = QVBoxLayout(card); layout.setContentsMargins(14, 12, 14, 12)
        lbl = QLabel(title); lbl.setObjectName("insightTitle")
        layout.addWidget(lbl); layout.addWidget(widget)
        return card

    def _render_semester_cards(self, p):
        a30 = p.get("activity", {}).get("last_30_days", {}); a180 = p.get("activity", {}).get("last_180_days", {})
        months = p.get("activity", {}).get("semester_months", [])
        moments = self._semester_moments(months)
        grid = QGridLayout(); grid.setSpacing(12)
        grid.addWidget(InsightCard("Recorte recente", f"{a30.get('reviews_bucket', 'sem dados')} reviews, {a30.get('study_days_bucket', 'sem dados')} dias estudados e retenção de {a30.get('retention_bucket', 'sem dados')}."), 0, 0)
        grid.addWidget(InsightCard("Janela ampliada", f"{a180.get('reviews_bucket', 'sem dados')} reviews, {a180.get('study_days_bucket', 'sem dados')} dias estudados e retenção de {a180.get('retention_bucket', 'sem dados')}."), 0, 1)
        grid.addWidget(InsightCard("Seu momento mais intenso", moments[0]), 1, 0)
        grid.addWidget(InsightCard("Leitura do semestre", moments[1]), 1, 1)
        self.layout.addLayout(grid)
        self.layout.addWidget(self._chart_card("Evolução do semestre", SemesterEvolutionChart(months)))

    def _semester_moments(self, months):
        if not months:
            return ("Dados mensais aparecem quando houver revlog suficiente.", "A evolução do semestre será calculada pelos meses recentes.")
        max_rev = max(months, key=lambda m: int(m.get("reviews") or 0))
        max_days = max(months, key=lambda m: int(m.get("study_days") or 0))
        first = months[0]; last = months[-1]
        trend = "Seu ritmo aumentou no fim do semestre." if int(last.get("reviews") or 0) > int(first.get("reviews") or 0) else "Seu ritmo ficou mais leve no fim do semestre."
        ret_first = first.get("retention"); ret_last = last.get("retention")
        if ret_first is not None and ret_last is not None and abs(float(ret_last) - float(ret_first)) < 2:
            trend += " A retenção se manteve estável."
        elif ret_first is not None and ret_last is not None and float(ret_last) > float(ret_first):
            trend += " A retenção melhorou no período."
        return (
            f"Seu pico foi em {max_rev.get('month_label')}: {max_rev.get('reviews')} reviews. O mês mais consistente foi {max_days.get('month_label')}: {max_days.get('study_days')} dias estudados.",
            trend,
        )

    def _render_area_region_addons(self, p):
        profile = p.get("profile_optional", {}).get("values", {})
        primary = profile.get("primary_area")
        state = profile.get("state")
        region = REGION_BY_STATE.get(state or "")
        a30 = p.get("activity", {}).get("last_30_days", {})
        media = p.get("media", {})
        addons = p.get("addons", {}).get("items", [])
        res = self._survey_results() or {}
        grid = QGridLayout(); grid.setSpacing(12)
        if primary and primary != "Prefiro não informar":
            area = self._comparison_group("by_primary_area", primary)
            if area:
                avg = area.get("averages", {})
                body = f"Na área {primary}, a retenção média recente foi {_avg_text(avg.get('retention30'))}. Usuários da área usam áudio em média em {_avg_text(avg.get('notesWithAudio'))} das notas. Você usa {media.get('notes_with_audio_ratio_bucket', 'sem dados')}."
            else:
                body = f"Quando houver respostas suficientes em {primary}, aqui aparecerão médias da sua área."
            grid.addWidget(InsightCard("Sua área", body), 0, 0)
        region_parts = []
        if region:
            rg = self._comparison_group("by_region", region)
            if rg:
                avg = rg.get("averages", {})
                region_parts.append(f"No {region}, a retenção média foi {_avg_text(avg.get('retention30'))} e o uso médio de FSRS por preset foi {_avg_text(avg.get('fsrsPresetRatio'))}.")
        if state:
            sg = self._comparison_group("by_state", state)
            if sg:
                avg = sg.get("averages", {})
                region_parts.append(f"No {state}, a retenção média foi {_avg_text(avg.get('retention30'))}.")
        grid.addWidget(InsightCard("Estado e região", " ".join(region_parts) if region_parts else "Comparações por estado e região aparecem depois que houver dados suficientes."), 0, 1)

        top_addons = (res.get("top_addons") or [])[:10]
        top_names = [str(x.get("name", "")).split(" (")[0].lower() for x in top_addons]
        user_names = [str(ad.get("name", "")) for ad in addons]
        hit = sum(1 for n in user_names if n.lower() in top_names)
        rare = [n for n in user_names if n and n.lower() not in top_names][:3]
        if top_addons:
            body = f"Você usa {hit} dos 10 addons mais populares da comunidade."
            if rare:
                body += " Seus addons mais raros neste recorte: " + ", ".join(rare) + "."
        else:
            body = "Depois da coleta, este card vai mostrar quantos dos seus addons estão entre os mais populares e quais parecem mais raros."
        grid.addWidget(InsightCard("Seu setup de addons", body), 1, 0, 1, 2)
        self.layout.addLayout(grid)

    def _share_text(self):
        p = self.payload or {}; a30 = p.get("activity", {}).get("last_30_days", {}); c = p.get("collection", {}); addons = p.get("addons", {})
        badge = self._profile_cache(p).get("badge", "Perfil") if p else "Perfil"
        top_reviews = _top_percent_for_bucket(a30.get("reviews_bucket"), self._global_comparison().get("distributions", {}).get("reviews_last_30_days"))
        return (
            "Meu Anki — Censo Anki Brasil\n"
            f"Perfil: {badge}\n"
            f"Cards: {c.get('card_count_bucket', 'sem dados')}\n"
            f"Reviews recentes: {a30.get('reviews_bucket', 'sem dados')}\n"
            f"Retenção: {a30.get('retention_bucket', 'sem dados')}\n"
            f"Addons ativos: {addons.get('enabled_addon_count_bucket', 'sem dados')}\n"
            + (f"Top comunidade: {top_reviews}% em reviews\n" if top_reviews else "") +
            "Projeto: Censo Anki Brasil"
        )

    def _copy_share_card(self):
        QApplication.clipboard().setText(self._share_text())

    def _open_results(self):
        base = (load_config().get("api_base_url") or "").rstrip("/")
        if base:
            webbrowser.open(base + "/results.html")

    def _share_box(self):
        box = QFrame(); box.setObjectName("shareBox")
        layout = QVBoxLayout(box); layout.setContentsMargins(14, 12, 14, 12)
        txt = QLabel(f"Seu ID anônimo é <b>{ensure_user_id()}</b>. Exporte o painel em PDF ou gere um card visual do seu perfil para compartilhar.")
        txt.setObjectName("insightBody"); txt.setWordWrap(True); layout.addWidget(txt)
        row = QHBoxLayout()
        buttons = [
            ("Copiar ID anônimo", lambda: QApplication.clipboard().setText(ensure_user_id())),
            ("Copiar resumo", self._copy_share_card),
            ("Exportar PDF", self._export_pdf),
            ("Exportar card", self._export_card),
            ("Ver resultados públicos", self._open_results),
            ("Atualizar painel", self.refresh),
        ]
        for label, fn in buttons:
            b = QPushButton(label); b.clicked.connect(fn); row.addWidget(b)
        row.addStretch(1); layout.addLayout(row)
        return box

    def _grab_panel_image(self):
        self.container.adjustSize()
        size = self.container.size()
        image = QImage(size, QImage.Format.Format_ARGB32)
        image.fill(QColor(self.tokens["window"]))
        painter = QPainter(image); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.container.render(painter); painter.end()
        return image

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar PDF", "meu-anki-resumo.pdf", "PDF (*.pdf)")
        if not path:
            return
        image = self._grab_panel_image()
        writer = QPdfWriter(path); writer.setResolution(144)
        painter = QPainter(writer); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        page_w, page_h = writer.width(), writer.height()
        scale = page_w / max(1, image.width())
        slice_h = max(1, int(page_h / scale))
        y = 0
        while y < image.height():
            part_h = min(slice_h, image.height() - y)
            part = image.copy(0, y, image.width(), part_h)
            target_h = int(part.height() * scale)
            painter.drawImage(QRect(0, 0, page_w, target_h), part)
            y += part_h
            if y < image.height():
                writer.newPage()
        painter.end()

    def _render_share_card(self, painter, width, height):
        t = self.tokens
        p = self.payload or {}
        a30 = p.get("activity", {}).get("last_30_days", {})
        c = p.get("collection", {})
        addons = p.get("addons", {})
        sched = p.get("scheduling", {})
        media = p.get("media", {})
        profile = self._profile_cache(p) if p else {"badge": "Perfil", "traits": []}
        badge = profile.get("badge", "Perfil")
        traits = [tr.get("name", "") for tr in profile.get("traits", [])[:5]]
        global_dist = self._global_comparison().get("distributions", {})
        top_reviews = _top_percent_for_bucket(a30.get("reviews_bucket"), global_dist.get("reviews_last_30_days"))
        top_time = _top_percent_for_bucket(a30.get("study_time_bucket"), global_dist.get("study_time_last_30_days"))
        top_cards = _top_percent_for_bucket(c.get("card_count_bucket"), global_dist.get("card_count_buckets"))
        top_addons = _top_percent_for_bucket(addons.get("enabled_addon_count_bucket"), global_dist.get("enabled_addon_count_buckets"))
        ret_pct = _percentile_for_percent(a30.get("retention_bucket"), global_dist.get("retention_last_30_days"))

        base = QColor(t["window"])
        hero = QColor(t["hero"])
        accent = QColor(t["accent"])
        soft = QColor(t["soft"])
        text_color = QColor(t["text"])
        muted = QColor(t["muted"])
        community = QColor(t["community"])

        grad = QLinearGradient(0, 0, width, height)
        grad.setColorAt(0.0, _mix(hero, accent, 0.38))
        grad.setColorAt(0.35, _mix(base, accent, 0.18))
        grad.setColorAt(1.0, _mix(base, hero, 0.26))
        painter.fillRect(0, 0, width, height, grad)

        # decorative glows
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 34))
        painter.drawEllipse(-120, -90, 420, 420)
        painter.setBrush(QColor(community.red(), community.green(), community.blue(), 26))
        painter.drawEllipse(width - 280, 80, 360, 360)

        # main rounded panel with soft shadow
        shadow = QRect(54, 58, width - 108, height - 116)
        painter.setBrush(QColor(0, 0, 0, 28))
        painter.drawRoundedRect(shadow, 28, 28)
        panel = QRect(40, 40, width - 80, height - 100)
        painter.setBrush(QColor(_mix(QColor(t["card"]), base, 0.08)))
        painter.drawRoundedRect(panel, 28, 28)

        # header
        painter.setPen(text_color)
        painter.setFont(QFont("", 30, QFont.Weight.Bold))
        painter.drawText(panel.left() + 42, panel.top() + 54, "Meu Anki | 2026.1")
        painter.setPen(muted)
        painter.setFont(QFont("", 13, QFont.Weight.DemiBold))
        painter.drawText(panel.left() + 42, panel.top() + 80, "Seu Wrapped pessoal do Censo Anki Brasil")

        # badge block
        badge_rect = QRect(panel.left() + 34, panel.top() + 106, panel.width() - 68, 108)
        badge_grad = QLinearGradient(badge_rect.left(), badge_rect.top(), badge_rect.right(), badge_rect.bottom())
        badge_grad.setColorAt(0, _mix(soft, accent, 0.18))
        badge_grad.setColorAt(1, _mix(QColor(t["card"]), hero, 0.26))
        painter.setBrush(badge_grad)
        painter.drawRoundedRect(badge_rect, 24, 24)
        painter.setPen(muted)
        painter.setFont(QFont("", 11, QFont.Weight.DemiBold))
        painter.drawText(badge_rect.left() + 20, badge_rect.top() + 24, "BADGE DO SEMESTRE")
        painter.setPen(text_color)
        painter.setFont(QFont("", 24, QFont.Weight.Bold))
        painter.drawText(badge_rect.left() + 20, badge_rect.top() + 58, badge)
        summary = []
        if top_reviews:
            summary.append(f"Top {top_reviews}% em reviews")
        if ret_pct:
            summary.append(f"Acima de {ret_pct}% da comunidade em retenção")
        if top_time:
            summary.append(f"Top {top_time}% em tempo")
        summary_text = " · ".join(summary[:2]) or "Comparações públicas aparecem conforme a comunidade responde ao censo"
        painter.setPen(muted)
        painter.setFont(QFont("", 11))
        painter.drawText(QRect(badge_rect.left() + 20, badge_rect.top() + 68, badge_rect.width() - 40, 28), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), summary_text)

        # trait chips
        chip_y = badge_rect.bottom() + 18
        chip_x = panel.left() + 40
        for trait in traits[:5]:
            w = min(220, max(108, 20 + len(trait) * 7))
            if chip_x + w > panel.right() - 36:
                chip_y += 34
                chip_x = panel.left() + 40
            r = QRect(chip_x, chip_y, w, 26)
            painter.setBrush(_mix(soft, QColor(t["card"]), 0.32))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(r, 13, 13)
            painter.setPen(text_color)
            painter.setFont(QFont("", 10, QFont.Weight.DemiBold))
            painter.drawText(r, int(Qt.AlignmentFlag.AlignCenter), trait)
            chip_x += w + 10

        section_y = chip_y + 50
        # highlight row
        highlights = [
            ("Reviews", f"Top {top_reviews}%" if top_reviews else "após coleta"),
            ("Retenção", f"{ret_pct}%" if ret_pct else "após coleta"),
            ("Addons", f"Top {top_addons}%" if top_addons else addons.get("enabled_addon_count_bucket", "sem dados")),
        ]
        highlight_gap = 14
        hi_w = (panel.width() - 68 - 2 * highlight_gap) // 3
        for i, (label, val) in enumerate(highlights):
            r = QRect(panel.left() + 34 + i * (hi_w + highlight_gap), section_y, hi_w, 84)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_mix(QColor(t["card"]), base, 0.02))
            painter.drawRoundedRect(r, 20, 20)
            painter.setPen(muted)
            painter.setFont(QFont("", 10, QFont.Weight.DemiBold))
            painter.drawText(r.left() + 16, r.top() + 24, label)
            painter.setPen(text_color)
            painter.setFont(QFont("", 20, QFont.Weight.Bold))
            painter.drawText(r.left() + 16, r.top() + 56, val)

        # stats grid 2x3 modern
        y0 = section_y + 102
        stats = [
            ("Cards", c.get("card_count_bucket", "sem dados")),
            ("Reviews 31d", a30.get("reviews_bucket", "sem dados")),
            ("Retenção 31d", a30.get("retention_bucket", "sem dados")),
            ("Tempo 31d", a30.get("study_time_bucket", "sem dados")),
            ("FSRS", "Ativado" if sched.get("fsrs_enabled") else "Desativado"),
            ("Áudio", media.get("notes_with_audio_ratio_bucket", "sem dados")),
        ]
        grid_gap = 16
        box_w = (panel.width() - 68 - grid_gap) // 2
        box_h = 106
        for idx, (label, val) in enumerate(stats):
            row, col = divmod(idx, 2)
            r = QRect(panel.left() + 34 + col * (box_w + grid_gap), y0 + row * (box_h + 16), box_w, box_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_mix(QColor(t["card"]), base, 0.0))
            painter.drawRoundedRect(r, 20, 20)
            painter.setPen(muted)
            painter.setFont(QFont("", 10, QFont.Weight.DemiBold))
            painter.drawText(r.left() + 16, r.top() + 24, label)
            painter.setPen(text_color)
            painter.setFont(QFont("", 20, QFont.Weight.Bold))
            painter.drawText(QRect(r.left() + 16, r.top() + 34, r.width() - 32, 50), int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), str(val))

        footer_y = panel.bottom() - 36
        painter.setPen(muted)
        painter.setFont(QFont("", 10))
        painter.drawText(panel.left() + 38, footer_y, "censo-anki-brasil · github.com/danyelbarboza/censo-anki-brasil")

    def _export_card(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar card", "meu-anki-card.png", "PNG (*.png);;JPEG (*.jpg)")
        if not path:
            return
        hi = QImage(2160, 2700, QImage.Format.Format_ARGB32_Premultiplied)
        hi.fill(QColor(self.tokens["window"]))
        painter = QPainter(hi)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._render_share_card(painter, 2160, 2700)
        painter.end()
        out = hi.scaled(1080, 1350, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        out.save(path)
