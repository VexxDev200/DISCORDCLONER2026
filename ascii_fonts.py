#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Все FIGlet-шрифты: pyfiglet + локальные .flf (как у TAAG / figlet.org)."""

import hashlib
import importlib.resources
import io
import json
import os
import shutil
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Set, Tuple

try:
    from pyfiglet import FigletFont, figlet_format
    from pyfiglet import SHARED_DIRECTORY as PYFIGLET_SHARED
except ImportError:
    FigletFont = None
    figlet_format = None
    PYFIGLET_SHARED = None

ROOT = Path(__file__).resolve().parent
FIGLET_FONT_DIR = ROOT / "figlet_fonts"
CUSTOM_FONT_DIR = ROOT / "custom_fonts"
REGISTRY_CACHE = ROOT / ".ascii_font_registry.json"
CACHE_VERSION = 2

FIGLET_BUNDLE_URLS = (
    "https://github.com/cmatsuoka/figlet/archive/refs/heads/master.zip",
    "https://github.com/xero/figlet-fonts/archive/refs/heads/master.zip",
)

_PROBE_TEXT = "MW@"
_PROBE_WIDTH = 999


def _scan_flf(directory: Path) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    if not directory.is_dir():
        return out
    for flf in directory.rglob("*.flf"):
        key = flf.stem
        if key not in out:
            out[key] = flf
    return out


def _dirs_signature() -> str:
    parts: List[str] = []
    for folder in (FIGLET_FONT_DIR, CUSTOM_FONT_DIR):
        if not folder.is_dir():
            parts.append(f"{folder.name}:empty")
            continue
        h = hashlib.sha256()
        for flf in sorted(folder.rglob("*.flf"), key=lambda p: str(p).lower()):
            st = flf.stat()
            h.update(f"{flf.name}|{st.st_mtime_ns}|{st.st_size}\n".encode("utf-8"))
        parts.append(f"{folder.name}:{h.hexdigest()[:24]}")
    return "|".join(parts)


def _package_font_names() -> Set[str]:
    """Только встроенные pyfiglet (без %APPDATA%/pyfiglet)."""
    if FigletFont is None:
        return set()
    names: Set[str] = set()
    for font in importlib.resources.files("pyfiglet.fonts").iterdir():
        if font.is_file() and FigletFont.isValidFont(font.name):
            names.add(font.name.split(".", 2)[0])
    return names



def _sync_flf_to_pyfiglet_shared(files: Dict[str, Path]) -> None:
    """pyfiglet ищет extra-шрифты только по имени в SHARED_DIRECTORY (не по полному пути)."""
    if not PYFIGLET_SHARED or not files:
        return
    shared = Path(PYFIGLET_SHARED)
    shared.mkdir(parents=True, exist_ok=True)
    for _name, src in files.items():
        dest = shared / src.name
        try:
            if not dest.exists() or src.stat().st_mtime_ns > dest.stat().st_mtime_ns:
                shutil.copy2(src, dest)
        except OSError:
            continue


def _remove_shared_font(src: Path) -> None:
    if not PYFIGLET_SHARED:
        return
    dest = Path(PYFIGLET_SHARED) / src.name
    try:
        dest.unlink(missing_ok=True)
    except OSError:
        pass


def _font_renders(font_name: str) -> bool:
    if figlet_format is None:
        return False
    try:
        figlet_format(_PROBE_TEXT, font=font_name, width=_PROBE_WIDTH)
        return True
    except Exception:
        return False


def _discover_extra_fonts() -> Tuple[Set[str], Set[str]]:
    """Валидные и отброшенные extra-имена (не встроенные pyfiglet)."""
    valid: Set[str] = set()
    invalid: Set[str] = set()
    if FigletFont is None:
        return valid, invalid

    pkg = _package_font_names()
    downloaded = _scan_flf(FIGLET_FONT_DIR)
    custom = _scan_flf(CUSTOM_FONT_DIR)

    to_sync: Dict[str, Path] = {}
    for name, path in downloaded.items():
        if name not in pkg:
            to_sync[name] = path
    for name, path in custom.items():
        to_sync[name] = path

    _sync_flf_to_pyfiglet_shared(to_sync)

    for name, src in sorted(to_sync.items(), key=lambda x: x[0].lower()):
        if _font_renders(name):
            valid.add(name)
        else:
            invalid.add(name)
            _remove_shared_font(src)

    # Убрать из shared битые файлы, оставшиеся от старых запусков
    if PYFIGLET_SHARED and Path(PYFIGLET_SHARED).is_dir():
        pkg_lower = {n.lower() for n in pkg}
        for flf in Path(PYFIGLET_SHARED).glob("*.flf"):
            stem = flf.stem
            if stem.lower() in pkg_lower:
                continue
            if stem in valid:
                continue
            if _font_renders(stem):
                valid.add(stem)
            else:
                invalid.add(stem)
                try:
                    flf.unlink(missing_ok=True)
                except OSError:
                    pass

    return valid, invalid


