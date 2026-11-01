#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Консольный выбор: Vexx Cloner (консоль) или Vexx ASCII (окно)."""

from __future__ import annotations

import os
import subprocess
import sys

import app_paths
import vexx_version


def _fix_console():
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def _print_menu():
    print()
    print("  ╔══════════════════════════════════════════╗")
    print("  ║           VEXX · выбор режима            ║")
    print("  ╠══════════════════════════════════════════╣")
    print(f"  ║  версия {vexx_version.__version__:<29}║")
    print("  ╠══════════════════════════════════════════╣")
    print("  ║  1  Discord Cloner  (консоль, клон)    ║")
    print("  ║  2  Vexx ASCII      (окно, баннеры)    ║")
    print("  ║  0  Выход                              ║")
    print("  ╚══════════════════════════════════════════╝")
    print()


def _run_cloner() -> None:
    try:
        import vexx_updater

        vexx_updater.ensure_config_from_example()
        vexx_updater.startup_auto_update([vexx_version.PRODUCT_CLONER])
    except Exception:
        pass
    from discordcloner import main as cloner_main

    cloner_main()


def _run_ascii_gui() -> None:
    root = app_paths.app_dir()
    script = os.path.join(root, "vexx_cloner_app.py")
    tab = "figlet"
    py = sys.executable
    pyw = os.path.join(os.path.dirname(py), "pythonw.exe")
    runner = pyw if sys.platform == "win32" and os.path.isfile(pyw) else py
    flags = 0
    if sys.platform == "win32" and runner.lower().endswith("pythonw.exe"):
        flags = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
    try:
        subprocess.Popen(
            [runner, script, tab],
            cwd=root,
            creationflags=flags,
            close_fds=False,
        )
        print("\n  Vexx ASCII запущен.\n")
    except OSError as e:
        print(f"\n  Ошибка запуска ASCII: {e}\n")
        from vexx_cloner_app import main as ascii_main

        ascii_main(initial_tab=tab)


def main() -> None:
    _fix_console()
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().lower()
        if arg in ("1", "cloner", "clone"):
            _run_cloner()
            return
        if arg in ("2", "ascii", "studio"):
            _run_ascii_gui()
            return

    while True:
        _print_menu()
        choice = input("  ▶ ").strip().lower()
        if choice in ("0", "q", "exit", "выход"):
            break
        if choice in ("1", "cloner", "clone", "клонер"):
            _run_cloner()
            break
        if choice in ("2", "ascii", "studio", "аски"):
            _run_ascii_gui()
            break
        print("  Неверный выбор.\n")


if __name__ == "__main__":
    main()
