from aqt import mw
from ..buckets import bucket_number, COUNT_BUCKETS_SMALL

def _bucket_retention_value(v):
    try:
        pct = float(v) * 100 if float(v) <= 1 else float(v)
    except Exception:
        return "unknown"
    if pct < 80: return "<80%"
    if pct < 85: return "80–85%"
    if pct < 90: return "85–90%"
    if pct < 95: return "90–95%"
    return "95%+"

def _first_number_bucket(n):
    try: n = int(n)
    except Exception: return "unknown"
    if n == 0: return "0"
    if n <= 10: return "1–10"
    if n <= 20: return "11–20"
    if n <= 50: return "21–50"
    if n <= 100: return "51–100"
    return "101+"

def _reviews_limit_bucket(n):
    try: n = int(n)
    except Exception: return "unknown"
    if n <= 0 or n >= 9999: return "sem limite"
    if n <= 100: return "1–100"
    if n <= 200: return "101–200"
    if n <= 500: return "201–500"
    if n <= 1000: return "501–1000"
    return "1001+"

def collect_scheduling():
    decks = []
    fsrs = False
    desired = None
    new_values = []
    rev_values = []
    preset_count = 0
    try:
        confs = mw.col.decks.all_config()
        preset_count = len(confs)
        for conf in confs:
            if conf.get("fsrs") or conf.get("fsrsWeights") or conf.get("fsrsWeights5"):
                fsrs = True
            if desired is None:
                desired = conf.get("desiredRetention") or conf.get("desired_retention")
            new_values.append(conf.get("new", {}).get("perDay", 0))
            rev_values.append(conf.get("rev", {}).get("perDay", 0))
    except Exception:
        try:
            conf = mw.col.decks.get_config(mw.col.decks.selected())
            fsrs = bool(conf.get("fsrs"))
            desired = conf.get("desiredRetention")
            new_values = [conf.get("new", {}).get("perDay", 0)]
            rev_values = [conf.get("rev", {}).get("perDay", 0)]
            preset_count = 1
        except Exception:
            pass
    return {
        "fsrs_enabled": bool(fsrs),
        "desired_retention_bucket": _bucket_retention_value(desired),
        "max_new_cards_per_day_bucket": _first_number_bucket(max(new_values) if new_values else 0),
        "max_reviews_per_day_bucket": _reviews_limit_bucket(max(rev_values) if rev_values else 0),
        "deck_preset_count_bucket": bucket_number(preset_count, COUNT_BUCKETS_SMALL),
    }
