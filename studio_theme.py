#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Тёмная cyber-тема для Vexx ASCII (GUI)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Dict

THEME: Dict[str, str] = {
    "bg": "#08080e",
    "bg_panel": "#101018",
    "bg_elevated": "#161622",
    "bg_input": "#1c1c2a",
    "bg_preview": "#050508",
    "fg": "#eaeaf4",
    "fg_muted": "#7a7a94",
    "accent": "#bf5fff",
    "accent_hover": "#d98aff",
    "accent2": "#00d9ff",
    "accent3": "#ff4d8d",
    "border": "#2c2c42",
    "border_glow": "#5a3d7a",
    "select_bg": "#352550",
    "select_fg": "#ffffff",
    "status_bg": "#0e0e16",
    "titlebar_bg": "#0c0c14",
    "tab_active": "#221a32",
    "tab_inactive": "#12121c",
    "success": "#00e676",
    "warning": "#ffb300",
}


def apply_theme(root: tk.Misc) -> ttk.Style:
    root.configure(bg=THEME["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    T = THEME
    base = (
        ("TFrame", {"background": T["bg_panel"]}),
        ("TLabel", {"background": T["bg_panel"], "foreground": T["fg"]}),
        (
            "TLabelframe",
            {"background": T["bg_panel"], "foreground": T["accent2"], "bordercolor": T["border"]},
        ),
        ("TLabelframe.Label", {"background": T["bg_panel"], "foreground": T["accent2"]}),
        ("TButton", {"background": T["bg_elevated"], "foreground": T["fg"], "bordercolor": T["border"]}),
        ("TCheckbutton", {"background": T["bg_panel"], "foreground": T["fg"]}),
        ("TNotebook", {"background": T["bg"], "bordercolor": T["border"]}),
        (
            "TNotebook.Tab",
            {
                "background": T["tab_inactive"],
                "foreground": T["fg_muted"],
                "padding": [14, 6],
            },
        ),
        ("TPanedwindow", {"background": T["bg"]}),
        ("Vertical.TScrollbar", {"background": T["bg_elevated"], "troughcolor": T["bg_input"]}),
        ("Horizontal.TScrollbar", {"background": T["bg_elevated"], "troughcolor": T["bg_input"]}),
    )
    for name, opts in base:
        style.configure(name, **opts)

    import studio_chrome

    studio_chrome.enhance_theme(style)

    style.map(
        "TNotebook.Tab",
        background=[("selected", T["tab_active"]), ("active", T["bg_elevated"])],
        foreground=[("selected", T["accent"]), ("active", T["fg"])],
    )
    style.map(
        "TButton",
        background=[("active", T["select_bg"]), ("pressed", T["border_glow"])],
        foreground=[("active", T["accent2"])],
    )
    style.configure(
        "Accent.TButton",
        background=T["select_bg"],
        foreground=T["accent2"],
        bordercolor=T["accent"],
    )
    style.map("Accent.TButton", background=[("active", T["border_glow"])])
    return style


def style_text_widget(w: tk.Text) -> None:
    T = THEME
    w.configure(
        bg=T["bg_preview"],
        fg=T["fg"],
        insertbackground=T["accent2"],
        selectbackground=T["select_bg"],
        selectforeground=T["select_fg"],
        highlightthickness=0,
        relief=tk.FLAT,
    )


def style_entry_widget(w: tk.Widget) -> None:
    T = THEME
    try:
        w.configure(
            fieldbackground=T["bg_input"],
            foreground=T["fg"],
            background=T["bg_input"],
        )
    except tk.TclError:
        pass
