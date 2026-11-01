#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Обновить bot.redirect_uri в config.json после деплоя Worker."""

from __future__ import annotations

import json
import sys

from app_paths import data_path

WORKER_NAME = "vexx-cloner-oauth"


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: python patch_oauth_redirect.py <worker-subdomain>")
        print(f"Example: python patch_oauth_redirect.py {WORKER_NAME}-yourname")
        return 1
    sub = sys.argv[1].strip().rstrip("/")
    redirect = f"https://{sub}.workers.dev/oauth/callback"
    path = data_path("config.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = {}
    if "bot" not in data or not isinstance(data["bot"], dict):
        data["bot"] = {}
    data["bot"]["redirect_uri"] = redirect
    data["bot"]["oauth_mode"] = "worker"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("OK config.json:")
    print(f"  redirect_uri = {redirect}")
    print(f"  oauth_mode = worker")
    print("")
    print("Discord Developer Portal → OAuth2 → Redirects → добавь ТО ЖЕ:")
    print(f"  {redirect}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
