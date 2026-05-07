def bucket_number(n, buckets):
    try:
        n = int(n or 0)
    except Exception:
        return "unknown"
    for upper, label in buckets:
        if n <= upper:
            return label
    return buckets[-1][1]

def bucket_percent(p):
    if p is None:
        return "unknown"
    try:
        p = float(p)
    except Exception:
        return "unknown"
    if p <= 0: return "0%"
    if p <= 1: return ">0–1%"
    if p <= 10: return "1–10%"
    if p <= 25: return "11–25%"
    if p <= 50: return "26–50%"
    if p <= 75: return "51–75%"
    return "76–100%"

def bucket_retention(p):
    if p is None: return "unknown"
    p = float(p)
    if p < 60: return "<60%"
    if p < 70: return "60–70%"
    if p < 80: return "70–80%"
    if p < 85: return "80–85%"
    if p < 90: return "85–90%"
    if p < 95: return "90–95%"
    return "95%+"

def bucket_duration_minutes(minutes):
    if minutes is None: return "unknown"
    h = float(minutes) / 60
    if h <= 0: return "0h"
    if h < 1: return "<1h"
    if h <= 5: return "1–5h"
    if h <= 10: return "5–10h"
    if h <= 30: return "10–30h"
    if h <= 60: return "30–60h"
    return "60h+"

def bucket_answer_seconds(sec):
    if sec is None: return "unknown"
    sec = float(sec)
    if sec < 3: return "<3s"
    if sec <= 5: return "3–5s"
    if sec <= 10: return "5–10s"
    if sec <= 20: return "10–20s"
    if sec <= 40: return "20–40s"
    return "40s+"

COUNT_BUCKETS_SMALL = [(0,"0"),(1,"1"),(5,"2–5"),(10,"6–10"),(25,"11–25"),(50,"26–50"),(10**12,"51+")]
COUNT_BUCKETS_MED = [(0,"0"),(50,"1–50"),(100,"51–100"),(500,"101–500"),(1000,"501–1.000"),(5000,"1.001–5.000"),(10**12,"5.001+")]
CARD_BUCKETS = [(500,"0–500"),(1000,"501–1.000"),(5000,"1.001–5.000"),(10000,"5.001–10.000"),(50000,"10.001–50.000"),(100000,"50.001–100.000"),(10**12,"100.001+")]
NOTE_BUCKETS = [(100,"0–100"),(500,"101–500"),(1000,"501–1.000"),(5000,"1.001–5.000"),(10000,"5.001–10.000"),(50000,"10.001–50.000"),(10**12,"50.001+")]
REVIEWS_BUCKETS = [(0,"0"),(100,"1–100"),(500,"101–500"),(1000,"501–1.000"),(3000,"1.001–3.000"),(10000,"3.001–10.000"),(10**12,"10.001+")]
STUDY_DAYS_30 = [(0,"0"),(3,"1–3"),(7,"4–7"),(14,"8–14"),(20,"15–20"),(30,"21–30"),(10**12,"31+")]
STUDY_DAYS_180 = [(0,"0"),(15,"1–15"),(45,"16–45"),(90,"46–90"),(135,"91–135"),(180,"136–180"),(10**12,"181+")]
MEDIA_SIZE_MB = [(0,"0"),(100,"<100 MB"),(500,"100–500 MB"),(1024,"500 MB–1 GB"),(5120,"1–5 GB"),(20480,"5–20 GB"),(10**12,"20 GB+")]
