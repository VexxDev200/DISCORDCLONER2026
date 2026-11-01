#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Логотип и иконка окна Vexx ASCII."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
ICON_ICO = ASSETS / "vexx_ascii_icon.ico"
ICON_PNG = ASSETS / "vexx_ascii_icon.png"
ICON_VERSION = 3


def ensure_brand_assets() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    stamp = ASSETS / ".icon_version"
    if ICON_PNG.is_file() and ICON_ICO.is_file():
        try:
            if stamp.read_text(encoding="utf-8").strip() == str(ICON_VERSION):
                return
        except OSError:
            pass
    for p in (ICON_ICO, ICON_PNG, stamp):
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return
    size = 256
    img = Image.new("RGBA", (size, size), (8, 8, 14, 255))
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / size
        r = int(140 + 80 * (1 - t))
        g = int(40 + 30 * t)
        b = int(200 + 55 * t)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    draw.rounded_rectangle(
        (12, 12, size - 12, size - 12), radius=36, outline=(0, 217, 255, 220), width=4
    )
    draw.rounded_rectangle(
        (20, 20, size - 20, size - 20), radius=28, outline=(191, 95, 255, 180), width=2
    )
    try:
        font = ImageFont.truetype("arialbd.ttf", 96)
    except OSError:
        font = ImageFont.load_default()
    draw.text((52, 72), "VX", fill=(255, 255, 255, 255), font=font)
    img.save(ICON_PNG, "PNG")
    img.save(ICON_ICO, format="ICO", sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
    stamp.write_text(str(ICON_VERSION), encoding="utf-8")


def apply_window_icon(root: tk.Tk) -> None:
    ensure_brand_assets()
    if not ICON_ICO.is_file():
        return
    ico = str(ICON_ICO.resolve())

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "VexxAscii.Studio.2026"
            )
        except Exception:
            pass

    def _set() -> None:
        try:
            root.iconbitmap(default=ico)
        except tk.TclError:
            pass
        try:
            root.iconbitmap(ico)
        except tk.TclError:
            pass
        if ICON_PNG.is_file():
            try:
                img = tk.PhotoImage(file=str(ICON_PNG.resolve()))
                root.iconphoto(True, img)
                root._brand_icon_ref = img
            except tk.TclError:
                pass

    _set()
    root.after_idle(_set)
