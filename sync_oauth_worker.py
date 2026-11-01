#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
После wrangler deploy: взять реальный URL (*.account.workers.dev),
обновить config.json и (опционально) секрет REDIRECT_URI.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import bot_config

ROOT = Path(__file__).resolve().parent
WORKER_DIR = ROOT / "oauth_worker"
CONFIG_PATH = ROOT / "config.json"

# https://name.subdomain.workers.dev — не путать с name.workers.dev (не существует)
WORKERS_URL_RE = re.compile(
    r"https://[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z0-9][a-zA-Z0-9.-]*\.workers\.dev"
)


def _parse_workers_url(text: str) -> str | None:
    for m in WORKERS_URL_RE.finditer(text):
        url = m.group(0).rstrip("/")
        # preview URLs иногда длиннее — берём строку из вывода deploy (обычно одна)
        if url.count(".") >= 2:
            return url
    return None


def deploy_and_get_url() -> str:
    proc = subprocess.run(
        ["npx", "wrangler", "deploy"],
        cwd=str(WORKER_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0:
        print(out)
        raise RuntimeError(f"wrangler deploy failed (code {proc.returncode})")
    url = _parse_workers_url(out)
    if not url:
        print(out)
        raise RuntimeError("Не нашёл https://....workers.dev в выводе deploy")
    return url


def patch_config(redirect_uri: str) -> None:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = {}
    if "bot" not in data or not isinstance(data["bot"], dict):
        data["bot"] = {}
    data["bot"]["redirect_uri"] = redirect_uri
    data["bot"]["oauth_mode"] = "worker"
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def put_redirect_secret(redirect_uri: str) -> None:
    proc = subprocess.run(
        ["npx", "wrangler", "secret", "put", "REDIRECT_URI"],
        cwd=str(WORKER_DIR),
        input=redirect_uri + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        print("WARN: REDIRECT_URI secret failed")


def sync_discord_secrets(cfg: dict) -> None:
    """Worker secrets must match bot_config (signed OAuth state)."""
    for name, key in (
        ("DISCORD_CLIENT_ID", "client_id"),
        ("DISCORD_CLIENT_SECRET", "client_secret"),
        ("REDIRECT_URI", "redirect_uri"),
    ):
        val = str(cfg.get(key) or "").strip()
        proc = subprocess.run(
            ["npx", "wrangler", "secret", "put", name],
            cwd=str(WORKER_DIR),
            input=val + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"secret {name}: {(proc.stderr or proc.stdout)[:200]}")


def main() -> int:
    base = sys.argv[1].strip().rstrip("/") if len(sys.argv) > 1 else ""
    if base.startswith("http"):
        workers_base = base.split("/oauth/callback")[0].rstrip("/")
    elif base:
        workers_base = f"https://{base}" if "://" not in base else base
    else:
        print("Deploy worker...")
        workers_base = deploy_and_get_url()

    redirect_uri = f"{workers_base}/oauth/callback"
    cfg = {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data.get("bot"), dict):
            cfg = bot_config.load_bot_config()
    except (OSError, json.JSONDecodeError):
        cfg = bot_config.load_bot_config()
    cfg["redirect_uri"] = redirect_uri
    patch_config(redirect_uri)
    sync_discord_secrets(cfg)

    print("")
    print("OK")
    print(f"  Worker:  {workers_base}")
    print(f"  Redirect: {redirect_uri}")
    print("")
    print("Discord Portal -> OAuth2 -> Redirects -> add EXACTLY:")
    print(f"  {redirect_uri}")
    print("")
    print("Restart: python discord_bot.py")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(f"ERROR: {e}")
        raise SystemExit(1)
