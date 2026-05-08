from datetime import datetime, timedelta, time
from aqt import mw
from ..buckets import bucket_number, bucket_duration_minutes, bucket_answer_seconds, bucket_retention, bucket_percent, REVIEWS_BUCKETS


def _local_tz():
    return datetime.now().astimezone().tzinfo


def _anki_rollover_hour():
    """Best-effort approximation of Anki's next-day cutoff hour."""
    try:
        cfg = mw.col.get_config("rollover")
        if cfg is not None:
            return int(cfg)
    except Exception:
        pass
    try:
        return int(mw.col.decks.config_dict_for_deck_id(1).get("rollover", 4))
    except Exception:
        return 4


def _anki_day_for_timestamp_ms(ts_ms: int):
    tz = _local_tz()
    dt = datetime.fromtimestamp(int(ts_ms) / 1000, tz=tz)
    rollover = _anki_rollover_hour()
    if dt.hour < rollover:
        dt = dt - timedelta(days=1)
    return dt.date()


def _start_for_anki_days(days: int):
    """Start timestamp for today + previous (days-1) Anki days."""
    tz = _local_tz()
    now = datetime.now(tz)
    rollover = _anki_rollover_hour()
    today = now.date()
    if now.hour < rollover:
        today = today - timedelta(days=1)
    start_day = today - timedelta(days=max(0, days - 1))
    start = datetime.combine(start_day, time(hour=rollover), tzinfo=tz)
    return int(start.timestamp() * 1000), today


def _rows_since_anki_days(days: int):
    cutoff, _today = _start_for_anki_days(days)
    try:
        return mw.col.db.all("select id, ease, time, type from revlog where id >= ?", cutoff)
    except Exception:
        return []


def _summarize_rows(rows, window_days: int):
    total = len(rows)
    if not total:
        return {
            "reviews_bucket": "0",
            "study_days_bucket": f"0 de {window_days}",
            "study_time_bucket": "0h",
            "avg_answer_time_bucket": "unknown",
            "retention_bucket": "unknown",
            "again_rate_bucket": "unknown",
            "hard_rate_bucket": "unknown",
            "good_rate_bucket": "unknown",
            "easy_rate_bucket": "unknown",
        }

    days_set = set(_anki_day_for_timestamp_ms(r[0]).isoformat() for r in rows)
    total_time_ms = sum(min(max(int(r[2] or 0), 0), 60000) for r in rows)
    avg_sec = total_time_ms / 1000 / total if total else None
    ease_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for r in rows:
        ease = int(r[1] or 0)
        ease_counts[ease] = ease_counts.get(ease, 0) + 1
    retention = 100 * (total - ease_counts.get(1, 0)) / total
    studied_days = len(days_set)

    return {
        "reviews_bucket": bucket_number(total, REVIEWS_BUCKETS),
        "study_days_bucket": f"{studied_days} de {window_days}",
        "study_time_bucket": bucket_duration_minutes(total_time_ms / 1000 / 60),
        "avg_answer_time_bucket": bucket_answer_seconds(avg_sec),
        "retention_bucket": bucket_retention(retention),
        "again_rate_bucket": bucket_percent(100 * ease_counts.get(1, 0) / total),
        "hard_rate_bucket": bucket_percent(100 * ease_counts.get(2, 0) / total),
        "good_rate_bucket": bucket_percent(100 * ease_counts.get(3, 0) / total),
        "easy_rate_bucket": bucket_percent(100 * ease_counts.get(4, 0) / total),
    }


def _summary(days):
    rows = _rows_since_anki_days(days)
    return _summarize_rows(rows, days)


def _month_label(date_obj):
    months = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    return f"{months[date_obj.month - 1]}/{date_obj.year}"


def _semester_months(month_count=6):
    tz = _local_tz()
    now = datetime.now(tz)
    first_this_month = now.date().replace(day=1)
    # Build last N calendar months, including current.
    months = []
    y, m = first_this_month.year, first_this_month.month
    for i in range(month_count - 1, -1, -1):
        mm = m - i
        yy = y
        while mm <= 0:
            mm += 12
            yy -= 1
        start = datetime(yy, mm, 1, _anki_rollover_hour(), tzinfo=tz)
        if mm == 12:
            end = datetime(yy + 1, 1, 1, _anki_rollover_hour(), tzinfo=tz)
        else:
            end = datetime(yy, mm + 1, 1, _anki_rollover_hour(), tzinfo=tz)
        months.append((start, end))

    start_ms = int(months[0][0].timestamp() * 1000)
    try:
        rows = mw.col.db.all("select id, ease, time, type from revlog where id >= ?", start_ms)
    except Exception:
        rows = []

    result = []
    for start, end in months:
        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        subset = [r for r in rows if start_ms <= int(r[0]) < end_ms]
        summary = _summarize_rows(subset, max(1, (end.date() - start.date()).days))
        total = len(subset)
        days_set = set(_anki_day_for_timestamp_ms(r[0]).isoformat() for r in subset)
        total_time_ms = sum(min(max(int(r[2] or 0), 0), 60000) for r in subset)
        ease_counts = {1: 0, 2: 0, 3: 0, 4: 0}
        for r in subset:
            ease = int(r[1] or 0)
            ease_counts[ease] = ease_counts.get(ease, 0) + 1
        retention = None if not total else round(100 * (total - ease_counts.get(1, 0)) / total, 2)
        result.append({
            "month": start.strftime("%Y-%m"),
            "month_label": _month_label(start.date()),
            "reviews": total,
            "reviews_bucket": summary["reviews_bucket"],
            "study_days": len(days_set),
            "study_time_bucket": summary["study_time_bucket"],
            "retention": retention,
            "retention_bucket": summary["retention_bucket"],
        })
    return result


def collect_activity():
    # Recent window follows Anki's native-feeling "today + previous 30 days".
    return {
        "last_30_days": _summary(31),
        "last_180_days": _summary(180),
        "semester_months": _semester_months(6),
    }
