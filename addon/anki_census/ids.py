"""Backward-compatible local identifier helper backed by shared global config."""

from .storage import load_config, save_config


def ensure_user_id() -> str:
    """Return the shared anonymous user id while keeping legacy `user_id` callers working."""
    cfg = load_config()
    user_id = cfg.get("user_id") or cfg.get("anonymous_user_id") or ""
    cfg["user_id"] = user_id
    save_config(cfg)
    return user_id
