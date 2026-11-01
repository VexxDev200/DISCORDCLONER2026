#!/usr/bin/env python3
"""Sync Discord secrets to Worker + verify signed state."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import bot_config
import bot_oauth

ROOT = Path(__file__).resolve().parent
WORKER = ROOT / "oauth_worker"


def put_secret(name: str, value: str) -> None:
    proc = subprocess.run(
        ["npx", "wrangler", "secret", "put", name],
        cwd=str(WORKER),
        input=(value or "") + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout)
        raise RuntimeError(f"secret {name} failed")


def main() -> int:
    cfg = bot_config.load_bot_config()
    cid = str(cfg.get("client_id") or "").strip()
    sec = str(cfg.get("client_secret") or "").strip()
    red = str(cfg.get("redirect_uri") or "").strip()
    if not cid or not sec or not red:
        print("Need bot.client_id, client_secret, redirect_uri in config (merge with defaults).")
        return 1

    state = bot_oauth.create_signed_state(cfg, "123456789")
    print(f"Signed state sample OK (len={len(state)})")

    print("Uploading Worker secrets...")
    put_secret("DISCORD_CLIENT_ID", cid)
    put_secret("DISCORD_CLIENT_SECRET", sec)
    put_secret("REDIRECT_URI", red)
    print("Done. client_secret length on worker:", len(sec))
    print("Restart bot and Authorize again (new link).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
