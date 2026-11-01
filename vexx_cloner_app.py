#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vexx ASCII — FIGlet + Terminal UI (без клонера в окне)."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox, ttk

import ascii_fonts
import studio_brand
import studio_chrome
import studio_theme
import vexx_version

from ascii_studio import FigletTab, TerminalTab


class VexxAsciiApp(tk.Tk):
    def __init__(self, initial_tab: str = "figlet"):
        super().__init__()
        studio_brand.apply_window_icon(self)
        self.minsize(960, 620)
        self.geometry("1180x780")

        self._body, _style = studio_chrome.install_window_chrome(self, "Vexx ASCII")
        parent = self._body

        try:
            import vexx_updater

            vexx_updater.ensure_config_from_example()
            vexx_updater.startup_auto_update([vexx_version.PRODUCT_ASCII])
        except Exception:
            pass

        self._build_menu()

        if ascii_fonts.figlet_format is None:
            messagebox.showerror(
                "Vexx ASCII",
                "Нужен pyfiglet:\npip install pyfiglet Pillow",
            )
            self.destroy()
            return

        self._font_names, self._font_paths = ascii_fonts.font_registry()

        self._status = ttk.Label(parent, text="", padding=(8, 4))
        self._status.pack(side=tk.BOTTOM, fill=tk.X)
        try:
            self._status.configure(background=studio_theme.THEME["status_bg"])
        except tk.TclError:
            pass

        nb = ttk.Notebook(parent)
        nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        self._figlet = FigletTab(
            nb, self._font_names, self._font_paths, self._set_status, self._on_fonts_updated
        )
        nb.add(self._figlet, text="FIGlet · ASCII")

        self._terminal = TerminalTab(
            nb, self._font_names, self._font_paths, self._set_status
        )
        nb.add(self._terminal, text="Terminal UI")

        tabs = {"figlet": 0, "ascii": 0, "terminal": 1}
        nb.select(tabs.get(initial_tab.lower(), 0))

    def _build_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        m = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Vexx", menu=m)
        studio_chrome.style_menubar(menubar)
        studio_chrome.style_menubar(m)
        m.add_command(label="Проверить обновления", command=self._check_updates)
        m.add_command(label="Установить обновления", command=self._apply_updates)
        m.add_separator()
        m.add_command(label=f"Версия {vexx_version.__version__}", state=tk.DISABLED)

    def _check_updates(self):
        try:
            import vexx_updater

            rep = vexx_updater.check_updates([vexx_version.PRODUCT_ASCII], force=True)
            messagebox.showinfo("Vexx Update", vexx_updater.format_report(rep))
        except Exception as e:
            messagebox.showerror("Vexx Update", str(e))

    def _apply_updates(self):
        try:
            import vexx_updater

            if not messagebox.askyesno(
                "Vexx Update",
                "Скачать обновление Vexx ASCII?\nПерезапусти программу после установки.",
            ):
                return
            rep = vexx_updater.apply_updates([vexx_version.PRODUCT_ASCII])
            messagebox.showinfo("Vexx Update", vexx_updater.format_report(rep))
        except Exception as e:
            messagebox.showerror("Vexx Update", str(e))

    def _on_fonts_updated(self, names, paths):
        self._font_names = names
        self._font_paths = paths
        self._terminal.reload_fonts(names, paths)

    def _set_status(self, msg: str):
        self._status.config(text=msg)


def main(initial_tab: str = "figlet"):
    if ascii_fonts.figlet_format is None:
        print("pip install pyfiglet Pillow")
        sys.exit(1)
    app = VexxAsciiApp(initial_tab=initial_tab)
    if app.winfo_exists():
        app.mainloop()


# совместимость
VexxClonerApp = VexxAsciiApp


if __name__ == "__main__":
    tab = "figlet"
    if len(sys.argv) > 1:
        tab = sys.argv[1]
    main(initial_tab=tab)
