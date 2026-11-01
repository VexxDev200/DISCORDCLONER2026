#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Готовые визуальные шаблоны Terminal UI — меню, таблицы, дашборды, микс."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import ascii_table_styles


@dataclass(frozen=True)
class VisualTemplate:
    id: str
    title: str
    category: str
    body: str
    style: str = "double"
    tags: tuple = ()
    blurb: str = ""


CATEGORIES: tuple = (
    "Все",
    "Полные экраны",
    "Меню",
    "Таблицы",
    "Списки",
    "Боксы",
    "Дашборд",
    "Рамки",
)


def _menu2(
    style: str,
    left_title: str,
    right_title: str,
    gap: int = 3,
    items: int = 3,
) -> str:
    def col(title: str, start: int) -> str:
        lines = [f"-- {title} --"]
        for i in range(items):
            n = start + i
            lines.append(f"{n} | Пункт {n}")
        return "\n".join(lines)

    return f"""[menu columns=2 style={style} gap={gap}]
{col(left_title, 1)}
{col(right_title, items + 1)}
[/menu]"""


def _list_block(style: str, n: int = 5) -> str:
    lines = "\n".join(f"{i} | Строка {i}" for i in range(1, n + 1))
    return f"[list style={style}]\n{lines}\n0 | Назад\n[/list]"


def _table_block(style: str, title: str = "Статус") -> str:
    return f"""[table style={style} title={title}]
Ключ | Значение
CPU | 12%
RAM | 4.2 GB
Ping | 24 ms
[/table]"""


def _box_block(style: str, title: str = "INFO") -> str:
    return f"""[box style={style} title={title}]
Сообщение системы
Строка два
[/box]"""


TEMPLATES: List[VisualTemplate] = [
    VisualTemplate(
        "full_classic",
        "Классика VEXX",
        "Полные экраны",
        """center: VEXX TERMINAL
meta: · · ·

""" + _menu2("double", "МОДУЛЬ A", "МОДУЛЬ B")
        + "\n\n"
        + _table_block("double", "METRICS")
        + "\n\n"
        + _list_block("single", 4),
        "double",
        ("full", "demo", "menu", "table"),
        "Баннер + 2 меню + таблица + список",
    ),
    VisualTemplate(
        "full_cyber",
        "Cyber deck",
        "Полные экраны",
        """center: ◈ NEURAL LINK ◈
meta: uplink stable · latency 18ms

"""
        + _menu2("cyber", "EXPLOIT", "PAYLOAD", gap=4)
        + "\n\n"
        + _box_block("cyber", "LOG")
        + "\n\n"
        + _list_block("cyber", 3),
        "cyber",
        ("cyber", "hacker"),
    ),
    VisualTemplate(
        "full_retro",
        "Retro CRT",
        "Полные экраны",
        """center: RETRO//OS
meta: boot ok

"""
        + _menu2("retro", "DISK", "NET")
        + "\n\n"
        + _table_block("ascii", "DRIVES"),
        "retro",
        ("retro", "8bit"),
    ),
    VisualTemplate(
        "full_minimal",
        "Minimal flat",
        "Полные экраны",
        """meta: 

"""
        + _list_block("markdown", 6)
        + "\n\n"
        + _table_block("minimal", ""),
        "markdown",
        ("clean", "flat"),
    ),
    VisualTemplate(
        "full_stars",
        "Star frame",
        "Полные экраны",
        """center: ★ LOBBY ★

"""
        + _menu2("stars", "PLAY", "SHOP", gap=5)
        + "\n\n"
        + _box_block("stars", "NEWS"),
        "stars",
        ("game", "fancy"),
    ),
    VisualTemplate(
        "menu_dual_heavy",
        "2 колонки · heavy",
        "Меню",
        _menu2("heavy", "ATTACK", "DEFENSE", gap=4, items=4),
        "heavy",
        ("2col", "pvp"),
    ),
    VisualTemplate(
        "menu_dual_round",
        "2 колонки · rounded",
        "Меню",
        _menu2("rounded", "CREATE", "JOIN", gap=3, items=5),
        "rounded",
        ("2col", "soft"),
    ),
    VisualTemplate(
        "menu_dual_ascii",
        "2 колонки · ASCII",
        "Меню",
        _menu2("ascii", "TOOLS", "CONFIG", items=6),
        "ascii",
        ("2col", "classic"),
    ),
    VisualTemplate(
        "menu_triple",
        "3 колонки",
        "Меню",
        """[menu columns=3 style=single gap=2]
-- A --
1 | Alpha
2 | Beta
-- B --
3 | Gamma
4 | Delta
-- C --
5 | Epsilon
6 | Zeta
[/menu]""",
        "single",
        ("3col",),
    ),
    VisualTemplate(
        "menu_wide_single",
        "1 широкая колонка",
        "Меню",
        """[menu columns=1 style=double gap=0]
-- ГЛАВНОЕ МЕНЮ --
1 | Запуск
2 | Настройки
3 | Профиль
4 | Выход
[/menu]""",
        "double",
        ("1col",),
    ),
    VisualTemplate(
        "menu_hash",
        "Hash меню",
        "Меню",
        _menu2("hash", "DEV", "PROD", items=4),
        "hash",
        ("dev",),
    ),
    VisualTemplate(
        "menu_arrows",
        "Arrows меню",
        "Меню",
        _menu2("arrows", "UP", "DOWN", gap=6, items=3),
        "arrows",
    ),
    VisualTemplate(
        "table_stats",
        "Таблица метрик",
        "Таблицы",
        _table_block("double", "SERVER"),
        "double",
    ),
    VisualTemplate(
        "table_heavy",
        "Heavy таблица",
        "Таблицы",
        """[table style=heavy title=INVENTORY]
Slot | Item | Qty
01 | Keycard | 1
02 | Medkit | 3
03 | Ammo | 120
[/table]""",
        "heavy",
    ),
    VisualTemplate(
        "table_equals",
        "Equals grid",
        "Таблицы",
        """[table style=equals title=SCOREBOARD]
# | Name | PTS
1 | ACE | 9999
2 | NOVA | 8420
3 | VEXX | 8011
[/table]""",
        "equals",
    ),
    VisualTemplate(
        "table_markdown",
        "Markdown table",
        "Таблицы",
        """[table style=markdown title=CHANGELOG]
Ver | Note
2.1 | UI refresh
2.0 | Templates
[/table]""",
        "markdown",
    ),
    VisualTemplate(
        "table_wide",
        "Wide 4 col",
        "Таблицы",
        """[table style=light title=MATRIX]
A | B | C | D
ok | ok | warn | ok
fail | ok | ok | ok
[/table]""",
        "light",
    ),
    VisualTemplate(
        "list_selector",
        "Список выбора",
        "Списки",
        _list_block("single", 8),
        "single",
    ),
    VisualTemplate(
        "list_heavy",
        "Heavy list",
        "Списки",
        _list_block("heavy", 5),
        "heavy",
    ),
    VisualTemplate(
        "list_dots",
        "Dots list",
        "Списки",
        _list_block("dots", 6),
        "dots",
    ),
    VisualTemplate(
        "box_alert",
        "Alert box",
        "Боксы",
        _box_block("heavy", "WARNING"),
        "heavy",
    ),
    VisualTemplate(
        "box_double",
        "Double box",
        "Боксы",
        """[box style=double title=README]
Первая строка
Вторая строка
Третья строка
[/box]""",
        "double",
    ),
    VisualTemplate(
        "box_shade",
        "Shade panel",
        "Боксы",
        _box_block("shade", "PANEL"),
        "shade",
    ),
    VisualTemplate(
        "dash_ops",
        "Ops dashboard",
        "Дашборд",
        """[menu columns=2 style=horiz_heavy gap=3]
-- QUEUE --
1 | Job A
2 | Job B
-- ALERTS --
3 | Warn
4 | OK
[/menu]

"""
        + _table_block("single", "NODES")
        + "\n\n"
        + _box_block("single", "TIP"),
        "horiz_heavy",
        ("mix", "admin"),
    ),
    VisualTemplate(
        "dash_shop",
        "Shop layout",
        "Дашборд",
        _menu2("stars", "BUY", "SELL", gap=4, items=4)
        + "\n\n"
        + _table_block("rounded", "PRICES"),
        "stars",
        ("shop",),
    ),
    VisualTemplate(
        "dash_clone",
        "Clone portal",
        "Дашборд",
        """center: DISCORD CLONER
meta: token ready · guild sync

"""
        + _menu2("double", "SOURCE", "TARGET", items=3)
        + "\n\n"
        + """[box style=double title=STATUS]
Ожидание /clone
[/box]""",
        "double",
        ("discord",),
    ),
    VisualTemplate(
        "dash_stack",
        "Vertical stack",
        "Дашборд",
        """[menu columns=1 style=light gap=0]
-- STEP 1 --
1 | Auth
[/menu]

[menu columns=1 style=light gap=0]
-- STEP 2 --
2 | Select
[/menu]

"""
        + _list_block("light", 3),
        "light",
        ("wizard",),
    ),
    VisualTemplate(
        "mix_table_list",
        "Table + list",
        "Дашборд",
        _table_block("double_single", "DATA")
        + "\n\n"
        + _list_block("double_single", 4),
        "double_single",
    ),
]


