#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Визуальный выбор стиля таблицы — как picker шрифтов."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

import tkinter as tk
from tkinter import font as tkfont, ttk

import ascii_table_styles
import studio_chrome
import studio_theme

MAX_CARDS = 200
PREVIEW_LINES = 6


def _preview_art(style: str) -> str:
    import ascii_terminal

    rows = [
        ["Col A", "Col B"],
        ["[1]", "TEST"],
        ["[2]", "TEST"],
    ]
    lines = ascii_terminal.render_table_preview(rows, style=style, title="TEST")
    out = lines[:PREVIEW_LINES]
    return "\n".join(out) if out else "—"


class VisualTablePicker(ttk.Frame):
    def __init__(
        self,
        master,
        style_var: tk.StringVar,
        on_selected: Optional[Callable[[], None]] = None,
        canvas_height: int = 280,
    ):
        super().__init__(master)
        self._style_var = style_var
        self._on_selected = on_selected
        self._filtered: List[str] = []
        self._debounce_id = None
        self._gen = 0
        self._card_frames: Dict[str, tk.Frame] = {}
        self._mono = tkfont.Font(family="Consolas", size=7)
        self._cache: Dict[str, str] = {}

        ttk.Label(self, text="Стили таблиц — клик по карточке:").pack(
            anchor=tk.W, padx=4, pady=(0, 2)
        )
        self._hint = ttk.Label(self, text="", wraplength=280, foreground="#666")
        self._hint.pack(anchor=tk.W, padx=4)

        outer = ttk.Frame(self)
        outer.pack(fill=tk.BOTH, expand=True)
        self._canvas = tk.Canvas(
            outer,
            bg=studio_theme.THEME["bg_input"],
            highlightthickness=0,
            width=300,
            height=canvas_height,
        )
        sy = studio_chrome.themed_scrollbar(outer, orient=tk.VERTICAL, command=self._canvas.yview)
        self._inner = ttk.Frame(self._canvas)
        self._win = self._canvas.create_window((0, 0), window=self._inner, anchor=tk.NW)
        self._canvas.configure(yscrollcommand=sy.set)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sy.pack(side=tk.RIGHT, fill=tk.Y)
        self._inner.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        self._canvas.bind("<Enter>", self._bind_wheel)
        self._canvas.bind("<Leave>", self._unbind_wheel)
        self._style_var.trace_add("write", lambda *_: self._highlight_selection())

    def _bind_wheel(self, _event=None):
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

    def _unbind_wheel(self, _event=None):
        self._canvas.unbind_all("<MouseWheel>")

    def _on_canvas_resize(self, event):
        self._canvas.itemconfigure(self._win, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-event.delta / 120), "units")

    def schedule_rebuild(self, filtered: Optional[List[str]] = None) -> None:
        if filtered is not None:
            self._filtered = filtered
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(120, self._rebuild)

    def _ordered(self) -> List[str]:
        q = self._filtered or ascii_table_styles.style_names()
        feat = [s for s in ascii_table_styles.FEATURED_TABLES if s in q]
        rest = [s for s in q if s not in feat]
        ordered = feat + sorted(rest)
        return ordered[:MAX_CARDS]

    def _rebuild(self) -> None:
        self._debounce_id = None
        names = self._ordered()
        total = len(ascii_table_styles.style_names())
        if total > len(names):
            self._hint.config(text=f"Показано {len(names)} из {total} стилей.")
        else:
            self._hint.config(text=f"{len(names)} стилей таблиц")

        for child in self._inner.winfo_children():
            child.destroy()
        self._card_frames.clear()

        self._gen += 1
        gen = self._gen
        cards = []
        for name in names:
            art = self._cache.get(name)
            if art is None:
                art = _preview_art(name)
                self._cache[name] = art
            cards.append((name, art))
        self._apply_cards(cards, gen)

    def _apply_cards(self, cards: List[tuple], gen: int) -> None:
        if gen != self._gen:
            return
        mono = self._mono
        T = studio_theme.THEME
        for name, art in cards:
            fr = tk.Frame(
                self._inner,
                bg=T["bg_elevated"],
                highlightthickness=2,
                highlightbackground=T["border"],
                cursor="hand2",
            )
            fr.pack(fill=tk.X, padx=4, pady=3)
            lbl = tk.Label(
                fr,
                text=name,
                bg=T["bg_elevated"],
                fg=T["accent2"],
                font=("Segoe UI", 9, "bold"),
                anchor=tk.W,
            )
            lbl.pack(fill=tk.X, padx=6, pady=(4, 0))
            prev = tk.Label(
                fr,
                text=art,
                bg=T["bg_elevated"],
                fg=T["fg_muted"],
                font=mono,
                justify=tk.LEFT,
                anchor=tk.W,
            )
            prev.pack(fill=tk.X, padx=6, pady=(0, 6))

            def pick(_e=None, n=name):
                self._style_var.set(n)
                if self._on_selected:
                    self._on_selected()

            for w in (fr, lbl, prev):
                w.bind("<Button-1>", pick)
            self._card_frames[name] = fr
        self._highlight_selection()

    def _highlight_selection(self) -> None:
        cur = self._style_var.get()
        T = studio_theme.THEME
        for name, fr in self._card_frames.items():
            if name == cur:
                fr.configure(
                    highlightbackground=T["accent"],
                    highlightcolor=T["accent3"],
                )
            else:
                fr.configure(
                    highlightbackground=T["border"],
                    highlightcolor=T["border"],
                )
