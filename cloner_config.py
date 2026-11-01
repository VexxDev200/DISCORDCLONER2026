#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load config.json next to exe/script and merge into runtime CONFIG."""

import json
import os
from typing import Any, Dict, MutableMapping

from app_paths import data_path

DEFAULT_PATH = data_path("config.json")


def apply_file_config(config: MutableMapping[str, Any], path: str | None = None) -> bool:
    p = path or DEFAULT_PATH
    if not os.path.isfile(p):
        return False
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    for key, value in data.items():
        config[key] = value
    return True


def save_default_config(path: str | None = None) -> str:
    """Write example config if missing (for first run)."""
    p = path or DEFAULT_PATH
    if os.path.isfile(p):
        return p
    sample = {
        "dry_run": False,
        "resume": True,
        "console_quiet": False,
        "delete_orphans": False,
        "parallel_cdn_workers": 4,
        "copy_settings": True,
        "copy_roles": True,
        "copy_channels": True,
        "copy_emojis": True,
        "copy_stickers": True,
        "copy_webhooks": True,
        "copy_banner": True,
        "copy_icon": True,
        "copy_members": True,
        "copy_onboarding": True,
        "copy_automod": True,
        "copy_scheduled_events": True,
        "copy_messages": False,
        "role_boost_fallback": True,
        "preflight": True,
        "interactive_modules": True,
        "turbo_mode": True,
        "mapping_profile": "default",
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)
    return p
