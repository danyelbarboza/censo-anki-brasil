from aqt import mw
from ..buckets import bucket_number, bucket_percent, COUNT_BUCKETS_SMALL


def _bucket_retention_value(v):
    try:
        pct = float(v) * 100 if float(v) <= 1 else float(v)
    except Exception:
        return "unknown"
    if pct < 80:
        return "<80%"
    if pct < 85:
        return "80–85%"
    if pct < 90:
        return "85–90%"
    if pct < 95:
        return "90–95%"
    return "95%+"


def _first_number_bucket(n):
    try:
        n = int(n)
    except Exception:
        return "unknown"
    if n == 0:
        return "0"
    if n <= 10:
        return "1–10"
    if n <= 20:
        return "11–20"
    if n <= 50:
        return "21–50"
    if n <= 100:
        return "51–100"
    return "101+"


def _reviews_limit_bucket(n):
    try:
        n = int(n)
    except Exception:
        return "unknown"
    if n <= 0 or n >= 9999:
        return "sem limite"
    if n <= 100:
        return "1–100"
    if n <= 200:
        return "101–200"
    if n <= 500:
        return "201–500"
    if n <= 1000:
        return "501–1000"
    return "1001+"


def _as_bool_marker(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "yes", "y", "1", "enabled", "on"}:
            return True
        if v in {"false", "no", "n", "0", "disabled", "off"}:
            return False
    return None


def _config_value(key):
    try:
        return mw.col.get_config(key)
    except Exception:
        return None


def _global_fsrs_enabled():
    for key in ("fsrs", "fsrsEnabled", "fsrs_enabled", "enable_fsrs", "enableFsrs"):
        marker = _as_bool_marker(_config_value(key))
        if marker is not None:
            return marker
    try:
        sched_ver = mw.col.get_config("schedVer")
        # In newer Anki versions, FSRS is only available with the modern scheduler.
        # This is not enough to prove FSRS is enabled, so do not infer True from it.
        _ = sched_ver
    except Exception:
        pass
    return None


def _preset_fsrs_enabled(conf):
    keys = (
        "fsrs", "fsrsEnabled", "fsrs_enabled", "enable_fsrs", "enableFsrs",
        "fsrsActivated", "fsrs_activated", "use_fsrs", "useFsrs"
    )
    for key in keys:
        if key in conf:
            marker = _as_bool_marker(conf.get(key))
            if marker is not None:
                return marker
    # Some Anki builds have nested deck-option structures.
    for section in ("scheduler", "scheduling", "rev", "new"):
        nested = conf.get(section)
        if isinstance(nested, dict):
            for key in keys:
                if key in nested:
                    marker = _as_bool_marker(nested.get(key))
                    if marker is not None:
                        return marker
    return None


def collect_scheduling():
    desired = None
    new_values = []
    rev_values = []
    preset_count = 0
    fsrs_markers = []
    global_fsrs = _global_fsrs_enabled()

    try:
        confs = mw.col.decks.all_config()
        preset_count = len(confs)
        for conf in confs:
            marker = _preset_fsrs_enabled(conf)
            if marker is not None:
                fsrs_markers.append(marker)
            if desired is None:
                desired = conf.get("desiredRetention") or conf.get("desired_retention")
            new_values.append(conf.get("new", {}).get("perDay", 0))
            rev_values.append(conf.get("rev", {}).get("perDay", 0))
    except Exception:
        try:
            conf = mw.col.decks.get_config(mw.col.decks.selected())
            preset_count = 1
            marker = _preset_fsrs_enabled(conf)
            if marker is not None:
                fsrs_markers.append(marker)
            desired = conf.get("desiredRetention") or conf.get("desired_retention")
            new_values = [conf.get("new", {}).get("perDay", 0)]
            rev_values = [conf.get("rev", {}).get("perDay", 0)]
        except Exception:
            pass

    if fsrs_markers:
        enabled_count = sum(1 for x in fsrs_markers if x)
        fsrs_pct = 100 * enabled_count / len(fsrs_markers)
        fsrs_enabled = enabled_count > 0
    elif global_fsrs is not None and preset_count:
        enabled_count = preset_count if global_fsrs else 0
        fsrs_pct = 100 if global_fsrs else 0
        fsrs_enabled = bool(global_fsrs)
    else:
        enabled_count = 0
        fsrs_pct = None
        fsrs_enabled = False

    return {
        "fsrs_enabled": bool(fsrs_enabled),
        "fsrs_enabled_preset_ratio_bucket": bucket_percent(fsrs_pct),
        "fsrs_enabled_preset_count_bucket": bucket_number(enabled_count, COUNT_BUCKETS_SMALL),
        "fsrs_preset_total_count_bucket": bucket_number(preset_count, COUNT_BUCKETS_SMALL),
        "desired_retention_bucket": _bucket_retention_value(desired),
        "max_new_cards_per_day_bucket": _first_number_bucket(max(new_values) if new_values else 0),
        "max_reviews_per_day_bucket": _reviews_limit_bucket(max(rev_values) if rev_values else 0),
        "deck_preset_count_bucket": bucket_number(preset_count, COUNT_BUCKETS_SMALL),
    }
