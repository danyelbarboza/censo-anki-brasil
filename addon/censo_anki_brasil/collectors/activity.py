from datetime import datetime, timezone, timedelta
from aqt import mw
from ..buckets import bucket_number, bucket_duration_minutes, bucket_answer_seconds, bucket_retention, bucket_percent, REVIEWS_BUCKETS, STUDY_DAYS_30, STUDY_DAYS_180

DAY_MS = 24 * 60 * 60 * 1000

def _rows_since(days):
    cutoff = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    try:
        return mw.col.db.all("select id, ease, time, type from revlog where id >= ?", cutoff)
    except Exception:
        return []

def _summary(days):
    rows = _rows_since(days)
    total = len(rows)
    if not total:
        return {"reviews_bucket": "0", "study_days_bucket": "0", "study_time_bucket": "0h", "avg_answer_time_bucket": "unknown", "retention_bucket": "unknown", "again_rate_bucket": "unknown", "hard_rate_bucket": "unknown", "good_rate_bucket": "unknown", "easy_rate_bucket": "unknown"}
    days_set = set(datetime.fromtimestamp(int(r[0])/1000, tz=timezone.utc).date().isoformat() for r in rows)
    total_time_ms = sum(min(max(int(r[2] or 0), 0), 60000) for r in rows)  # cap at 60s/card for sane aggregate
    avg_sec = total_time_ms / 1000 / total if total else None
    ease_counts = {1:0,2:0,3:0,4:0}
    for r in rows:
        ease_counts[int(r[1] or 0)] = ease_counts.get(int(r[1] or 0), 0) + 1
    retention = 100 * (total - ease_counts.get(1,0)) / total
    day_bucket = STUDY_DAYS_30 if days <= 30 else STUDY_DAYS_180
    return {
        "reviews_bucket": bucket_number(total, REVIEWS_BUCKETS),
        "study_days_bucket": bucket_number(len(days_set), day_bucket),
        "study_time_bucket": bucket_duration_minutes(total_time_ms / 1000 / 60),
        "avg_answer_time_bucket": bucket_answer_seconds(avg_sec),
        "retention_bucket": bucket_retention(retention),
        "again_rate_bucket": bucket_percent(100 * ease_counts.get(1,0) / total),
        "hard_rate_bucket": bucket_percent(100 * ease_counts.get(2,0) / total),
        "good_rate_bucket": bucket_percent(100 * ease_counts.get(3,0) / total),
        "easy_rate_bucket": bucket_percent(100 * ease_counts.get(4,0) / total),
    }

def collect_activity():
    return {"last_30_days": _summary(30), "last_180_days": _summary(180)}
