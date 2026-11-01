#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автообновление Vexx Cloner / Bot / ASCII.

Режимы:
  1) Git — если в папке есть .git и git_pull_if_repo=true
  2) manifest.json + zip по HTTPS (update_config.json → manifest_url)
  3) Для frozen GodCloner.exe — url в manifest.products.cloner.exe
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import app_paths
import vexx_version

try:
    import github_update
except ImportError:
    github_update = None

CONFIG_NAME = "update_config.json"
STATE_NAME = "update_state.json"
USER_AGENT = f"VexxUpdater/{vexx_version.__version__}"

PROTECTED_FILES = frozenset(
    {
        "config.json",
        "bot_config.json",
        "databaseneon.txt",
        "update_config.json",
        "update_state.json",
        "db_embed.py",
        ".env",
    }
)
PROTECTED_PREFIXES = (
    "oauth_worker" + os.sep,
    "dist" + os.sep,
    ".git" + os.sep,
    "node_modules" + os.sep,
)


@dataclass
class ProductStatus:
    product: str
    local_version: str
    remote_version: str
    update_available: bool
    message: str = ""


@dataclass
class UpdateReport:
    ok: bool
    checks: List[ProductStatus] = field(default_factory=list)
    applied: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    used_git: bool = False


def _config_path() -> str:
    return app_paths.data_path(CONFIG_NAME)


def _state_path() -> str:
    return app_paths.data_path(STATE_NAME)


def default_config() -> Dict[str, Any]:
    return {
        "manifest_url": "",
        "channel": "stable",
        "auto_check_on_startup": True,
        "auto_apply": True,
        "use_bundle": True,
        "check_interval_hours": 6,
        "products": {"cloner": True, "bot": False, "ascii": True},
        "git_pull_if_repo": True,
    }


def load_config() -> Dict[str, Any]:
    path = _config_path()
    cfg = default_config()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                cfg.update(data)
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def _manifest_url(cfg: Dict[str, Any]) -> str:
    if github_update:
        return github_update.resolve_manifest_url(cfg)
    return (cfg.get("manifest_url") or "").strip()


def save_config(cfg: Dict[str, Any]) -> None:
    with open(_config_path(), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_state() -> Dict[str, Any]:
    path = _state_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: Dict[str, Any]) -> None:
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")


def parse_version(s: str) -> Tuple[int, ...]:
    if not s:
        return (0,)
    parts = re.findall(r"\d+", str(s))
    return tuple(int(p) for p in parts) if parts else (0,)


def version_lt(a: str, b: str) -> bool:
    return parse_version(a) < parse_version(b)


def local_version(_product: str) -> str:
    return vexx_version.__version__


