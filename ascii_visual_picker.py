#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Визуальный выбор шаблонов Terminal UI — сетка карточек как у шрифтов."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import font as tkfont, ttk

import ascii_terminal
import ascii_terminal_templates as tpl
import studio_chrome
import studio_theme

MAX_CARDS = 60
PREVIEW_LINES = 12
GRID_COLS = 2
DEBOUNCE_MS = 200
_PREVIEW_CACHE: Dict[str, str] = {}
_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="layout-prev")


def _trim(text: str, max_lines: int = PREVIEW_LINES) -> str:
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines.append("…")
    return "\n".join(lines) if lines else "—"


def _render_preview(template_id: str, body: str, font_paths: Dict[str, str]) -> str:
    cached = _PREVIEW_CACHE.get(template_id)
    if cached is not None:
        return cached
    mini = f"""banner: .
font: standard

{body}

prompt: >
"""
    plain = ascii_terminal.render_terminal_plain(mini, font_paths=font_paths)
    art = _trim(plain)
    _PREVIEW_CACHE[template_id] = art
    if len(_PREVIEW_CACHE) > 800:
        for k in list(_PREVIEW_CACHE.keys())[:200]:
            _PREVIEW_CACHE.pop(k, None)
    return art


class VisualLayoutPicker(ttk.Frame):
    def __init__(
        self,
        master,
        selection_var: tk.StringVar,
        on_selected: Optional[Callable[[], None]] = None,
        font_paths: Optional[Dict[str, str]] = None,
        canvas_height: int = 360,
    ):
        super().__init__(master)
        self._sel_var = selection_var
        self._on_selected = on_selected
        self._font_paths = font_paths or {}
        self._category_var = tk.StringVar(value="Все")
        self._filter_var = tk.StringVar()
        self._filtered: List[tpl.VisualTemplate] = []
        self._debounce_id = None
        self._gen = 0
        self._card_frames: Dict[str, tk.Frame] = {}
        self._mono = tkfont.Font(family="Consolas", size=7)

        bar = ttk.Frame(self)
        bar.pack(fill=tk.X, padx=2, pady=(0, 4))
        ttk.Label(bar, text="Категория:").pack(side=tk.LEFT)
        cb = ttk.Combobox(
            bar,
            textvariable=self._category_var,
            values=tpl.CATEGORIES,
            width=16,
            state="readonly",
        )
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.schedule_rebuild())
        ttk.Label(bar, text="Поиск:").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Entry(bar, textvariable=self._filter_var, width=14).pack(side=tk.LEFT, padx=4)
        self._filter_var.trace_add("write", lambda *_: self.schedule_rebuild())

        ttk.Label(self, text="Шаблоны и рамки — клик по карточке (сетка 2×):").pack(
            anchor=tk.W, padx=4
        )
        self._hint = ttk.Label(self, text="", wraplength=420, foreground="#888")
        self._hint.pack(anchor=tk.W, padx=4)

        outer = ttk.Frame(self)
        outer.pack(fill=tk.BOTH, expand=True)
        self._canvas = tk.Canvas(
            outer,
            bg=studio_theme.THEME["bg_input"],
            highlightthickness=0,
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
        self._sel_var.trace_add("write", lambda *_: self._highlight_selection())

    def set_paths(self, paths: Dict[str, str]) -> None:
        self._font_paths = paths
        _PREVIEW_CACHE.clear()

    def _bind_wheel(self, _event=None):
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

    def _unbind_wheel(self, _event=None):
        self._canvas.unbind_all("<MouseWheel>")

    def _on_canvas_resize(self, event):
        self._canvas.itemconfigure(self._win, width=max(event.width, 280))

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-event.delta / 120), "units")

    def schedule_rebuild(self) -> None:
        if self._debounce_id:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(DEBOUNCE_MS, self._rebuild)

    def _ordered(self, items: List[tpl.VisualTemplate]) -> List[tpl.VisualTemplate]:
        feat = [t for t in items if t.id in tpl.FEATURED_IDS]
        rest = [t for t in items if t.id not in tpl.FEATURED_IDS]
        ordered = feat + rest
        return ordered[:MAX_CARDS]

    def _rebuild(self) -> None:
        self._debounce_id = None
        cat = self._category_var.get()
        q = self._filter_var.get()
        total_list = tpl.filter_templates("Все", q, include_borders=True)
        items = tpl.filter_templates(cat, q, include_borders=True)
        shown = self._ordered(items)
        total = len(total_list)
        if total > len(shown):
            self._hint.config(
                text=f"Показано {len(shown)} из {total}. Сузь «Поиск» или категорию."
            )
        else:
            self._hint.config(text=f"{len(shown)} шаблонов · категория «{cat}»")
        self._filtered = shown

        for child in self._inner.winfo_children():
            child.destroy()
        self._card_frames.clear()
        if not shown:
            ttk.Label(self._inner, text="(ничего не найдено)").grid(
                padx=8, pady=8, column=0
            )
            return

        for c in range(GRID_COLS):
            self._inner.columnconfigure(c, weight=1, uniform="cards")

        self._gen += 1
        gen = self._gen
        paths = self._font_paths

        def work():
            cards: List[Tuple[tpl.VisualTemplate, str]] = []
            for t in shown:
                art = _render_preview(t.id, t.body, paths)
                cards.append((t, art))
            self.after(0, lambda: self._apply_cards(cards, gen))

        import threading

        threading.Thread(target=work, daemon=True).start()

    def _apply_cards(self, cards: List[Tuple[tpl.VisualTemplate, str]], gen: int) -> None:
        if gen != self._gen:
            return
        mono = self._mono
        T = studio_theme.THEME
        for idx, (t, art) in enumerate(cards):
            row, col = divmod(idx, GRID_COLS)
            fr = tk.Frame(
                self._inner,
                bg=T["bg_elevated"],
                highlightthickness=2,
                highlightbackground=T["border"],
                cursor="hand2",
            )
            fr.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            title = t.title
            if t.category == "Рамки":
                sub = f"рамка · {t.style}"
            else:
                sub = t.category
            lbl = tk.Label(
                fr,
                text=title,
                bg=T["bg_elevated"],
                fg=T["accent2"],
                font=("Segoe UI", 9, "bold"),
                anchor=tk.W,
            )
            lbl.pack(fill=tk.X, padx=6, pady=(4, 0))
            sub_l = tk.Label(
                fr,
                text=sub,
                bg=T["bg_elevated"],
                fg=T["fg_muted"],
                font=("Segoe UI", 8),
                anchor=tk.W,
            )
            sub_l.pack(fill=tk.X, padx=6)
            prev = tk.Label(
                fr,
                text=art,
                bg=T["bg_elevated"],
                fg=T["fg_muted"],
                font=mono,
                justify=tk.LEFT,
                anchor=tk.NW,
            )
            prev.pack(fill=tk.BOTH, expand=True, padx=6, pady=(2, 6))

            def pick(_e=None, tid=t.id):
                self._sel_var.set(tid)
                if self._on_selected:
                    self._on_selected()

            for w in (fr, lbl, sub_l, prev):
                w.bind("<Button-1>", pick)
            self._card_frames[t.id] = fr
        self._highlight_selection()

    def _highlight_selection(self) -> None:
        cur = self._sel_var.get()
        T = studio_theme.THEME
        for tid, fr in self._card_frames.items():
            if tid == cur:
                fr.configure(
                    highlightbackground=T["accent"],
                    highlightcolor=T["accent3"],
                )
            else:
                fr.configure(
                    highlightbackground=T["border"],
                    highlightcolor=T["border"],
                )
