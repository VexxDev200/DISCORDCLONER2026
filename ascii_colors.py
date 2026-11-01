#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ANSI truecolor + пресеты «перелив» как в TAAG Filter."""

import colorsys
import math
from typing import Callable, Dict, List, Set, Tuple

RgbFn = Callable[[float, int, int, int, float], Tuple[int, int, int]]

RESET = "\033[0m"


def _hsv(h: float, s: float, v: float) -> Tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _preset_taag_red(t, _row, _cols, _col, _p):
    return 255, _lerp(80, 120, t), _lerp(80, 120, t)


def _preset_rainbow(t, _row, _cols, _col, p):
    return _hsv(t + p * 0.15, 0.95, 1.0)


def _preset_iridescent(t, row, _cols, _col, p):
    return _hsv(t * 0.7 + row * 0.04 + p, 0.55, 1.0)


def _preset_neon_pulse(t, _row, _cols, _col, p):
    h = 0.78 + 0.08 * math.sin(p * 2 + t * 6)
    return _hsv(h, 1.0, 1.0)


def _preset_fire(t, _row, _cols, _col, _p):
    return 255, int(120 * (1 - t) + 40), int(20 * (1 - t))


def _preset_ocean(t, _row, _cols, _col, _p):
    return int(30 + 80 * t), int(140 + 80 * t), int(200 + 55 * (1 - t))


def _preset_gold(t, _row, _cols, _col, _p):
    return int(200 + 55 * t), int(160 + 60 * t), int(40 + 30 * math.sin(t * math.pi))


def _preset_cyber(t, _row, _cols, _col, p):
    return _hsv(0.48 + t * 0.12 + p * 0.05, 1.0, 1.0)


def _preset_matrix(t, row, _cols, _col, p):
    v = 0.35 + 0.65 * (1 - t) + 0.1 * math.sin(row * 0.5 + p * 3)
    return 0, int(180 * min(1, v)), int(40 * min(1, v))


def _preset_blood(t, _row, _cols, _col, _p):
    return int(120 + 135 * t), int(10 * (1 - t)), int(20 * (1 - t))


def _preset_discord(t, _row, _cols, _col, _p):
    return _lerp(88, 114, t), _lerp(101, 137, t), _lerp(242, 218, t)


def _preset_vaporwave(t, row, _cols, _col, p):
    return _hsv(0.78 + t * 0.08 + row * 0.02, 0.75, 0.95 + 0.05 * math.sin(p + t * 4))


def _preset_sunset(t, _row, _cols, _col, _p):
    return 255, int(80 + 120 * (1 - t)), int(20 + 80 * t)


def _preset_arctic(t, _row, _cols, _col, _p):
    return int(200 + 55 * t), int(230 + 25 * t), 255


def _preset_toxic(t, row, _cols, _col, p):
    return _hsv(0.28 + 0.05 * math.sin(row * 0.3 + p * 2), 1.0, 0.9 + 0.1 * t)


def _preset_sakura(t, _row, _cols, _col, _p):
    return 255, int(180 + 60 * t), int(200 + 40 * (1 - t))


def _preset_lavender(t, _row, _cols, _col, _p):
    return int(180 + 60 * t), int(140 + 80 * t), 255


def _preset_copper(t, _row, _cols, _col, _p):
    return int(180 + 75 * t), int(90 + 50 * t), int(40 + 30 * (1 - t))


def _preset_ice(t, _row, _cols, _col, p):
    return int(180 + 70 * t), int(220 + 30 * t), 255 - int(20 * math.sin(p + t * 5))


def _preset_plasma(t, row, _cols, col, p):
    return _hsv(t * 0.5 + row * 0.03 + col * 0.002 + p * 0.2, 0.9, 1.0)


def _preset_aurora(t, row, _cols, _col, p):
    return _hsv(0.42 + t * 0.25 + row * 0.02 + p * 0.15, 0.65, 0.95)


def _preset_minecraft(t, _row, _cols, _col, _p):
    return int(80 + 40 * t), int(120 + 80 * (1 - t)), int(40 + 30 * t)


def _preset_slime(t, row, _cols, _col, p):
    return _hsv(0.33 + 0.04 * math.sin(row + p * 2), 0.85, 0.85 + 0.15 * t)


