#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vexx ASCII — FIGlet, Terminal UI (таблицы, меню, перелив ANSI)."""

import re
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, font as tkfont, ttk

import ascii_colors
import ascii_fonts
import ascii_font_picker
import ascii_visual_picker
import ascii_terminal
import ascii_terminal_templates
import studio_brand
import studio_theme
import studio_chrome

DEFAULT_FONT = "slant"
PREVIEW_WIDTH = 120
EXAMPLE_PATH = ascii_fonts.ROOT / "terminal_ui.example.txt"


def _paint_colored_text(widget: tk.Text, art: str, preset: str, phase: float) -> None:
    widget.configure(state=tk.NORMAL)
    widget.delete("1.0", tk.END)
    if not art:
        widget.insert("1.0", "(пусто)")
        widget.configure(state=tk.DISABLED)
        return
    if preset == "Без цвета":
        widget.insert("1.0", art)
        widget.configure(state=tk.DISABLED)
        return
    phase = round(phase, 2)
    tags_used: set = set()
    lines = art.split("\n")
    for row, line in enumerate(lines):
        if row:
            widget.insert(tk.END, "\n")
        cols = len(line)
        for col, ch in enumerate(line):
            if ch == " ":
                widget.insert(tk.END, ch)
            else:
                hex_c = ascii_colors.tk_color_at(preset, col, cols, row, phase)
                if hex_c not in tags_used:
                    widget.tag_config(hex_c, foreground=hex_c)
                    tags_used.add(hex_c)
                widget.insert(tk.END, ch, hex_c)
    widget.configure(state=tk.DISABLED)


