#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Конструктор CLI: баннер FIGlet, таблицы, меню-колонки, списки выбора."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

import ascii_colors
import ascii_fonts
import ascii_table_styles

BOX = ascii_table_styles.TABLE_STYLES

DEFAULT_DSL = """banner: VEXX ASCII
font: slant
preset: Iridescent (перелив)
center: TEST
meta: TEST · TEST · TEST

[menu columns=2 style=double gap=3]
-- TEST --
1 | TEST
2 | TEST
3 | TEST
-- TEST --
4 | TEST
5 | TEST
6 | TEST
[/menu]

[table style=double title=TEST]
TEST | TEST
TEST | TEST
TEST | TEST
[/table]

[list style=single]
1 | TEST
2 | TEST
3 | TEST
0 | TEST
[/list]

prompt: [+] TEST ->
"""


@dataclass
class TerminalSpec:
    banner: str = "VEXX ASCII"
    font: str = "slant"
    preset: str = "Iridescent (перелив)"
    center: str = ""
    meta_lines: List[str] = field(default_factory=list)
    blocks: List[dict] = field(default_factory=list)
    prompt: str = "[+] Выберите ->"


def _display_width(s: str) -> int:
    return len(s)


def _pad(s: str, width: int) -> str:
    w = _display_width(s)
    if w >= width:
        return s[:width]
    return s + " " * (width - w)


def _center_line(text: str, width: int) -> str:
    w = _display_width(text)
    if w >= width:
        return text[:width]
    left = (width - w) // 2
    return " " * left + text + " " * (width - left - w)


def _box_lines(
    title: Optional[str],
    body_lines: List[str],
    style: str = "double",
    min_inner: int = 20,
) -> List[str]:
    b = BOX.get(style, BOX["double"])
    inner = min_inner
    for ln in body_lines:
        inner = max(inner, _display_width(ln))
    if title:
        inner = max(inner, _display_width(title) + 2)

    top = b["tl"] + b["h"] * (inner + 2) + b["tr"]
    out = [top]
    if title:
        out.append(b["v"] + " " + _center_line(title, inner) + " " + b["v"])
        out.append(b["lm"] + b["h"] * (inner + 2) + b["rm"])
    for ln in body_lines:
        out.append(b["v"] + " " + _pad(ln, inner) + " " + b["v"])
    out.append(b["bl"] + b["h"] * (inner + 2) + b["br"])
    return out


def _table_lines(
    rows: List[List[str]],
    style: str = "double",
    title: Optional[str] = None,
) -> List[str]:
    if not rows:
        return []
    b = BOX.get(style, BOX["double"])
    cols = len(rows[0])
    widths = [0] * cols
    for row in rows:
        for i, cell in enumerate(row[:cols]):
            widths[i] = max(widths[i], _display_width(cell))

    def fmt_row(cells: List[str]) -> str:
        parts = []
        for i in range(cols):
            c = cells[i] if i < len(cells) else ""
            parts.append(_pad(c, widths[i]))
        return b["v"] + " " + " │ ".join(parts) + " " + b["v"]

    inner_w = sum(widths) + 3 * (cols - 1)
    top = b["tl"] + b["h"] * (inner_w + 2) + b["tr"]
    mid = b["lm"] + b["h"] * (inner_w + 2) + b["rm"]
    bot = b["bl"] + b["h"] * (inner_w + 2) + b["br"]
    out = [top]
    if title:
        out.append(b["v"] + " " + _center_line(title, inner_w) + " " + b["v"])
        out.append(mid)
    out.append(fmt_row(rows[0]))
    out.append(mid)
    for row in rows[1:]:
        out.append(fmt_row(row))
    out.append(bot)
    return out


def render_table_preview(
    rows: List[List[str]],
    style: str = "double",
    title: Optional[str] = None,
) -> List[str]:
    return _table_lines(rows, style=style, title=title)


def list_table_styles() -> List[str]:
    return ascii_table_styles.style_names()