def _preset_halloween(t, _row, _cols, _col, _p):
    return int(255 * (1 - t * 0.5)), int(120 * t), 0


def _preset_candy(t, _row, _cols, _col, p):
    return _hsv(0.92 + 0.06 * math.sin(p * 3 + t * 8), 0.8, 1.0)


def _preset_monochrome(t, _row, _cols, _col, _p):
    v = int(80 + 175 * t)
    return v, v, v


def _preset_blue_red(t, _row, _cols, _col, _p):
    if t < 0.5:
        u = t * 2
        return _lerp(40, 80, u), _lerp(80, 40, u), _lerp(220, 200, u)
    u = (t - 0.5) * 2
    return _lerp(200, 255, u), _lerp(40, 60, u), _lerp(60, 80, u)


def _preset_pastel(t, row, _cols, _col, _p):
    return _hsv(0.08 + t * 0.7 + row * 0.01, 0.35, 0.98)


def _preset_deep_sea(t, _row, _cols, _col, _p):
    return int(5 + 30 * t), int(40 + 60 * t), int(90 + 120 * (1 - t))


def _preset_lava_lamp(t, row, _cols, _col, p):
    h = 0.02 + 0.12 * math.sin(p * 1.5 + t * 4 + row * 0.08)
    return _hsv(h, 0.95, 0.85 + 0.15 * math.sin(p + t * 6))


def _preset_glitch(t, row, cols, col, p):
    base = _hsv(t + row * 0.05, 0.9, 1.0)
    if (col + int(p * 20)) % 7 == 0:
        return base[2], base[0], base[1]
    if (row + col) % 11 == 0:
        return 255, 255, 255
    return base


def _preset_synthwave(t, _row, _cols, _col, p):
    return _hsv(0.82 + 0.1 * t + 0.05 * math.sin(p * 2), 0.9, 1.0)


def _preset_emerald(t, _row, _cols, _col, _p):
    return int(20 + 40 * t), int(160 + 80 * t), int(80 + 60 * (1 - t))


def _preset_ruby(t, _row, _cols, _col, _p):
    return int(160 + 95 * t), int(20 + 30 * t), int(60 + 40 * (1 - t))


def _preset_sapphire(t, _row, _cols, _col, _p):
    return int(30 + 40 * t), int(80 + 70 * t), int(180 + 75 * t)


def _preset_amethyst(t, row, _cols, _col, p):
    return _hsv(0.72 + 0.08 * t + 0.03 * math.sin(row + p), 0.7, 0.95)


def _preset_chrome(t, _row, _cols, _col, _p):
    v = int(160 + 95 * abs(math.sin(t * math.pi)))
    return v, v, int(v * 1.05) if v < 240 else 255


def _preset_retro_tv(t, row, _cols, col, p):
    return _hsv(0.55 + 0.02 * (col % 3) + row * 0.01 + p * 0.08, 0.55, 0.85)


def _preset_wine(t, _row, _cols, _col, _p):
    return int(100 + 100 * t), int(15 + 25 * t), int(40 + 50 * (1 - t))


def _preset_mint(t, _row, _cols, _col, _p):
    return int(180 + 50 * (1 - t)), 255, int(200 + 40 * t)


def _preset_peach(t, _row, _cols, _col, _p):
    return 255, int(200 + 40 * t), int(160 + 60 * (1 - t))


def _preset_steel(t, _row, _cols, _col, _p):
    v = int(120 + 100 * t)
    return v, int(v * 1.02), int(v * 1.08)


def _preset_ultraviolet(t, row, _cols, _col, p):
    return _hsv(0.68 + t * 0.15 + p * 0.1 + row * 0.015, 0.85, 0.92)


def _preset_coral(t, _row, _cols, _col, _p):
    return 255, int(100 + 80 * t), int(90 + 70 * (1 - t))


def _preset_forest(t, _row, _cols, _col, _p):
    return int(20 + 30 * t), int(90 + 80 * t), int(40 + 30 * (1 - t))


def _preset_sky(t, _row, _cols, _col, _p):
    return int(100 + 100 * t), int(180 + 60 * t), 255


