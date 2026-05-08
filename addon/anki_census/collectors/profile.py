from ..storage import load_config

def collect_profile():
    cfg = load_config()
    return {
        "values": cfg.get("profile", {}),
        "updated_at": cfg.get("profile_updated_at", {}),
    }