def apply_style_to_dsl(text: str, style: str) -> str:
    """Подставить style= во все блоки menu/table/list/box."""
    style = (style or "double").strip()
    block_re = re.compile(
        r"\[(menu|table|list|box)([^\]]*)\]",
        re.IGNORECASE,
    )

    def repl(m: re.Match) -> str:
        kind, attrs = m.group(1), m.group(2) or ""
        if re.search(r"style\s*=", attrs, re.I):
            attrs = re.sub(r"style\s*=\s*\S+", f"style={style}", attrs, flags=re.I)
        else:
            attrs = f" style={style}{attrs}"
        return f"[{kind}{attrs}]"

    return block_re.sub(repl, text)


def split_dsl_sections(text: str) -> Tuple[str, str, str]:
    """header (до блоков), blocks, prompt-строка."""
    m = re.search(r"\[(menu|table|list|box)\b", text, re.I)
    if not m:
        prompt_m = re.search(r"^prompt\s*:.*$", text, re.M | re.I)
        if prompt_m:
            return text[: prompt_m.start()].rstrip(), "", text[prompt_m.start() :].strip()
        return text.rstrip(), "", ""
    header = text[: m.start()].rstrip()
    rest = text[m.start() :]
    prompt_m = re.search(r"^prompt\s*:.*$", rest, re.M | re.I)
    if prompt_m:
        blocks = rest[: prompt_m.start()].strip()
        prompt = rest[prompt_m.start() :].strip()
    else:
        blocks = rest.strip()
        prompt = ""
    return header, blocks, prompt


def merge_dsl_sections(header: str, blocks: str, prompt: str) -> str:
    parts: List[str] = []
    if header.strip():
        parts.append(header.rstrip())
    if blocks.strip():
        if parts:
            parts.append("")
        parts.append(blocks.strip())
    if prompt.strip():
        if parts:
            parts.append("")
        parts.append(prompt.strip())
    return "\n".join(parts).rstrip() + "\n"


def extract_style_header(text: str) -> str:
    lines: List[str] = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("["):
            break
        if ":" not in s:
            continue
        key = s.split(":", 1)[0].strip().lower()
        if key in ("banner", "font", "preset", "color", "colour"):
            lines.append(raw.rstrip())
    return "\n".join(lines)


def apply_template_body_to_dsl(text: str, body: str) -> str:
    """Подставить layout (center, meta, блоки), сохранив banner/font/preset."""
    head = extract_style_header(text)
    _, _, prompt = split_dsl_sections(text)
    if not prompt.strip():
        prompt = "prompt: [+] Выберите ->"
    parts: List[str] = []
    if head.strip():
        parts.append(head.strip())
    if body.strip():
        parts.append("")
        parts.append(body.strip())
    parts.append("")
    parts.append(prompt.strip())
    return "\n".join(parts).rstrip() + "\n"


def apply_border_only_to_dsl(text: str, style: str) -> str:
    return apply_style_to_dsl(text, style)


def _join_columns(blocks: List[List[str]], gap: int) -> List[str]:
    if not blocks:
        return []
    height = max(len(b) for b in blocks)
    widths = [max(_display_width(line) for line in b) if b else 0 for b in blocks]
    out = []
    g = " " * gap
    for row in range(height):
        parts = []
        for bi, block in enumerate(blocks):
            line = block[row] if row < len(block) else ""
            parts.append(_pad(line, widths[bi]))
        out.append(g.join(parts))
    return out


def _format_menu_item(num: str, text: str) -> str:
    text = text.strip()
    if num.strip():
        return f"[{num.strip()}] {text}"
    return text