def _border_templates() -> List[VisualTemplate]:
    out: List[VisualTemplate] = []
    for name in ascii_table_styles.style_names():
        preview_body = (
            _menu2(name, "A", "B", items=2)
            + "\n\n"
            + _table_block(name, "TEST")
        )
        out.append(
            VisualTemplate(
                f"border:{name}",
                name,
                "Рамки",
                preview_body,
                name,
                ("border", "style"),
                "Только стиль рамки на текущем DSL",
            )
        )
    return out


_ALL: Optional[List[VisualTemplate]] = None


def all_templates(include_borders: bool = True) -> List[VisualTemplate]:
    global _ALL
    if _ALL is None:
        _ALL = list(TEMPLATES)
    if include_borders:
        return _ALL + _border_templates()
    return list(_ALL)


def get_template(tid: str) -> Optional[VisualTemplate]:
    for t in all_templates(True):
        if t.id == tid:
            return t
    return None


def filter_templates(
    category: str = "Все",
    query: str = "",
    include_borders: bool = True,
) -> List[VisualTemplate]:
    q = (query or "").strip().lower()
    cat = category or "Все"
    items = all_templates(include_borders)
    out: List[VisualTemplate] = []
    for t in items:
        if cat != "Все" and t.category != cat:
            continue
        if q:
            hay = " ".join(
                [t.id, t.title, t.category, t.style, t.blurb, " ".join(t.tags)]
            ).lower()
            if q not in hay:
                continue
        out.append(t)
    return out


FEATURED_IDS = (
    "full_classic",
    "full_cyber",
    "menu_dual_heavy",
    "menu_triple",
    "dash_clone",
    "dash_ops",
    "border:double",
    "border:heavy",
    "border:rounded",
    "border:cyber",
    "border:ascii",
)