def _preset_ember(t, row, _cols, _col, p):
    return _hsv(0.05 + 0.08 * t + 0.02 * math.sin(row + p * 4), 0.95, 0.75 + 0.25 * t)


def _preset_holo(t, row, cols, col, p):
    return _hsv(t * 0.6 + row * 0.035 + col / max(cols, 1) * 0.2 + p * 0.25, 0.5, 1.0)


def _preset_pride(t, _row, _cols, _col, p):
    return _hsv(t + p * 0.05, 0.85, 1.0)


def _preset_noir(t, _row, _cols, _col, _p):
    v = int(30 + 200 * t * t)
    return v, v, v


def _preset_cotton(t, _row, _cols, _col, _p):
    return 255, int(240 + 15 * t), int(250 - 20 * t)


def _preset_rust(t, _row, _cols, _col, _p):
    return int(180 + 60 * t), int(70 + 40 * t), int(30 + 20 * (1 - t))


def _preset_teal(t, _row, _cols, _col, _p):
    return int(0 + 40 * t), int(160 + 70 * t), int(150 + 80 * (1 - t))


def _preset_amber(t, _row, _cols, _col, _p):
    return 255, int(180 + 60 * t), int(0 + 40 * (1 - t))


def _preset_charcoal(t, _row, _cols, _col, _p):
    v = int(50 + 120 * t)
    return v, v, int(v * 1.05)


def _preset_rose_gold(t, _row, _cols, _col, _p):
    return 255, int(170 + 50 * t), int(160 + 40 * (1 - t))


def _preset_electric(t, row, _cols, _col, p):
    return _hsv(0.58 + 0.12 * math.sin(p * 3 + t * 10 + row * 0.05), 1.0, 1.0)


def _preset_midnight(t, _row, _cols, _col, p):
    return int(20 + 40 * t), int(30 + 50 * t), int(80 + 120 * (1 - t) + 20 * math.sin(p))


def _preset_dracula(t, _row, _cols, _col, _p):
    return _lerp(189, 255, t), _lerp(147, 121, t), _lerp(249, 192, t)


def _preset_nord(t, _row, _cols, _col, _p):
    return _lerp(136, 94, t), _lerp(192, 129, t), _lerp(208, 145, t)


def _preset_tokyo_night(t, row, _cols, _col, p):
    return _hsv(0.62 + t * 0.12 + 0.04 * math.sin(row + p * 2), 0.75, 0.88 + 0.12 * t)


def _preset_catppuccin(t, _row, _cols, _col, _p):
    return _lerp(205, 245, t), _lerp(214, 194, t), _lerp(244, 231, t)


def _preset_gruvbox(t, _row, _cols, _col, _p):
    return _lerp(215, 251, t), _lerp(153, 184, t), _lerp(132, 117, t)


def _preset_solarized(t, _row, _cols, _col, _p):
    if t < 0.5:
        u = t * 2
        return _lerp(7, 38, u), _lerp(54, 139, u), _lerp(66, 153, u)
    u = (t - 0.5) * 2
    return _lerp(181, 203, u), _lerp(137, 75, u), _lerp(0, 22, u)


def _preset_one_dark(t, _row, _cols, _col, _p):
    return _lerp(97, 224, t), _lerp(175, 108, t), _lerp(239, 152, t)


def _preset_tron(t, row, _cols, col, p):
    pulse = 0.85 + 0.15 * math.sin(p * 2.5 + col * 0.08 + row * 0.06)
    return int(0 * pulse), int(220 * pulse + 35 * t), int(255 * pulse)


def _preset_phosphor(t, row, _cols, _col, p):
    flick = 0.9 + 0.1 * math.sin(row * 0.8 + p * 4 + t * 12)
    return 0, int(255 * flick * (0.55 + 0.45 * t)), int(70 * flick * (1 - t * 0.5))


def _preset_nebula(t, row, cols, col, p):
    return _hsv(0.72 + t * 0.2 + row * 0.025 + col / max(cols, 1) * 0.15 + p * 0.12, 0.8, 0.75 + 0.25 * t)


def _preset_oil_slick(t, row, _cols, col, p):
    return _hsv(0.15 + t * 0.65 + row * 0.04 + col * 0.003 + p * 0.18, 0.85, 0.55 + 0.45 * abs(math.sin(t * math.pi)))


