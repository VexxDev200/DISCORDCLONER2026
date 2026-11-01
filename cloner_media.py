#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CDN download helpers for Discord media uploads."""

import base64
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, Hashable, List, Optional, TypeVar

_ssl = ssl.create_default_context()
_ssl.check_hostname = False
_ssl.verify_mode = ssl.CERT_NONE

T = TypeVar("T")
K = TypeVar("K")


def fetch_bytes(url: str, timeout: int = 30) -> Optional[bytes]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=_ssl, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def bytes_to_data_uri(raw: bytes, mime: str) -> str:
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def fetch_data_uri(url: str, mime: str, timeout: int = 30) -> Optional[str]:
    raw = fetch_bytes(url, timeout=timeout)
    if not raw:
        return None
    return bytes_to_data_uri(raw, mime)


def guild_icon_uri(guild_id: str, icon_hash: str) -> Optional[str]:
    ext = "gif" if icon_hash.startswith("a_") else "png"
    mime = "image/gif" if ext == "gif" else "image/png"
    url = f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.{ext}"
    return fetch_data_uri(url, mime)


def role_icon_uri(role_id: str, icon_hash: str) -> Optional[str]:
    ext = "gif" if icon_hash.startswith("a_") else "png"
    mime = "image/gif" if ext == "gif" else "image/png"
    url = f"https://cdn.discordapp.com/role-icons/{role_id}/{icon_hash}.{ext}?size=128"
    return fetch_data_uri(url, mime)


def emoji_uri(emoji_id: str, animated: bool) -> Optional[str]:
    ext = "gif" if animated else "png"
    mime = f"image/{ext}"
    url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
    return fetch_data_uri(url, mime)


def sticker_uri(sticker_id: str, fmt: int) -> Optional[str]:
    ext = "png" if fmt == 1 else "apng" if fmt == 2 else "json"
    mime = "image/png" if ext == "png" else "application/json" if ext == "json" else "image/apng"
    url = f"https://cdn.discordapp.com/stickers/{sticker_id}.{ext}"
    return fetch_data_uri(url, mime)


def webhook_avatar_uri(webhook_id: str, avatar_hash: str) -> Optional[str]:
    ext = "gif" if avatar_hash.startswith("a_") else "png"
    mime = "image/gif" if ext == "gif" else "image/png"
    url = f"https://cdn.discordapp.com/avatars/{webhook_id}/{avatar_hash}.{ext}"
    return fetch_data_uri(url, mime)


def parallel_map(
    items: List[K],
    fn: Callable[[K], T],
    workers: int = 4,
    key_fn: Optional[Callable[[K], Hashable]] = None,
) -> Dict[Hashable, T]:
    out: Dict[Hashable, T] = {}
    if not items:
        return out
    key_fn = key_fn or (lambda i: id(i))
    w = max(1, min(workers, len(items)))

    def task(item: K):
        return key_fn(item), fn(item)

    with ThreadPoolExecutor(max_workers=w) as pool:
        for k, val in pool.map(task, items):
            out[k] = val
    return out
