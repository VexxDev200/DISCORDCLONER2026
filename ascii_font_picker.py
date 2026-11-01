#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Визуальный выбор FIGlet-шрифта — превью по клику."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import font as tkfont, ttk

import ascii_fonts
import studio_chrome
import studio_theme

PREVIEW_WIDTH = 36
MAX_CARDS = 48
PREVIEW_LINES = 4
PICKER_DEBOUNCE_MS = 280
CARD_SAMPLE_MAX = 10
FEATURED = (
    "slant",
    "standard",
    "banner3",
    "big",
    "block",
    "doom",
    "graffiti",
    "lean",
    "rectangles",
    "small",
)

_PREVIEW_CACHE: Dict[Tuple[str, str, int], str] = {}
_POOL = ThreadPoolExecutor(max_workers=6, thread_name_prefix="figlet-prev")


def _trim_art(art: str, max_lines: int = PREVIEW_LINES) -> str:
    lines = [ln for ln in art.splitlines() if ln.strip()]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
    return "\n".join(lines) if lines else "—"


def _render_card(sample: str, name: str, paths: Dict[str, str]) -> Tuple[str, str]:
    key = (sample, name, PREVIEW_WIDTH)
    cached = _PREVIEW_CACHE.get(key)
    if cached is not None:
        return name, cached
    art = ascii_fonts.render_figlet(sample, name, paths, width=PREVIEW_WIDTH)
    trimmed = _trim_art(art)
    _PREVIEW_CACHE[key] = trimmed
    if len(_PREVIEW_CACHE) > 3000:
        for k in list(_PREVIEW_CACHE.keys())[:500]:
            _PREVIEW_CACHE.pop(k, None)
    return name, trimmed


class VisualFontPicker(ttk.Frame):
    """Список карточек: имя + мини-баннер; клик = выбор шрифта."""

    def __init__(
        self,
        master,
        font_var: tk.StringVar,
        on_selected: Optional[Callable[[], None]] = None,
        sample_fn: Optional[Callable[[], str]] = None,
        canvas_height: int = 320,
    ):
        super().__init__(master)
        self._font_var = font_var
        self._on_selected = on_selected
        self._sample_fn = sample_fn or (lambda: "TEST")
        self._font_paths: Dict[str, str] = {}
        self._filtered: List[str] = []
        self._debounce_id = None
        self._gen = 0
        self._card_frames: Dict[str, tk.Frame] = {}
        self._mono = tkfont.Font(family="Consolas", size=7)

        ttk.Label(self, text="Визуальный выбор — клик по карточке:").pack(
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
        self._font_var.trace_add("write", lambda *_: self._highlight_selection())

    def _bind_wheel(self, _event=None):
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

    def _unbind_wheel(self, _event=None):
        self._canvas.unbind_all("<MouseWheel>")

    def _on_canvas_resize(self, event):
        self._canvas.itemconfigure(self._win, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-event.delta / 120), "units")

    def set_paths(self, paths: Dict[str, str]) -> None:
        self._font_paths = paths

    def schedule_rebuild(self, filtered_names: List[str], total: int) -> None:
        self._filtered = filtered_names
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(PICKER_DEBOUNCE_MS, lambda: self._rebuild(total))

    def _ordered_names(self) -> List[str]:
        q = self._filtered
        if not q:
            return []
        featured = [f for f in FEATURED if f in q]
        rest = [f for f in q if f not in featured]
        return (featured + rest)[:MAX_CARDS]

    def _rebuild(self, total: int) -> None:
        self._debounce_id = None
        names = self._ordered_names()
        if total > len(names):
            self._hint.config(
                text=f"Показано {len(names)} из {total}. Уточни «Поиск», чтобы сузить."
            )
        else:
            self._hint.config(text=f"{len(names)} шрифтов")

        for child in self._inner.winfo_children():
            child.destroy()
        self._card_frames.clear()

        if not names:
            ttk.Label(self._inner, text="(нет шрифтов)").pack(padx=8, pady=8)
            return

        self._gen += 1
        gen = self._gen
        raw = self._sample_fn().strip() or "TEST"
        sample = raw[:CARD_SAMPLE_MAX]

        paths = self._font_paths

        def work():
            cards = list(_POOL.map(lambda name: _render_card(sample, name, paths), names))
            self.after(0, lambda: self._apply_cards(cards, gen))

        import threading

        threading.Thread(target=work, daemon=True).start()

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
                self._font_var.set(n)
                if self._on_selected:
                    self._on_selected()

            for w in (fr, lbl, prev):
                w.bind("<Button-1>", pick)
            self._card_frames[name] = fr

        self._highlight_selection()

    def _highlight_selection(self) -> None:
        cur = self._font_var.get()
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
