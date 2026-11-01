#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Кастомный title bar и scrollbars под cyber-тему Vexx ASCII."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple

import studio_theme

T = studio_theme.THEME

TITLE_H = 38
RESIZE_MARGIN = 5


def enhance_theme(style: ttk.Style) -> None:
    style.configure(
        "TEntry",
        fieldbackground=T["bg_input"],
        foreground=T["fg"],
        insertcolor=T["accent2"],
        bordercolor=T["border"],
        lightcolor=T["border"],
        darkcolor=T["bg_elevated"],
    )
    style.configure(
        "TCombobox",
        fieldbackground=T["bg_input"],
        foreground=T["fg"],
        arrowcolor=T["accent2"],
        bordercolor=T["border"],
        lightcolor=T["border"],
        darkcolor=T["bg_elevated"],
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", T["bg_input"]), ("disabled", T["bg_panel"])],
        foreground=[("disabled", T["fg_muted"])],
    )

    for orient, name in (
        ("vertical", "Vertical.TScrollbar"),
        ("horizontal", "Horizontal.TScrollbar"),
    ):
        vname = f"Vexx.{name}"
        style.configure(
            vname,
            background=T["border_glow"],
            troughcolor=T["bg_input"],
            bordercolor=T["border"],
            arrowcolor=T["accent2"],
            darkcolor=T["bg_elevated"],
            lightcolor=T["select_bg"],
            gripcount=0,
            width=12,
        )
        style.map(
            vname,
            background=[
                ("active", T["accent"]),
                ("pressed", T["accent_hover"]),
                ("!disabled", T["border_glow"]),
            ],
            troughcolor=[("!disabled", T["bg_input"])],
            arrowcolor=[("active", T["accent2"]), ("!disabled", T["fg_muted"])],
        )


def themed_scrollbar(master, orient: str = tk.VERTICAL, **kwargs) -> ttk.Scrollbar:
    st = "Vexx.Vertical.TScrollbar"
    if orient in (tk.HORIZONTAL, "horizontal"):
        st = "Vexx.Horizontal.TScrollbar"
    return ttk.Scrollbar(master, orient=orient, style=st, **kwargs)


def _caption_color_bgr(hex_rgb: str) -> int:
    h = hex_rgb.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (b << 16) | (g << 8) | r


def _try_dwm_dark_title(root: tk.Tk) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        dark = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark)
        )
        cap = ctypes.c_int(_caption_color_bgr(T["titlebar_bg"]))
        for attr in (35, 34):
            try:
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(cap), ctypes.sizeof(cap)
                )
            except Exception:
                pass
    except Exception:
        pass


def _chrome_btn(parent, text: str, fg: str, hover_bg: str, command) -> tk.Label:
    lbl = tk.Label(
        parent,
        text=text,
        bg=T["titlebar_bg"],
        fg=fg,
        font=("Segoe UI", 11),
        width=3,
        cursor="hand2",
    )

    def on_enter(_e=None):
        lbl.configure(bg=hover_bg)

    def on_leave(_e=None):
        lbl.configure(bg=T["titlebar_bg"])

    lbl.bind("<Enter>", on_enter)
    lbl.bind("<Leave>", on_leave)
    lbl.bind("<Button-1>", lambda _e: command())
    return lbl