def _http_get(url: str, timeout: float = 25.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_manifest(url: str) -> Dict[str, Any]:
    raw = _http_get(url.strip())
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("manifest must be a JSON object")
    return data


def _git_root() -> Optional[str]:
    root = app_paths.app_dir()
    if os.path.isdir(os.path.join(root, ".git")):
        return root
    return None


def git_update(root: Optional[str] = None) -> Tuple[bool, str]:
    root = root or _git_root()
    if not root:
        return False, "no git repo"
    try:
        subprocess.run(
            ["git", "fetch", "--quiet"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        st = subprocess.run(
            ["git", "status", "-sb"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        behind = "behind" in (st.stdout or "")
        if not behind:
            return True, "already up to date (git)"
        subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        return True, "git pull OK"
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e)).strip()
        return False, f"git failed: {err[:200]}"
    except FileNotFoundError:
        return False, "git not installed"
    except subprocess.TimeoutExpired:
        return False, "git timeout"


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _download(url: str, dest: str) -> None:
    data = _http_get(url, timeout=120)
    folder = os.path.dirname(dest)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)


def _is_protected(rel: str) -> bool:
    rel = rel.replace("/", os.sep).lstrip(os.sep)
    base = os.path.basename(rel)
    if base in PROTECTED_FILES:
        return True
    for pref in PROTECTED_PREFIXES:
        if rel.startswith(pref):
            return True
    return False


def _safe_extract_zip(zip_path: str, dest_root: str) -> List[str]:
    written: List[str] = []
    dest_root = os.path.abspath(dest_root)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("/", os.sep)
            if name.startswith(".." + os.sep) or ".." + os.sep in name:
                continue
            rel = name.lstrip(os.sep)
            if _is_protected(rel):
                continue
            out = os.path.join(dest_root, rel)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with zf.open(info) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            written.append(rel)
    return written


def apply_product_zip(
    product: str,
    meta: Dict[str, Any],
    dest_root: Optional[str] = None,
) -> Tuple[bool, str, List[str]]:
    url = (meta.get("zip") or "").strip()
    if not url:
        return False, "no zip url in manifest", []
    dest_root = dest_root or app_paths.app_dir()
    expect = (meta.get("sha256") or "").strip().lower()
    with tempfile.TemporaryDirectory(prefix="vexx-up-") as tmp:
        zpath = os.path.join(tmp, f"{product}.zip")
        _download(url, zpath)
        if expect and _sha256_file(zpath) != expect:
            return False, "sha256 mismatch", []
        files = _safe_extract_zip(zpath, dest_root)
    if not files:
        return False, "zip empty or all files protected", []
    return True, f"extracted {len(files)} files", files


def apply_cloner_exe(meta: Dict[str, Any]) -> Tuple[bool, str]:
    exe_meta = meta.get("exe") if isinstance(meta.get("exe"), dict) else {}
    url = (exe_meta.get("url") or meta.get("exe_url") or "").strip()
    if not url:
        return False, "no exe url in manifest"
    root = app_paths.app_dir()
    target = os.path.join(root, "VexxCloner.exe")
    new_path = target + ".new"
    _download(url, new_path)
    expect = (exe_meta.get("sha256") or "").strip().lower()
    if expect and _sha256_file(new_path) != expect:
        os.remove(new_path)
        return False, "exe sha256 mismatch"
    if os.path.isfile(target):
        bak = target + ".bak"
        try:
            if os.path.isfile(bak):
                os.remove(bak)
            os.replace(target, bak)
        except OSError:
            pass
    os.replace(new_path, target)
    legacy = os.path.join(root, "GodCloner.exe")
    if os.path.isfile(legacy) and legacy != target:
        try:
            os.remove(legacy)
        except OSError:
            pass
    return True, "VexxCloner.exe updated"


def check_updates(
    products: Optional[List[str]] = None,
    force: bool = False,
) -> UpdateReport:
    cfg = load_config()
    report = UpdateReport(ok=True)
    enabled = cfg.get("products") or {}
    want = products or [
        p
        for p in (
            vexx_version.PRODUCT_CLONER,
            vexx_version.PRODUCT_BOT,
            vexx_version.PRODUCT_ASCII,
        )
        if enabled.get(p, True)
    ]

    state = load_state()
    now = time.time()
    interval = float(cfg.get("check_interval_hours") or 6) * 3600
    last = float(state.get("last_check_ts") or 0)
    if not force and interval > 0 and (now - last) < interval:
        report.checks.append(
            ProductStatus(
                "all",
                vexx_version.__version__,
                vexx_version.__version__,
                False,
                "skipped (interval)",
            )
        )
        return report

    state["last_check_ts"] = now
    save_state(state)

    manifest_url = _manifest_url(cfg)
    manifest: Optional[Dict[str, Any]] = None
    if manifest_url:
        try:
            manifest = fetch_manifest(manifest_url)
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError) as e:
            report.errors.append(f"manifest: {e}")
            manifest = None

    prods = (manifest or {}).get("products") or {}
    if cfg.get("use_bundle") and manifest and isinstance(prods.get("bundle"), dict):
        bver = str(prods["bundle"].get("version") or "")
        local = local_version("bundle")
        if bver and version_lt(local, bver):
            report.checks.append(
                ProductStatus("bundle", local, bver, True, "github bundle")
            )
            return report

    for product in want:
        local = local_version(product)
        remote = local
        if manifest and product in prods and isinstance(prods[product], dict):
            remote = str(prods[product].get("version") or local)
        avail = version_lt(local, remote)
        msg = "up to date"
        if manifest is None and manifest_url:
            msg = "manifest unavailable"
        elif avail:
            msg = f"new {remote}"
        report.checks.append(
            ProductStatus(product, local, remote, avail, msg)
        )

    return report


def apply_updates(
    products: Optional[List[str]] = None,
    include_exe: bool = True,
) -> UpdateReport:
    cfg = load_config()
    report = check_updates(products=products, force=True)
    root = app_paths.app_dir()

    if cfg.get("git_pull_if_repo") and _git_root():
        ok, msg = git_update(root)
        report.used_git = ok
        if ok and "pull OK" in msg:
            report.applied.append(f"git: {msg}")
            return report
        if not ok and msg != "already up to date (git)":
            report.errors.append(msg)

    manifest_url = _manifest_url(cfg)
    if not manifest_url:
        if not report.applied:
            report.errors.append(
                "manifest: укажи manifest_url или положи updates/github_target.json"
            )
            report.ok = False
        return report

    try:
        manifest = fetch_manifest(manifest_url)
    except Exception as e:
        report.errors.append(str(e))
        report.ok = False
        return report

    prods = manifest.get("products") or {}
    if cfg.get("use_bundle") and isinstance(prods.get("bundle"), dict):
        b = prods["bundle"]
        bver = str(b.get("version") or "")
        if bver and version_lt(local_version("bundle"), bver):
            ok, msg, _ = apply_product_zip("bundle", b, root)
            if ok:
                report.applied.append(f"bundle: {msg}")
                report.checks.append(
                    ProductStatus("bundle", bver, bver, False, "installed")
                )
            else:
                report.errors.append(f"bundle: {msg}")
            state = load_state()
            state["last_apply_ts"] = time.time()
            save_state(state)
            return report

    want = [c.product for c in report.checks if c.update_available and c.product != "all"]
    if products:
        want = list(products)

    for product in want:
        meta = prods.get(product)
        if not isinstance(meta, dict):
            report.errors.append(f"{product}: missing in manifest")
            continue
        remote = str(meta.get("version") or "")
        if remote and not version_lt(local_version(product), remote):
            continue
        if product == vexx_version.PRODUCT_CLONER and app_paths.is_frozen() and include_exe:
            ok, msg = apply_cloner_exe(meta)
            if ok:
                report.applied.append(f"cloner exe: {msg}")
            else:
                ok2, msg2, _ = apply_product_zip(product, meta, root)
                if ok2:
                    report.applied.append(f"cloner: {msg2}")
                else:
                    report.errors.append(f"cloner: {msg}; {msg2}")
            continue
        ok, msg, _files = apply_product_zip(product, meta, root)
        if ok:
            report.applied.append(f"{product}: {msg}")
        else:
            report.errors.append(f"{product}: {msg}")

    state = load_state()
    state["last_apply_ts"] = time.time()
    save_state(state)
    return report


def format_report(report: UpdateReport) -> str:
    lines = [f"Vexx local {vexx_version.__version__}"]
    for c in report.checks:
        if c.product == "all":
            lines.append(f"  · {c.message}")
            continue
        flag = "↑" if c.update_available else "ok"
        lines.append(
            f"  {flag} {c.product}: {c.local_version} -> {c.remote_version} ({c.message})"
        )
    for a in report.applied:
        lines.append(f"  + {a}")
    for e in report.errors:
        lines.append(f"  ! {e}")
    return "\n".join(lines)


def startup_auto_update(products: Optional[List[str]] = None) -> None:
    cfg = load_config()
    if not cfg.get("auto_check_on_startup", True):
        return

    def run():
        try:
            cfg = load_config()
            force = bool(cfg.get("auto_apply"))
            rep = check_updates(products=products, force=force)
            if cfg.get("auto_apply") and any(
                c.update_available for c in rep.checks
            ):
                rep = apply_updates(products=products)
                if rep.applied:
                    print("[Vexx Update] Перезапусти Vexx после обновления.")
            if any(c.update_available for c in rep.checks) or rep.applied or rep.errors:
                print("[Vexx Update]\n" + format_report(rep))
        except Exception as e:
            print(f"[Vexx Update] {e}")

    threading.Thread(target=run, daemon=True, name="vexx-update").start()


def ensure_config_from_example() -> None:
    dst = _config_path()
    if os.path.isfile(dst):
        return
    ex = app_paths.data_path("update_config.example.json")
    if os.path.isfile(ex):
        shutil.copy2(ex, dst)


def main(argv: Optional[List[str]] = None) -> int:
    ensure_config_from_example()
    args = argv if argv is not None else sys.argv[1:]
    force = "--force" in args or "-f" in args
    apply = "--apply" in args or "-a" in args
    quiet = "--quiet" in args or "-q" in args

    products = None
    for a in args:
        if a.startswith("--product="):
            products = [a.split("=", 1)[1].strip()]

    rep = apply_updates(products=products) if apply else check_updates(products=products, force=force)
    if not quiet:
        print(format_report(rep))
    if rep.errors and not rep.applied and any(c.update_available for c in rep.checks):
        return 2
    if any(c.update_available for c in rep.checks):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