def _preset_biolum(t, row, _cols, _col, p):
    return _hsv(0.48 + 0.06 * math.sin(row * 0.4 + p * 3), 0.95, 0.5 + 0.5 * t)


def _preset_venom(t, row, _cols, _col, p):
    return _hsv(0.28 + 0.05 * t + 0.03 * math.sin(row + p * 2), 1.0, 0.35 + 0.65 * t)


def _preset_samurai(t, _row, _cols, _col, _p):
    if t < 0.55:
        u = t / 0.55
        return int(180 + 75 * u), int(20 + 30 * u), int(30 + 40 * u)
    u = (t - 0.55) / 0.45
    return int(240 + 15 * u), int(240 + 15 * u), int(235 + 20 * u)


def _preset_cyberpunk(t, row, _cols, col, p):
    if (col + int(p * 10)) % 5 < 2:
        return _hsv(0.88 + 0.05 * t, 1.0, 1.0)
    return _hsv(0.52 + 0.08 * math.sin(row + p), 1.0, 0.95)


def _preset_heatmap(t, _row, _cols, _col, _p):
    if t < 0.33:
        u = t / 0.33
        return 0, int(80 + 175 * u), int(200 * (1 - u))
    if t < 0.66:
        u = (t - 0.33) / 0.33
        return int(255 * u), 255, 0
    u = (t - 0.66) / 0.34
    return 255, int(255 * (1 - u)), 0


def _preset_duotone_cyan_magenta(t, _row, _cols, _col, _p):
    if t < 0.5:
        u = t * 2
        return _lerp(0, 255, u), _lerp(220, 0, u), _lerp(255, 200, u)
    u = (t - 0.5) * 2
    return _lerp(255, 255, u), _lerp(0, 80, u), _lerp(200, 255, u)


def _preset_spotify(t, _row, _cols, _col, _p):
    return _lerp(30, 29, t), _lerp(185, 215, t), _lerp(84, 96, t)


def _preset_twitch(t, row, _cols, _col, p):
    return _hsv(0.72 + 0.06 * t + 0.04 * math.sin(row + p * 2), 0.65, 0.55 + 0.45 * t)


def _preset_cga(t, _row, _cols, _col, _p):
    stops = [(0, 0, 170), (0, 170, 170), (170, 0, 170), (255, 255, 255)]
    i = min(int(t * len(stops)), len(stops) - 1)
    return stops[i]


def _preset_inferno(t, _row, _cols, _col, _p):
    if t < 0.4:
        u = t / 0.4
        return int(40 + 80 * u), 0, int(60 + 100 * u)
    if t < 0.7:
        u = (t - 0.4) / 0.3
        return int(120 + 135 * u), int(20 * u), 0
    u = (t - 0.7) / 0.3
    return 255, int(200 + 55 * u), int(80 * u)


def _preset_cosmic_dust(t, row, cols, col, p):
    base = _hsv(0.58 + t * 0.15, 0.4, 0.35 + 0.65 * t)
    sparkle = 1.0 if (row * 17 + col * 13 + int(p * 30)) % 23 == 0 else 0.0
    if sparkle:
        return 255, 255, 255
    return base


def _preset_blood_moon(t, row, _cols, _col, p):
    return _hsv(0.98 + 0.03 * math.sin(row * 0.2 + p), 0.75 + 0.2 * t, 0.45 + 0.55 * t)


def _preset_frost_fire(t, _row, _cols, _col, _p):
    if t < 0.5:
        u = t * 2
        return _lerp(180, 255, u), _lerp(220, 120, u), 255
    u = (t - 0.5) * 2
    return 255, _lerp(120, 40, u), _lerp(255, 20, u)


def _preset_miami(t, row, _cols, _col, p):
    return _hsv(0.86 + 0.08 * t + 0.06 * math.sin(p + row * 0.05), 0.85, 0.92 + 0.08 * math.sin(t * 6))


def _preset_monokai(t, _row, _cols, _col, _p):
    palette = [(248, 248, 242), (230, 219, 116), (102, 217, 239), (249, 38, 114), (166, 226, 46)]
    i = min(int(t * len(palette)), len(palette) - 1)
    return palette[i]


