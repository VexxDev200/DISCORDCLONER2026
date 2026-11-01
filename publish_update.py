#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка zip + manifest → commit → push → GitHub Release.

Перед первым запуском:
  1. copy update_publish.example.json → update_publish.json (укажи github_repo)
  2. git init && git remote add origin https://github.com/USER/REPO.git
  3. gh auth login
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

import github_update
import pack_updates
import vexx_version

ROOT = os.path.dirname(os.path.abspath(__file__))


def _run(cmd: list[str], cwd: str = ROOT) -> None:
    print("+", " ".join(cmd))
    subprocess.check_call(cmd, cwd=cwd)


def _git(*args: str) -> None:
    _run(["git", *args])


def bump_version(kind: str = "patch") -> str:
    parts = [int(x) for x in re.findall(r"\d+", vexx_version.__version__)]
    while len(parts) < 4:
        parts.append(0)
    if kind == "patch":
        parts[-1] += 1
    else:
        parts[-1] += 1
    new_v = ".".join(str(p) for p in parts)
    path = os.path.join(ROOT, "vexx_version.py")
    text = open(path, "r", encoding="utf-8").read()
    text = re.sub(
        r'(__version__\s*=\s*")[^"]+(")',
        rf"\g<1>{new_v}\g<2>",
        text,
        count=1,
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    import importlib

    importlib.reload(vexx_version)
    print(f"version → {new_v}")
    return new_v


def build_manifest_for_github(cfg: dict) -> tuple:
    repo = cfg["github_repo"]
    branch = cfg.get("branch") or "main"
    prefix = cfg.get("tag_prefix") or "v"
    ver = vexx_version.__version__
    tag = github_update.release_tag(ver, prefix)

    from datetime import datetime, timezone

    released = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    products = {}
    assets: list = []

    for key, flist in (
        ("cloner", pack_updates.CLONER_FILES),
        ("bot", pack_updates.BOT_FILES),
        ("ascii", pack_updates.ASCII_FILES),
    ):
        zpath, digest = pack_updates._zip_product(key, flist)
        fname = os.path.basename(zpath)
        assets.append(zpath)
        products[key] = {
            "version": ver,
            "zip": github_update.release_asset_url(repo, tag, fname),
            "sha256": digest,
        }
        print(f"{key}: {zpath}")

    manifest = {
        "schema": 1,
        "channel": "stable",
        "released": released,
        "github_repo": repo,
        "github_tag": tag,
        "products": products,
    }
    github_update.write_repo_manifest(manifest)

    bundle_files = sorted(
        set(pack_updates.CLONER_FILES + pack_updates.BOT_FILES + pack_updates.ASCII_FILES)
    )
    bpath, bsha = pack_updates._zip_product("bundle", bundle_files)
    bfname = os.path.basename(bpath)
    assets.append(bpath)
    products["bundle"] = {
        "version": ver,
        "zip": github_update.release_asset_url(repo, tag, bfname),
        "sha256": bsha,
    }
    github_update.write_repo_manifest(manifest)

    exe = os.path.join(ROOT, "dist", "VexxCloner_release", "VexxCloner.exe")
    if os.path.isfile(exe):
        ename = "VexxCloner.exe"
        assets.append(exe)
        products["cloner"]["exe"] = {
            "url": github_update.release_asset_url(repo, tag, ename),
            "sha256": pack_updates._sha256(exe),
        }
        github_update.write_repo_manifest(manifest)

    return manifest, assets, tag


def sync_client_config(manifest_url: str) -> None:
    path = os.path.join(ROOT, "update_config.json")
    cfg = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    cfg["manifest_url"] = manifest_url
    cfg.setdefault("auto_apply", True)
    cfg.setdefault("use_bundle", True)
    cfg.setdefault("auto_check_on_startup", True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"update_config.json → manifest_url set")


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish Vexx update to GitHub")
    ap.add_argument("--bump", action="store_true", help="увеличить patch в vexx_version.py")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--no-release", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(os.path.join(ROOT, ".git")):
        print("ERROR: нет .git — git init && git remote add origin ...")
        return 1

    try:
        cfg = github_update.load_publish_config()
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        return 1

    if args.bump:
        bump_version()
        import importlib

        importlib.reload(vexx_version)

    repo = cfg["github_repo"]
    branch = cfg.get("branch") or "main"
    prefix = cfg.get("tag_prefix") or "v"

    github_update.write_github_target(repo, branch, prefix)
    manifest, assets, tag = build_manifest_for_github(cfg)
    mpath = github_update.write_repo_manifest(manifest)
    print(f"manifest: {mpath}")

    murl = github_update.raw_manifest_url(repo, branch)
    sync_client_config(murl)

    dist_manifest = os.path.join(ROOT, "dist", "updates", "manifest.json")
    os.makedirs(os.path.dirname(dist_manifest), exist_ok=True)
    with open(dist_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    msg = (cfg.get("commit_message") or "release {version}").format(
        version=vexx_version.__version__
    )
    _git("add", "-A")
    try:
        _git("commit", "-m", msg)
    except subprocess.CalledProcessError:
        print("(nothing to commit or commit failed)")

    if cfg.get("push", True) and not args.no_push:
        try:
            _git("tag", "-f", tag)
        except subprocess.CalledProcessError:
            pass
        _git("push", "origin", branch)
        try:
            _git("push", "origin", tag, "--force")
        except subprocess.CalledProcessError as e:
            print(f"WARN: tag push: {e}")

    if cfg.get("create_release", True) and not args.no_release:
        import shutil

        if not shutil.which("gh"):
            print("WARN: gh CLI not found — создай Release вручную и залей zip из dist/updates/")
        else:
            files = [a for a in assets if os.path.isfile(a)]
            cmd = [
                "gh",
                "release",
                "create",
                tag,
                *files,
                "--repo",
                repo,
                "--title",
                f"Vexx {vexx_version.__version__}",
                "--notes",
                f"Auto-published {vexx_version.__version__}",
            ]
            try:
                _run(cmd)
            except subprocess.CalledProcessError:
                print("WARN: gh release failed (tag exists?) — проверь GitHub Releases")

    print("\nDone.")
    print(f"Clients manifest: {murl}")
    print("Users with auto_apply=true will download bundle on next start.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
