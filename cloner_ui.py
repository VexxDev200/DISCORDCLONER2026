#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Console UI helpers."""

from colorama import Fore, Style

# Палитра Vexx ASCII (magenta / cyan / pink)
M = Fore.MAGENTA + Style.BRIGHT
C = Fore.CYAN + Style.BRIGHT
P = Fore.LIGHTMAGENTA_EX
Y = Fore.YELLOW + Style.BRIGHT
W = Fore.WHITE
D = Fore.LIGHTBLACK_EX


def hub_title():
    print()
    print(M + "  ╔" + "═" * 58 + "╗" + Style.RESET_ALL)
    print(M + "  ║" + C + "     ⚡ VEXX CLONER · COMMAND DECK ⚡          " + M + "║" + Style.RESET_ALL)
    print(M + "  ╠" + "═" * 58 + "╣" + Style.RESET_ALL)
    print(M + "  ║" + P + "  Neon · Triad · Chimera · Time Machine          " + M + "║" + Style.RESET_ALL)
    print(M + "  ╚" + "═" * 58 + "╝" + Style.RESET_ALL)


def section(title: str):
    print(C + f"\n  ▸ {title}" + Style.RESET_ALL)
    print(D + "  " + "─" * 56 + Style.RESET_ALL)


def progress(label: str, current: int, total: int, width: int = 40):
    if total <= 0:
        return
    filled = int(width * min(current, total) / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = 100.0 * current / total
    print(
        Fore.GREEN + Style.BRIGHT + f"\r  [{bar}] {pct:5.1f}%  {label[:40]}",
        end="",
        flush=True,
    )
    if current >= total:
        print(Style.RESET_ALL)


def menu_hub() -> str:
    hub_title()
    section("Режим")
    print(Y + "  1" + W + "  Полный клон (Triad — выбор стратегии)")
    print(Y + "  2" + W + "  Chimera · 2 source → 1 target")
    print(Y + "  3" + W + "  Time Machine · снимок → target")
    print(Y + "  4" + W + "  Shadow Sync · дельта зеркало")
    print(Y + "  5" + W + "  Anomaly Vault · повтор одной ошибки")
    print(Y + "  6" + W + "  Профиль mappings (Multiverse)")
    print(Y + "  7" + W + "  Обновления Vexx (check / install)")
    print(Y + "  0" + D + "  Выход")
    return input(C + "\n  ▶ " + Style.RESET_ALL).strip()


def pick_triad() -> str:
    section("Triad Run — стратегия")
    print(W + "  1  Surgical — только genome-diff (минимум PATCH)")
    print(W + "  2  Vanilla   — без иконок ролей / gradient (цвета Обычные ✓)")
    print(W + "  3  Hard      — роли+каналы, без emoji/stickers/events")
    return input(Y + "  Стратегия [2]: " + Style.RESET_ALL).strip() or "2"


def show_genome_result(pct: float, seal: str = ""):
    section("Server Genome")
    color = Fore.GREEN if pct >= 90 else Fore.YELLOW if pct >= 70 else Fore.RED
    print(color + Style.BRIGHT + f"  Совпадение структуры: {pct}%" + Style.RESET_ALL)
    if seal:
        print(P + f"  Entropy Seal: {seal}" + Style.RESET_ALL)
