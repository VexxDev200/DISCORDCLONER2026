#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub Releases — URL манифеста и zip."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

ROOT = os.path.dirname(os.path.abspath(__file__))
UPDATES_DIR = os.path.join(ROOT, "updates")
TARGET_FILE = os.path.join(UPDATES_DIR, "github_target.json")
PUBLISH_CFG = os.path.join(ROOT, "update_publish.json")
PUBLISH_EXAMPLE = os.path.join(ROOT, "update_publish.example.json")


def load_publish_config() -> Dict[str, Any]:
    path = PUBLISH_CFG if os.path.isfile(PUBLISH_CFG) else PUBLISH_EXAMPLE
    if not os.path.isfile(path):
        raise FileNotFoundError(
            "Создай update_publish.json из update_publish.example.json (github_repo)."
        )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    repo = (data.get("github_repo") or "").strip()
    if "/" not in repo:
        raise ValueError("github_repo должен быть owner/repo")
    return data


def release_tag(version: str, prefix: str = "v") -> str:
    v = version.strip()
    if prefix and not v.startswith(prefix):
        return f"{prefix}{v}"
    return v


def release_asset_url(repo: str, tag: str, filename: str) -> str:
    return f"https://github.com/{repo}/releases/download/{tag}/{filename}"


def raw_manifest_url(repo: str, branch: str = "main") -> str:
    return f"https://raw.githubusercontent.com/{repo}/{branch}/updates/manifest.json"


def write_github_target(repo: str, branch: str = "main", tag_prefix: str = "v") -> None:
    os.makedirs(UPDATES_DIR, exist_ok=True)
    data = {"github_repo": repo, "branch": branch, "tag_prefix": tag_prefix}
    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def read_github_target(app_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    base = app_dir or ROOT
    for rel in (os.path.join("updates", "github_target.json"),):
        path = os.path.join(base, rel)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
    return None


def app_dir_for_updates() -> str:
    try:
        import app_paths

        return app_paths.app_dir()
    except ImportError:
        return ROOT


def resolve_manifest_url(cfg: Dict[str, Any]) -> str:
    url = (cfg.get("manifest_url") or "").strip()
    if url:
        return url
    tgt = read_github_target(app_dir_for_updates())
    if tgt and tgt.get("github_repo"):
        return raw_manifest_url(
            tgt["github_repo"],
            tgt.get("branch") or "main",
        )
    return ""


def write_repo_manifest(manifest: Dict[str, Any]) -> str:
    os.makedirs(UPDATES_DIR, exist_ok=True)
    path = os.path.join(UPDATES_DIR, "manifest.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path
