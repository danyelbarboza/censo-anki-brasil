import json, os
from aqt import mw
from ..constants import ADDON_NAME
from ..buckets import bucket_number, COUNT_BUCKETS_SMALL

def _addons_dir():
    for attr in ("addonsFolder",):
        try:
            p = getattr(mw.addonManager, attr)()
            if p and os.path.isdir(p): return p
        except Exception: pass
    try:
        p = mw.pm.addonFolder()
        if p and os.path.isdir(p): return p
    except Exception: pass
    return None

def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}

def _disabled_ids():
    try:
        return set(mw.addonManager.getConfig("_disabled") or [])
    except Exception:
        pass
    try:
        return set(mw.addonManager.disabledAddons())
    except Exception:
        return set()

def collect_addons():
    base = _addons_dir()
    items = []
    disabled = _disabled_ids()
    if base:
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if not os.path.isdir(path): continue
            if name.startswith("__") or name == "censo_anki_brasil": continue
            manifest = _read_json(os.path.join(path, "manifest.json"))
            meta = _read_json(os.path.join(path, "meta.json"))
            display = manifest.get("name") or meta.get("name") or name
            source = "ankiweb" if name.isdigit() else "local"
            enabled = name not in disabled
            items.append({"id": name if name.isdigit() else None, "folder": name, "name": str(display), "enabled": bool(enabled), "source": source})
    return {
        "addon_count_bucket": bucket_number(len(items), COUNT_BUCKETS_SMALL),
        "enabled_addon_count_bucket": bucket_number(sum(1 for x in items if x["enabled"]), COUNT_BUCKETS_SMALL),
        "disabled_addon_count_bucket": bucket_number(sum(1 for x in items if not x["enabled"]), COUNT_BUCKETS_SMALL),
        "local_addon_count_bucket": bucket_number(sum(1 for x in items if x["source"] == "local"), COUNT_BUCKETS_SMALL),
        "items": items,
    }