def parse_terminal_dsl(text: str) -> TerminalSpec:
    spec = TerminalSpec()
    block_re = re.compile(
        r"\[(menu|table|list|box)([^\]]*)\](.*?)\[/\1\]",
        re.DOTALL | re.IGNORECASE,
    )

    header = text
    for m in block_re.finditer(text):
        header = header.replace(m.group(0), "")

    for raw in header.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip().lower()
        val = val.strip()
        if key == "banner":
            spec.banner = val
        elif key == "font":
            spec.font = val
        elif key in ("preset", "color", "colour"):
            spec.preset = val
        elif key == "center":
            spec.center = val
        elif key == "meta":
            spec.meta_lines.append(val)
        elif key == "prompt":
            spec.prompt = val

    for m in block_re.finditer(text):
        kind = m.group(1).lower()
        attrs = m.group(2) or ""
        body = m.group(3).strip()
        opts = dict(re.findall(r"(\w+)\s*=\s*(\S+)", attrs))
        style = opts.get("style", "double")
        if kind == "menu":
            cols_n = int(opts.get("columns", "2"))
            gap = int(opts.get("gap", "3"))
            columns: List[dict] = []
            current: Optional[dict] = None
            for line in body.splitlines():
                s = line.strip()
                if not s:
                    continue
                if s.startswith("--") and s.endswith("--"):
                    title = s.strip("- ").strip()
                    current = {"title": title, "items": []}
                    columns.append(current)
                    continue
                if "|" in s:
                    num, label = s.split("|", 1)
                    item = _format_menu_item(num, label)
                    if current is None:
                        current = {"title": "", "items": []}
                        columns.append(current)
                    current["items"].append(item)
            spec.blocks.append(
                {"type": "menu", "columns": columns, "cols_n": cols_n, "gap": gap, "style": style}
            )
        elif kind == "table":
            rows = []
            title = opts.get("title")
            for line in body.splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                rows.append([c.strip() for c in s.split("|")])
            spec.blocks.append({"type": "table", "rows": rows, "style": style, "title": title})
        elif kind == "list":
            items = []
            for line in body.splitlines():
                s = line.strip()
                if not s:
                    continue
                if "|" in s:
                    num, label = s.split("|", 1)
                    items.append(_format_menu_item(num, label))
                else:
                    items.append(s)
            spec.blocks.append({"type": "list", "items": items, "style": style})
        elif kind == "box":
            lines = [ln.rstrip() for ln in body.splitlines() if ln.strip()]
            title = opts.get("title")
            spec.blocks.append({"type": "box", "lines": lines, "style": style, "title": title})

    return spec


def render_terminal_plain(
    spec_or_dsl: Union[TerminalSpec, str],
    font_paths: Optional[Dict[str, str]] = None,
    banner_width: int = 100,
) -> str:
    spec = (
        parse_terminal_dsl(spec_or_dsl)
        if isinstance(spec_or_dsl, str)
        else spec_or_dsl
    )
    font_paths = font_paths or {}
    parts: List[str] = []

    art = ascii_fonts.render_figlet(
        spec.banner, spec.font, font_paths, width=banner_width
    )
    if art and not art.startswith("[ошибка"):
        parts.append(art.rstrip())

    canvas_w = max(
        (max(_display_width(l) for l in art.splitlines()) if art else 0),
        60,
    )

    if spec.center:
        parts.append(_center_line(spec.center, canvas_w))
    for meta in spec.meta_lines:
        parts.append(_center_line(meta, canvas_w))

    if parts:
        parts.append("")

    for block in spec.blocks:
        btype = block["type"]
        style = block.get("style", "double")

        if btype == "menu":
            col_boxes: List[List[str]] = []
            for col in block["columns"]:
                title = col.get("title") or ""
                body = col.get("items") or []
                col_boxes.append(_box_lines(title or None, body, style=style, min_inner=18))
            merged = _join_columns(col_boxes, block.get("gap", 3))
            parts.extend(merged)
            parts.append("")

        elif btype == "table":
            rows = block.get("rows") or []
            if rows:
                parts.extend(_table_lines(rows, style=style, title=block.get("title")))
                parts.append("")

        elif btype == "list":
            items = block.get("items") or []
            if items:
                parts.extend(_box_lines(None, items, style=style, min_inner=28))
                parts.append("")

        elif btype == "box":
            lines = block.get("lines") or []
            if lines:
                parts.extend(
                    _box_lines(block.get("title"), lines, style=style, min_inner=24)
                )
                parts.append("")

    if spec.prompt:
        parts.append(spec.prompt)

    while parts and parts[-1] == "":
        parts.pop()
    return "\n".join(parts)


def render_terminal(
    dsl: str,
    font_paths: Optional[Dict[str, str]] = None,
    phase: float = 0.0,
    ansi: bool = True,
) -> Tuple[str, str]:
    """Возвращает (plain, colored)."""
    spec = parse_terminal_dsl(dsl)
    plain = render_terminal_plain(spec, font_paths=font_paths)
    if not ansi or spec.preset in ("", "Без цвета"):
        return plain, plain
    colored = ascii_colors.colorize_ascii(plain, spec.preset, phase)
    return plain, colored
