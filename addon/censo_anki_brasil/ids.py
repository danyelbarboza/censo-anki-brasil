import secrets
from .constants import USER_ID_ALPHABET, USER_ID_LENGTH
from .storage import load_config, save_config

def ensure_user_id() -> str:
    cfg = load_config()
    if cfg.get("user_id"):
        return cfg["user_id"]
    user_id = "".join(secrets.choice(USER_ID_ALPHABET) for _ in range(USER_ID_LENGTH))
    cfg["user_id"] = user_id
    save_config(cfg)
    return user_id