def attach_custom_titlebar(root: tk.Tk, title: str) -> tk.Frame:
    root.configure(bg=T["titlebar_bg"])
    saved_geom = root.geometry()
    root.overrideredirect(True)

    bar = tk.Frame(root, bg=T["titlebar_bg"], highlightthickness=0)
    bar.pack(side=tk.TOP, fill=tk.X)

    inner = tk.Frame(bar, bg=T["titlebar_bg"], height=TITLE_H)
    inner.pack(fill=tk.X)
    inner.pack_propagate(False)

    title_lbl = tk.Label(
        inner,
        text=f"  {title}",
        bg=T["titlebar_bg"],
        fg=T["fg"],
        font=("Segoe UI Semibold", 10),
        anchor=tk.W,
    )
    title_lbl.pack(side=tk.LEFT)

    accent_dot = tk.Label(
        inner,
        text=" · cyber",
        bg=T["titlebar_bg"],
        fg=T["accent2"],
        font=("Segoe UI", 9),
    )
    accent_dot.pack(side=tk.LEFT)

    btns = tk.Frame(inner, bg=T["titlebar_bg"])
    btns.pack(side=tk.RIGHT, padx=4)

    root._vexx_maximized = False
    root._vexx_restore_geom = saved_geom

    def minimize():
        root.overrideredirect(False)
        root.iconify()

        def restore_border(_e=None):
            root.overrideredirect(True)
            root.unbind("<Map>", restore_border_id)

        restore_border_id = root.bind("<Map>", restore_border, add="+")

    def toggle_max():
        if root._vexx_maximized:
            root.geometry(root._vexx_restore_geom)
            root._vexx_maximized = False
        else:
            root._vexx_restore_geom = root.geometry()
            sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
            root.geometry(f"{sw}x{sh}+0+0")
            root._vexx_maximized = True

    _chrome_btn(btns, "─", T["fg_muted"], T["bg_elevated"], minimize).pack(
        side=tk.LEFT, padx=1
    )
    _chrome_btn(btns, "□", T["fg_muted"], T["bg_elevated"], toggle_max).pack(
        side=tk.LEFT, padx=1
    )
    _chrome_btn(btns, "✕", T["accent3"], "#4a1830", root.destroy).pack(
        side=tk.LEFT, padx=1
    )

    glow = tk.Frame(root, bg=T["accent"], height=2)
    glow.pack(side=tk.TOP, fill=tk.X)

    body = tk.Frame(root, bg=T["bg"])
    body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    drag: dict = {}

    def start_drag(event):
        drag["x"] = event.x_root - root.winfo_x()
        drag["y"] = event.y_root - root.winfo_y()

    def do_drag(event):
        if root._vexx_maximized:
            return
        root.geometry(
            f"+{event.x_root - drag.get('x', 0)}+{event.y_root - drag.get('y', 0)}"
        )

    for w in (inner, title_lbl, accent_dot):
        w.bind("<Button-1>", start_drag)
        w.bind("<B1-Motion>", do_drag)
        w.bind("<Double-Button-1>", lambda _e: toggle_max())

    _bind_resize(root)
    root.after(80, lambda: _try_dwm_dark_title(root))
    return body


def _bind_resize(root: tk.Tk) -> None:
    root._vexx_resize = None

    def edge_at(x, y) -> Optional[str]:
        w, h = root.winfo_width(), root.winfo_height()
        m = RESIZE_MARGIN
        left, right = x <= m, x >= w - m
        top, bot = y <= m, y >= h - m
        if top and left:
            return "nw"
        if top and right:
            return "ne"
        if bot and left:
            return "sw"
        if bot and right:
            return "se"
        if left:
            return "w"
        if right:
            return "e"
        if bot:
            return "s"
        if top:
            return "n"
        return None

    def on_motion(event):
        if root._vexx_maximized:
            return
        edge = edge_at(event.x, event.y)
        cursors = {
            "n": "top_side",
            "s": "bottom_side",
            "e": "right_side",
            "w": "left_side",
            "ne": "top_right_corner",
            "nw": "top_left_corner",
            "se": "bottom_right_corner",
            "sw": "bottom_left_corner",
        }
        root.configure(cursor=cursors.get(edge or "", ""))

    def start_resize(event):
        if root._vexx_maximized:
            return
        edge = edge_at(event.x, event.y)
        if edge:
            root._vexx_resize = (
                edge,
                event.x_root,
                event.y_root,
                root.winfo_x(),
                root.winfo_y(),
                root.winfo_width(),
                root.winfo_height(),
            )

    def do_resize(event):
        data = root._vexx_resize
        if not data:
            return
        edge, sx, sy, ox, oy, ow, oh = data
        dx, dy = event.x_root - sx, event.y_root - sy
        nx, ny, nw, nh = ox, oy, ow, oh
        if "e" in edge:
            nw = max(400, ow + dx)
        if "s" in edge:
            nh = max(300, oh + dy)
        if "w" in edge:
            nw = max(400, ow - dx)
            nx = ox + dx
        if "n" in edge:
            nh = max(300, oh - dy)
            ny = oy + dy
        root.geometry(f"{int(nw)}x{int(nh)}+{int(nx)}+{int(ny)}")

    def stop_resize(_event):
        root._vexx_resize = None

    root.bind("<Motion>", on_motion)
    root.bind("<ButtonPress-1>", start_resize, add="+")
    root.bind("<B1-Motion>", do_resize, add="+")
    root.bind("<ButtonRelease-1>", stop_resize, add="+")


def style_menubar(menubar: tk.Menu) -> None:
    try:
        menubar.configure(
            bg=T["bg_elevated"],
            fg=T["fg"],
            activebackground=T["select_bg"],
            activeforeground=T["accent2"],
            borderwidth=0,
            relief=tk.FLAT,
        )
    except tk.TclError:
        pass


def install_window_chrome(root: tk.Tk, title: str) -> Tuple[tk.Frame, ttk.Style]:
    style = studio_theme.apply_theme(root)
    body = attach_custom_titlebar(root, title)
    return body, style