def _preset_everforest(t, _row, _cols, _col, _p):
    return _lerp(167, 231, t), _lerp(192, 216, t), _lerp(128, 156, t)


def _preset_ayu(t, _row, _cols, _col, _p):
    return _lerp(255, 255, t), _lerp(180, 122, t), _lerp(97, 87, t)


def _preset_scanline(t, row, cols, col, p):
    base = _hsv(0.35 + t * 0.15, 0.7, 0.8)
    if row % 2 == 0:
        dim = 0.55 + 0.15 * math.sin(p * 2)
        return int(base[0] * dim), int(base[1] * dim), int(base[2] * dim)
    return base


def _preset_golden_hour(t, _row, _cols, _col, _p):
    return 255, int(140 + 80 * (1 - t)), int(40 + 100 * t)


def _preset_deep_purple(t, row, _cols, _col, p):
    return _hsv(0.68 + 0.12 * t + 0.05 * math.sin(row + p), 0.9, 0.5 + 0.5 * t)


def _preset_carbon(t, _row, _cols, _col, _p):
    v = int(25 + 200 * t)
    return v, int(v * 0.98), int(v * 1.04)


def _preset_bubblegum(t, row, _cols, _col, p):
    return _hsv(0.92 + 0.06 * math.sin(row * 0.1 + p * 2), 0.55 + 0.35 * t, 1.0)


def _preset_rainbow_dark(t, row, _cols, col, p):
    r, g, b = _hsv(t + p * 0.12 + row * 0.02, 0.85, 0.55 + 0.45 * t)
    return r, g, b


def _preset_terminal_amber(t, _row, _cols, _col, p):
    warm = 0.92 + 0.08 * math.sin(p * 3 + t * 8)
    return int(255 * warm), int(180 * warm * (0.7 + 0.3 * t)), int(40 * warm * (1 - t))


