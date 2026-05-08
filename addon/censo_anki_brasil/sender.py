import json
import urllib.request
import urllib.error
from .storage import load_config

CLIENT_NAME = "CensoAnkiBrasilAddon"


def _base_url():
    cfg = load_config()
    return (cfg.get("api_base_url") or "").rstrip("/")


def post_json(path: str, payload: dict, timeout=20) -> dict:
    base = _base_url()
    if not base:
        raise RuntimeError("URL da API não configurada")
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        base + path,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"{CLIENT_NAME}/{payload.get('addon_version','unknown')}",
            "X-Census-Client": "censo-anki-brasil-addon",
            "X-Census-Schema": payload.get("schema_version", ""),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Servidor retornou erro {e.code}: {body[:300]}")


def get_json(path: str, timeout=12) -> dict:
    base = _base_url()
    if not base:
        raise RuntimeError("URL da API não configurada")
    req = urllib.request.Request(
        base + path,
        headers={
            "Accept": "application/json",
            "User-Agent": f"{CLIENT_NAME}/results",
            "X-Census-Client": "censo-anki-brasil-addon",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Servidor retornou erro {e.code}: {body[:300]}")


def submit_payload(payload: dict) -> dict:
    return post_json("/submit", payload)


def submit_debug_payload(payload: dict) -> dict:
    return post_json("/debug-submit", payload)


def fetch_public_results() -> dict:
    return get_json("/results")