def _build_font_paths(valid_extra: Set[str]) -> Dict[str, str]:
    paths: Dict[str, str] = {}
    for name in sorted(_package_font_names(), key=str.lower):
        paths[name] = name
    for name in sorted(valid_extra, key=str.lower):
        if name not in paths:
            paths[name] = name
    return paths


def _load_registry_cache() -> dict | None:
    if not REGISTRY_CACHE.is_file():
        return None
    try:
        data = json.loads(REGISTRY_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("version") != CACHE_VERSION:
        return None
    if data.get("signature") != _dirs_signature():
        return None
    return data


def _save_registry_cache(valid_extra: Set[str], invalid_extra: Set[str]) -> None:
    payload = {
        "version": CACHE_VERSION,
        "signature": _dirs_signature(),
        "valid_extra": sorted(valid_extra, key=str.lower),
        "invalid_extra": sorted(invalid_extra, key=str.lower),
    }
    try:
        REGISTRY_CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=0), encoding="utf-8")
    except OSError:
        pass


def font_registry(*, rebuild: bool = False) -> Tuple[List[str], Dict[str, str]]:
    """Имена шрифтов → имя для figlet_format (всегда имя, не путь)."""
    cached = None if rebuild else _load_registry_cache()
    if cached is not None:
        valid_extra = set(cached.get("valid_extra") or [])
        paths = _build_font_paths(valid_extra)
        names = sorted(paths.keys(), key=str.lower)
        return names, paths

    valid_extra, invalid_extra = _discover_extra_fonts()
    _save_registry_cache(valid_extra, invalid_extra)
    paths = _build_font_paths(valid_extra)
    names = sorted(paths.keys(), key=str.lower)
    return names, paths


def invalidate_font_cache() -> None:
    try:
        REGISTRY_CACHE.unlink(missing_ok=True)
    except OSError:
        pass
    clear_render_cache()


@lru_cache(maxsize=4096)
def _figlet_line_cached(line: str, font_name: str, width: int) -> str:
    if figlet_format is None:
        return ""
    return figlet_format(line, font=font_name, width=width).rstrip("\n")


def clear_render_cache() -> None:
    _figlet_line_cached.cache_clear()


def render_figlet(text: str, font_key: str, paths: Dict[str, str], width: int = 120) -> str:
    if figlet_format is None or not text.strip():
        return ""
    font_name = paths.get(font_key, font_key)
    chunks = []
    for line in text.splitlines():
        if not line.strip():
            chunks.append("")
            continue
        try:
            chunks.append(_figlet_line_cached(line, font_name, width))
        except Exception as e:
            return f"[ошибка '{font_key}': {e}]"
    return "\n".join(chunks)


def _format_download_error(exc: BaseException) -> str:
    if exc is None:
        return "неизвестная ошибка"
    msg = str(exc).strip()
    if msg:
        return f"{type(exc).__name__}: {msg}"
    return type(exc).__name__


def _extract_flf_from_zip(data: bytes) -> int:
    count = 0
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for info in zf.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".flf"):
                continue
            base = os.path.basename(info.filename)
            if not base:
                continue
            target = FIGLET_FONT_DIR / base
            if target.exists():
                continue
            target.write_bytes(zf.read(info))
            count += 1
    return count


def download_full_figlet_bundle(progress_cb=None) -> Tuple[int, str]:
    import urllib.error
    import urllib.request

    FIGLET_FONT_DIR.mkdir(parents=True, exist_ok=True)
    errors: List[str] = []
    added = 0
    ok_sources: List[str] = []

    for url in FIGLET_BUNDLE_URLS:
        host = url.split("/")[2]
        if progress_cb:
            progress_cb(f"Загрузка: {host}…")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as ex:
            errors.append(f"{host}\n  → {_format_download_error(ex)}")
            continue

        if progress_cb:
            progress_cb(f"Распаковка {host}…")
        try:
            n = _extract_flf_from_zip(data)
            added += n
            ok_sources.append(host)
        except zipfile.BadZipFile as ex:
            errors.append(f"{host}\n  → битый zip: {ex}")
            continue

    invalidate_font_cache()
    if progress_cb:
        progress_cb("Проверка шрифтов…")
    names, _ = font_registry(rebuild=True)
    on_disk = len(list(FIGLET_FONT_DIR.glob("*.flf")))

    if ok_sources:
        src = " + ".join(ok_sources)
        msg = (
            f"Готово: +{added} новых .flf на диске ({on_disk}), "
            f"в списке {len(names)} рабочих шрифтов.\n({src})"
        )
        if errors:
            msg += "\n\nНе загрузилось:\n" + "\n".join(errors)
        return len(names), msg

    detail = "\n\n".join(errors) if errors else "нет доступных URL"
    raise RuntimeError(f"Не удалось скачать архив шрифтов.\n\n{detail}")
