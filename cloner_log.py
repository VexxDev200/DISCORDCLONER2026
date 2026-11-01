#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File logging; console can stay quiet."""

from datetime import datetime, timezone

from app_paths import data_path

_LOG_PATH = data_path("cloner.log")


def _line(level: str, msg: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{ts} [{level}] {msg}\n"


def write(level: str, msg: str) -> None:
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(_line(level, msg))
    except OSError:
        pass


def info(msg: str) -> None:
    write("INFO", msg)


def error(msg: str) -> None:
    write("ERROR", msg)


def summary(stats: dict) -> None:
    write(
        "SUMMARY",
        f"roles={stats.get('roles')} channels={stats.get('channels')} "
        f"errors={stats.get('errors')} failed={len(stats.get('failed_items') or [])} "
        f"elapsed={stats.get('elapsed_sec')}s",
    )