# (display name, rgb function, animated)
_PRESET_DEFS: List[Tuple[str, RgbFn, bool]] = [
    ("Без цвета", lambda *a: (220, 220, 220), False),
    ("TAAG красный", _preset_taag_red, False),
    ("Rainbow", _preset_rainbow, True),
    ("Iridescent (перелив)", _preset_iridescent, True),
    ("Neon pulse", _preset_neon_pulse, True),
    ("Fire", _preset_fire, False),
    ("Ocean", _preset_ocean, False),
    ("Gold metal", _preset_gold, False),
    ("Cyber", _preset_cyber, True),
    ("Matrix green", _preset_matrix, True),
    ("Blood", _preset_blood, False),
    ("Discord blurple", _preset_discord, False),
    ("Vaporwave", _preset_vaporwave, True),
    ("Sunset", _preset_sunset, False),
    ("Arctic", _preset_arctic, False),
    ("Toxic", _preset_toxic, True),
    ("Sakura", _preset_sakura, False),
    ("Lavender", _preset_lavender, False),
    ("Copper", _preset_copper, False),
    ("Ice shimmer", _preset_ice, True),
    ("Plasma", _preset_plasma, True),
    ("Aurora", _preset_aurora, True),
    ("Minecraft", _preset_minecraft, False),
    ("Slime", _preset_slime, True),
    ("Halloween", _preset_halloween, False),
    ("Candy", _preset_candy, True),
    ("Monochrome", _preset_monochrome, False),
    ("Blue ↔ Red", _preset_blue_red, False),
    ("Pastel dream", _preset_pastel, False),
    ("Deep sea", _preset_deep_sea, False),
    ("Lava lamp", _preset_lava_lamp, True),
    ("Glitch", _preset_glitch, True),
    ("Synthwave", _preset_synthwave, True),
    ("Emerald", _preset_emerald, False),
    ("Ruby", _preset_ruby, False),
    ("Sapphire", _preset_sapphire, False),
    ("Amethyst", _preset_amethyst, True),
    ("Chrome", _preset_chrome, False),
    ("Retro TV", _preset_retro_tv, True),
    ("Wine", _preset_wine, False),
    ("Mint", _preset_mint, False),
    ("Peach", _preset_peach, False),
    ("Steel", _preset_steel, False),
    ("Ultraviolet", _preset_ultraviolet, True),
    ("Coral", _preset_coral, False),
    ("Forest", _preset_forest, False),
    ("Sky", _preset_sky, False),
    ("Ember wave", _preset_ember, True),
    ("Holographic", _preset_holo, True),
    ("Pride spectrum", _preset_pride, True),
    ("Noir", _preset_noir, False),
    ("Cotton", _preset_cotton, False),
    ("Rust", _preset_rust, False),
    ("Teal", _preset_teal, False),
    ("Amber", _preset_amber, False),
    ("Charcoal", _preset_charcoal, False),
    ("Rose gold", _preset_rose_gold, False),
    ("Electric", _preset_electric, True),
    ("Midnight", _preset_midnight, True),
    ("Dracula", _preset_dracula, False),
    ("Nord frost", _preset_nord, False),
    ("Tokyo Night", _preset_tokyo_night, True),
    ("Catppuccin", _preset_catppuccin, False),
    ("Gruvbox", _preset_gruvbox, False),
    ("Solarized", _preset_solarized, False),
    ("One Dark Pro", _preset_one_dark, False),
    ("Tron cyan", _preset_tron, True),
    ("Phosphor CRT", _preset_phosphor, True),
    ("Nebula", _preset_nebula, True),
    ("Oil slick", _preset_oil_slick, True),
    ("Bioluminescence", _preset_biolum, True),
    ("Venom acid", _preset_venom, True),
    ("Samurai", _preset_samurai, False),
    ("Cyberpunk FM", _preset_cyberpunk, True),
    ("Heatmap", _preset_heatmap, False),
    ("Cyan ↔ Magenta", _preset_duotone_cyan_magenta, False),
    ("Spotify green", _preset_spotify, False),
    ("Twitch purple", _preset_twitch, True),
    ("CGA retro", _preset_cga, False),
    ("Inferno", _preset_inferno, False),
    ("Cosmic dust", _preset_cosmic_dust, True),
    ("Blood moon", _preset_blood_moon, True),
    ("Frost ↔ Fire", _preset_frost_fire, False),
    ("Miami vice", _preset_miami, True),
    ("Monokai", _preset_monokai, False),
    ("Everforest", _preset_everforest, False),
    ("Ayu mirage", _preset_ayu, False),
    ("Scanline", _preset_scanline, True),
    ("Golden hour", _preset_golden_hour, False),
    ("Deep purple", _preset_deep_purple, True),
    ("Carbon", _preset_carbon, False),
    ("Bubblegum", _preset_bubblegum, True),
    ("Rainbow on dark", _preset_rainbow_dark, True),
    ("Terminal amber", _preset_terminal_amber, True),
]

COLOR_PRESETS: List[str] = [name for name, _, _ in _PRESET_DEFS]

_PRESET_MAP: Dict[str, RgbFn] = {name: fn for name, fn, _ in _PRESET_DEFS}
_ANIMATED: Set[str] = {name for name, _, anim in _PRESET_DEFS if anim}


def _truecolor_fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def _rgb_at(preset: str, col: int, cols: int, row: int, phase: float) -> Tuple[int, int, int]:
    t = col / max(cols - 1, 1)
    fn = _PRESET_MAP.get(preset)
    if fn is None:
        return 220, 220, 220
    return fn(t, row, cols, col, phase)


def colorize_ascii(art: str, preset: str, phase: float = 0.0) -> str:
    if not art or preset in ("", "Без цвета"):
        return art
    lines = art.split("\n")
    out_lines: List[str] = []
    for row, line in enumerate(lines):
        if not line.strip():
            out_lines.append(line)
            continue
        cols = len(line)
        parts: List[str] = []
        append = parts.append
        for col, ch in enumerate(line):
            if ch == " ":
                append(ch)
            else:
                r, g, b = _rgb_at(preset, col, cols, row, phase)
                append(_truecolor_fg(r, g, b))
                append(ch)
                append(RESET)
        out_lines.append("".join(parts))
    return "\n".join(out_lines)


def tk_color_at(preset: str, col: int, cols: int, row: int, phase: float) -> str:
    r, g, b = _rgb_at(preset, col, cols, row, phase)
    return f"#{r:02x}{g:02x}{b:02x}"


def animated_presets() -> set:
    return set(_ANIMATED)