class FigletTab(ttk.Frame):
    def __init__(self, master, font_names, font_paths, status_cb, fonts_updated_cb=None):
        super().__init__(master)
        self._font_names = font_names
        self._font_paths = font_paths
        self._status_cb = status_cb
        self._fonts_updated_cb = fonts_updated_cb
        self._debounce_id = None
        self._picker_debounce_id = None
        self._phase = 0.0
        self._anim_job = None
        self._plain_art = ""

        default = DEFAULT_FONT if DEFAULT_FONT in font_paths else font_names[0]
        self._font_var = tk.StringVar(value=default)
        self._font_filter_var = tk.StringVar()
        self._input_var = tk.StringVar(value="VEXX ASCII")
        self._color_var = tk.StringVar(value="Iridescent (перелив)")
        self._ansi_copy_var = tk.BooleanVar(value=True)

        self._build()
        self._apply_font_filter()
        self._refresh()
        self._start_animation()

    def _build(self):
        bar1 = ttk.Frame(self, padding=8)
        bar1.pack(fill=tk.X)
        ttk.Label(bar1, text="Шрифт:").pack(side=tk.LEFT)
        self._font_combo = ttk.Combobox(
            bar1, textvariable=self._font_var, width=26, state="readonly"
        )
        self._font_combo.pack(side=tk.LEFT, padx=4)
        self._font_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh())
        ttk.Label(bar1, text="Поиск:").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Entry(bar1, textvariable=self._font_filter_var, width=14).pack(side=tk.LEFT, padx=4)
        self._font_filter_var.trace_add("write", lambda *_: self._apply_font_filter())
        self._count_lbl = ttk.Label(bar1, text="")
        self._count_lbl.pack(side=tk.LEFT, padx=8)
        ttk.Button(bar1, text="↓ ALL FIGlet", command=self._download_fonts).pack(side=tk.RIGHT)

        bar2 = ttk.Frame(self, padding=(8, 0, 8, 4))
        bar2.pack(fill=tk.X)
        ttk.Label(bar2, text="Текст:").pack(side=tk.LEFT)
        ttk.Entry(bar2, textvariable=self._input_var, width=36).pack(
            side=tk.LEFT, padx=6, fill=tk.X, expand=True
        )
        self._input_var.trace_add("write", lambda *_: self._schedule_refresh())
        self._input_var.trace_add("write", lambda *_: self._schedule_picker())
        ttk.Label(bar2, text="Цвет:").pack(side=tk.LEFT, padx=(8, 0))
        cb = ttk.Combobox(
            bar2, textvariable=self._color_var, values=ascii_colors.COLOR_PRESETS,
            width=28, state="readonly",
        )
        cb.pack(side=tk.LEFT, padx=4)
        self._color_var.trace_add("write", lambda *_: self._on_color_change())
        ttk.Checkbutton(bar2, text="ANSI в буфер", variable=self._ansi_copy_var).pack(
            side=tk.LEFT, padx=8
        )

        bar3 = ttk.Frame(self, padding=(8, 0, 8, 6))
        bar3.pack(fill=tk.X)
        ttk.Button(bar3, text="Копировать", command=self._copy).pack(side=tk.LEFT, padx=2)
        ttk.Button(bar3, text="Копировать + ascii_out.txt", command=self._copy_save).pack(
            side=tk.LEFT, padx=2
        )

        body = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        picker_wrap = ttk.LabelFrame(body, text="Шрифты — превью", padding=4)
        body.add(picker_wrap, weight=0)
        self._font_picker = ascii_font_picker.VisualFontPicker(
            picker_wrap,
            self._font_var,
            on_selected=self._refresh,
            sample_fn=lambda: self._input_var.get().strip() or "TEST",
        )
        self._font_picker.pack(fill=tk.BOTH, expand=True)
        self._font_picker.set_paths(self._font_paths)

        preview_wrap = ttk.Frame(body)
        body.add(preview_wrap, weight=1)
        self._preview = self._make_preview(preview_wrap)
        ttk.Label(
            preview_wrap,
            text="Большой превью · truecolor · комбо + клик по карточке.",
            wraplength=560,
        ).pack(fill=tk.X, padx=6, pady=(0, 4))

    def _make_preview(self, parent):
        frame = ttk.Frame(parent, padding=(6, 0, 10, 10))
        frame.pack(fill=tk.BOTH, expand=True)
        mono = tkfont.Font(family="Consolas", size=9)
        preview = tk.Text(
            frame, wrap=tk.NONE, font=mono, borderwidth=0, padx=8, pady=8,
        )
        studio_theme.style_text_widget(preview)
        sy = studio_chrome.themed_scrollbar(frame, orient=tk.VERTICAL, command=preview.yview)
        sx = studio_chrome.themed_scrollbar(frame, orient=tk.HORIZONTAL, command=preview.xview)
        preview.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        preview.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return preview

    def reload_fonts(self, names, paths):
        self._font_names, self._font_paths = names, paths
        self._font_picker.set_paths(paths)
        self._apply_font_filter()
        self._refresh()

    def _apply_font_filter(self):
        q = self._font_filter_var.get().strip().lower()
        filtered = [f for f in self._font_names if q in f.lower()] if q else self._font_names
        self._font_combo["values"] = filtered
        self._count_lbl.config(text=f"{len(filtered)} / {len(self._font_names)} шрифтов")
        if filtered and self._font_var.get() not in filtered:
            self._font_var.set(filtered[0])
        self._font_picker.schedule_rebuild(filtered, len(self._font_names))

    def _on_color_change(self):
        self._refresh()
        self._start_animation()

    def _start_animation(self):
        if self._anim_job:
            self.master.after_cancel(self._anim_job)
            self._anim_job = None
        if self._color_var.get() in ascii_colors.animated_presets():
            self._tick_animation()
        else:
            self._phase = 0.0

    def _tick_animation(self):
        self._phase += 0.04
        _paint_colored_text(
            self._preview, self._plain_art, self._color_var.get(), self._phase
        )
        self._anim_job = self.master.after(75, self._tick_animation)

    def _schedule_picker(self):
        if self._picker_debounce_id:
            self.master.after_cancel(self._picker_debounce_id)
        q = self._font_filter_var.get().strip().lower()
        filtered = [f for f in self._font_names if q in f.lower()] if q else self._font_names

        def go():
            self._picker_debounce_id = None
            self._font_picker.schedule_rebuild(filtered, len(self._font_names))

        self._picker_debounce_id = self.master.after(350, go)

    def _schedule_refresh(self):
        if self._debounce_id:
            self.master.after_cancel(self._debounce_id)
        self._debounce_id = self.master.after(100, self._refresh)

    def _refresh(self):
        self._debounce_id = None
        self._plain_art = ascii_fonts.render_figlet(
            self._input_var.get(), self._font_var.get(), self._font_paths, width=PREVIEW_WIDTH
        )
        _paint_colored_text(
            self._preview, self._plain_art, self._color_var.get(), self._phase
        )

    def _export(self) -> str:
        if self._ansi_copy_var.get() and self._color_var.get() != "Без цвета":
            return ascii_colors.colorize_ascii(
                self._plain_art, self._color_var.get(), self._phase
            )
        return self._plain_art

    def _copy(self):
        text = self._export()
        if not text.strip():
            return
        root = self.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(text)
        self._status_cb("Скопировано (FIGlet)")

    def _copy_save(self):
        text = self._export()
        if not text.strip():
            return
        root = self.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(text)
        path = ascii_fonts.ROOT / "ascii_out.txt"
        path.write_text(text, encoding="utf-8")
        self._status_cb(f"Сохранено {path}")

    def _download_fonts(self):
        self._status_cb("Качаю шрифты…")

        def work():
            def progress(text: str):
                self.master.after(0, lambda t=text: self._status_cb(t))

            try:
                _total, msg = ascii_fonts.download_full_figlet_bundle(progress)
                names, paths = ascii_fonts.font_registry(rebuild=True)
                self.master.after(0, lambda: self._finish_dl(names, paths, msg))
            except Exception as e:
                err = f"{type(e).__name__}: {e}" if str(e).strip() else type(e).__name__
                self.master.after(0, lambda m=err: messagebox.showerror("Ошибка", m))

        threading.Thread(target=work, daemon=True).start()

    def _finish_dl(self, names, paths, msg):
        self.reload_fonts(names, paths)
        if self._fonts_updated_cb:
            self._fonts_updated_cb(names, paths)
        messagebox.showinfo("Шрифты", msg)


