#!/usr/bin/env python3
import argparse, json, os, shutil, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADDON = ROOT / "addon"
DIST = ROOT / "dist"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--api-url", required=True, help="URL pública do Cloudflare Worker, sem barra final")
    p.add_argument("--version", default="0.1.0")
    args = p.parse_args()
    DIST.mkdir(exist_ok=True)
    tmp = DIST / "build"
    if tmp.exists(): shutil.rmtree(tmp)
    shutil.copytree(ADDON, tmp)
    cfg_path = tmp / "config.json"
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    cfg["api_base_url"] = args.api_url.rstrip("/")
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    out = DIST / f"censo-anki-brasil-{args.version}.ankiaddon"
    if out.exists(): out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in tmp.rglob("*"):
            if path.is_file():
                z.write(path, path.relative_to(tmp).as_posix())
    shutil.rmtree(tmp)
    print(out)

if __name__ == "__main__":
    main()
