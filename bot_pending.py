#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Очередь: после первого OAuth автоматически стартовать /clone."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class PendingClone:
    source_id: str
    target_id: str
    strategy: str


_lock = threading.Lock()
_pending: Dict[str, PendingClone] = {}


def set_pending_clone(
    discord_user_id: str,
    source_id: str,
    target_id: str,
    strategy: str,
) -> None:
    with _lock:
        _pending[str(discord_user_id)] = PendingClone(
            source_id.strip(),
            target_id.strip(),
            str(strategy or "2"),
        )


def pop_pending_clone(discord_user_id: str) -> Optional[PendingClone]:
    with _lock:
        return _pending.pop(str(discord_user_id), None)


def clear_pending(discord_user_id: str) -> None:
    with _lock:
        _pending.pop(str(discord_user_id), None)