class TerminalTab(ttk.Frame):
    def __init__(self, master, font_names, font_paths, status_cb):
        super().__init__(master)
        self._font_names = font_names
        self._font_paths = font_paths
        self._status_cb = status_cb
        self._font_var = tk.StringVar(value="slant")
        self._phase = 0.0
        self._anim_job = None
        self._plain = ""
        self._preset = "Iridescent (перелив)"
        self._ansi_var = tk.BooleanVar(value=True)
        self._debounce_id = None
        self._picker_debounce_id = None
        self._sync_font = False
        initial = ascii_terminal.DEFAULT_DSL
        if EXAMPLE_PATH.is_file():
            try:
                initial = EXAMPLE_PATH.read_text(encoding="utf-8")
            except OSError:
                pass

        self._template_var = tk.StringVar(value="full_classic")
        self._sync_template = False

        self._build(initial)
        self._refresh()
        self._start_animation()

    def _build(self, initial: str):
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Пример", command=self._load_example).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Открыть…", command=self._open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Сохранить…", command=self._save_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="Копировать ANSI", command=self._copy).pack(side=tk.LEFT, padx=8)
        ttk.Checkbutton(top, text="ANSI", variable=self._ansi_var).pack(side=tk.LEFT)
        ttk.Label(top, text="  Цвет:").pack(side=tk.LEFT, padx=(12, 0))
        self._preset_var = tk.StringVar(value="Iridescent (перелив)")
        pc = ttk.Combobox(
            top,
            textvariable=self._preset_var,
            values=ascii_colors.COLOR_PRESETS,
            width=28,
            state="readonly",
        )
        pc.pack(side=tk.LEFT, padx=4)
        pc.bind("<<ComboboxSelected>>", lambda e: self._apply_preset_to_dsl())

        paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        left_col = ttk.Frame(paned)
        paned.add(left_col, weight=1)

        left = ttk.Frame(left_col)
        left.pack(fill=tk.BOTH, expand=True)
        ttk.Label(left, text="DSL — баннер, layout, prompt:").pack(anchor=tk.W)
        mono = tkfont.Font(family="Consolas", size=9)
        self._editor = tk.Text(left, font=mono, height=10, wrap=tk.NONE, undo=True)
        self._editor.pack(fill=tk.BOTH, expand=True)
        self._editor.insert("1.0", initial)
        self._editor.bind("<KeyRelease>", lambda e: self._schedule_refresh())

        pick_nb = ttk.Notebook(left_col)
        pick_nb.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        tab_font = ttk.Frame(pick_nb, padding=4)
        pick_nb.add(tab_font, text="Шрифты")
        self._font_picker = ascii_font_picker.VisualFontPicker(
            tab_font,
            self._font_var,
            on_selected=self._apply_font_to_dsl,
            sample_fn=self._banner_sample,
            canvas_height=260,
        )
        self._font_picker.pack(fill=tk.BOTH, expand=True)
        self._font_picker.set_paths(self._font_paths)

        tab_vis = ttk.Frame(pick_nb, padding=4)
        pick_nb.add(tab_vis, text="Шаблоны · всё")
        self._layout_picker = ascii_visual_picker.VisualLayoutPicker(
            tab_vis,
            self._template_var,
            on_selected=self._apply_visual_template,
            font_paths=self._font_paths,
            canvas_height=340,
        )
        self._layout_picker.pack(fill=tk.BOTH, expand=True)
        self._layout_picker.schedule_rebuild()

        prev_frame = ttk.Frame(paned)
        paned.add(prev_frame, weight=2)
        ttk.Label(prev_frame, text="Превью (как в консоли):").pack(anchor=tk.W)
        self._preview = tk.Text(
            prev_frame, wrap=tk.NONE, font=mono, borderwidth=0, padx=8, pady=8,
        )
        studio_theme.style_text_widget(self._preview)
        sy = studio_chrome.themed_scrollbar(prev_frame, orient=tk.VERTICAL, command=self._preview.yview)
        self._preview.configure(yscrollcommand=sy.set)
        self._preview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sy.pack(side=tk.RIGHT, fill=tk.Y)

        n_styles = len(ascii_terminal.list_table_styles())
        n_tpl = len(ascii_terminal_templates.filter_templates("Все", "", True))
        help_txt = (
            "Ключи: banner, font, preset, center, meta, prompt. "
            "Блоки: [menu], [table], [list], [box]. "
            f"Вкладка «Шаблоны · всё»: {n_tpl} карточек (экраны, меню, дашборды, {n_styles} рамок)."
        )
        ttk.Label(self, text=help_txt, wraplength=980).pack(fill=tk.X, padx=10, pady=(0, 8))
        self._font_picker.schedule_rebuild(self._font_names[:], len(self._font_names))

    def _apply_visual_template(self) -> None:
        if self._sync_template:
            return
        tid = self._template_var.get().strip()
        t = ascii_terminal_templates.get_template(tid)
        if not t:
            return
        text = self._editor.get("1.0", tk.END)
        if t.id.startswith("border:"):
            text = ascii_terminal.apply_border_only_to_dsl(text, t.style)
        else:
            text = ascii_terminal.apply_template_body_to_dsl(text, t.body)
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", text)
        self._schedule_refresh()

    def _banner_sample(self) -> str:
        spec = ascii_terminal.parse_terminal_dsl(self._dsl())
        return (spec.banner or "TEST")[:24]

    def _apply_font_to_dsl(self) -> None:
        name = self._font_var.get()
        text = self._editor.get("1.0", tk.END)
        if re.search(r"^font\s*:", text, re.M | re.I):
            text = re.sub(
                r"^font\s*:.*$",
                f"font: {name}",
                text,
                count=1,
                flags=re.M | re.I,
            )
        else:
            text = re.sub(
                r"^(banner\s*:.*)$",
                rf"\1\nfont: {name}",
                text,
                count=1,
                flags=re.M | re.I,
            )
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", text)
        self._schedule_refresh()

    def _apply_preset_to_dsl(self) -> None:
        preset = self._preset_var.get()
        text = self._editor.get("1.0", tk.END)
        if re.search(r"^preset\s*:", text, re.M | re.I):
            text = re.sub(
                r"^preset\s*:.*$",
                f"preset: {preset}",
                text,
                count=1,
                flags=re.M | re.I,
            )
        else:
            text = re.sub(
                r"^(font\s*:.*)$",
                rf"\1\npreset: {preset}",
                text,
                count=1,
                flags=re.M | re.I,
            )
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", text)
        self._schedule_refresh()

    def reload_fonts(self, names, paths):
        self._font_names = names
        self._font_paths = paths
        self._font_picker.set_paths(paths)
        self._layout_picker.set_paths(paths)
        self._font_picker.schedule_rebuild(names, len(names))
        self._layout_picker.schedule_rebuild()
        self._refresh()

    def _dsl(self) -> str:
        return self._editor.get("1.0", tk.END)

    def _schedule_refresh(self):
        if self._debounce_id:
            self.master.after_cancel(self._debounce_id)
        self._debounce_id = self.master.after(120, self._refresh)

    def _refresh(self):
        self._debounce_id = None
        dsl = self._dsl()
        spec = ascii_terminal.parse_terminal_dsl(dsl)
        self._preset = spec.preset
        if self._preset_var.get() != spec.preset:
            self._preset_var.set(spec.preset)
        if not self._sync_font and self._font_var.get() != spec.font:
            self._sync_font = True
            self._font_var.set(spec.font)
            self._sync_font = False
        self._plain = ascii_terminal.render_terminal_plain(dsl, self._font_paths)
        _paint_colored_text(self._preview, self._plain, self._preset, self._phase)
        self._start_animation()

    def _start_animation(self):
        if self._anim_job:
            self.master.after_cancel(self._anim_job)
            self._anim_job = None
        if self._preset in ascii_colors.animated_presets():
            self._tick()

    def _tick(self):
        self._phase += 0.04
        _paint_colored_text(self._preview, self._plain, self._preset, self._phase)
        self._anim_job = self.master.after(75, self._tick)

    def _export(self) -> str:
        _, colored = ascii_terminal.render_terminal(
            self._dsl(), self._font_paths, self._phase, ansi=self._ansi_var.get()
        )
        return colored

    def _copy(self):
        text = self._export()
        if not text.strip():
            return
        root = self.winfo_toplevel()
        root.clipboard_clear()
        root.clipboard_append(text)
        self._status_cb("Скопировано (Terminal UI)")

    def _load_example(self):
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", ascii_terminal.DEFAULT_DSL)
        self._refresh()

    def _open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("Terminal UI", "*.txt"), ("All", "*.*")]
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            messagebox.showerror("Ошибка", str(e))
            return
        self._editor.delete("1.0", tk.END)
        self._editor.insert("1.0", text)
        self._refresh()

    def _save_file(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile="terminal_ui.txt",
            filetypes=[("Terminal UI", "*.txt")],
        )
        if not path:
            return
        try:
            Path(path).write_text(self._dsl(), encoding="utf-8")
            self._status_cb(f"Сохранено {path}")
        except OSError as e:
            messagebox.showerror("Ошибка", str(e))


def main():
    from vexx_cloner_app import main as run_app

    run_app(initial_tab="figlet")


if __name__ == "__main__":
    main()
