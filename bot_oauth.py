#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Discord OAuth2 для привязки аккаунта без ручного токена."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple

OAUTH_AUTHORIZE = "https://discord.com/api/oauth2/authorize"
OAUTH_TOKEN = "https://discord.com/api/v10/oauth2/token"
API_ME = "https://discord.com/api/v10/users/@me"

_pending: Dict[str, Tuple[str, float]] = {}
_lock = threading.Lock()
TTL_SEC = 600


def _state_secret(cfg: Dict[str, Any]) -> str:
    return str(cfg.get("client_secret") or cfg.get("oauth_state_secret") or "").strip()


def create_signed_state(
    cfg: Dict[str, Any],
    discord_user_id: str,
    *,
    source_id: str = "",
    target_id: str = "",
    strategy: str = "2",
) -> str:
    secret = _state_secret(cfg)
    if not secret:
        raise RuntimeError("missing client_secret for OAuth state")
    payload = {
        "u": str(discord_user_id),
        "s": str(source_id or ""),
        "t": str(target_id or ""),
        "st": str(strategy or "2"),
        "e": int(time.time()) + TTL_SEC,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()[:16]
    return base64.urlsafe_b64encode(raw + sig).decode("ascii").rstrip("=")


def register_oauth_state(
    cfg: Dict[str, Any],
    discord_user_id: str,
    store=None,
    *,
    source_id: str = "",
    target_id: str = "",
    strategy: str = "2",
    use_signed: bool = True,
) -> str:
    if use_signed and _state_secret(cfg):
        state = create_signed_state(
            cfg,
            discord_user_id,
            source_id=source_id,
            target_id=target_id,
            strategy=strategy,
        )
        if store is not None and getattr(store, "enabled", False):
            store.save_oauth_flow(
                state,
                discord_user_id,
                source_id=source_id,
                target_id=target_id,
                strategy=strategy,
                ttl_sec=TTL_SEC,
            )
        return state
    state = secrets.token_urlsafe(24)
    if store is not None and getattr(store, "enabled", False):
        if store.save_oauth_flow(
            state,
            discord_user_id,
            source_id=source_id,
            target_id=target_id,
            strategy=strategy,
            ttl_sec=TTL_SEC,
        ):
            return state
    with _lock:
        _pending[state] = (str(discord_user_id), time.time() + TTL_SEC)
    return state


def pop_oauth_user(state: str, store=None) -> Optional[str]:
    flow = consume_oauth_flow(state, store)
    return flow.get("discord_user_id") if flow else None


def consume_oauth_flow(state: str, store=None) -> Optional[Dict[str, Any]]:
    if store is not None and getattr(store, "enabled", False):
        row = store.consume_oauth_flow(state)
        if row:
            return {
                "discord_user_id": str(row.get("discord_user_id") or ""),
                "source_id": row.get("source_id") or "",
                "target_id": row.get("target_id") or "",
                "strategy": str(row.get("strategy") or "2"),
            }
    with _lock:
        item = _pending.pop(state, None)
    if not item:
        return None
    user_id, exp = item
    if time.time() > exp:
        return None
    return {
        "discord_user_id": user_id,
        "source_id": "",
        "target_id": "",
        "strategy": "2",
    }


def build_authorize_url(
    cfg: Dict[str, Any],
    discord_user_id: str,
    store=None,
    *,
    source_id: str = "",
    target_id: str = "",
    strategy: str = "2",
) -> str:
    state = register_oauth_state(
        cfg,
        discord_user_id,
        store,
        source_id=source_id,
        target_id=target_id,
        strategy=strategy,
    )
    params = {
        "client_id": str(cfg["client_id"]),
        "response_type": "code",
        "redirect_uri": str(cfg["redirect_uri"]),
        "scope": str(cfg.get("oauth_scope") or "identify guilds"),
        "state": state,
        "prompt": "consent",
    }
    return f"{OAUTH_AUTHORIZE}?{urllib.parse.urlencode(params)}"


def _post_form(url: str, data: Dict[str, str]) -> Dict[str, Any]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "VexxClonerBot/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw) if raw else {}


def exchange_code(cfg: Dict[str, Any], code: str) -> Dict[str, Any]:
    return _post_form(
        OAUTH_TOKEN,
        {
            "client_id": str(cfg["client_id"]),
            "client_secret": str(cfg["client_secret"]),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": str(cfg["redirect_uri"]),
        },
    )


def refresh_access(cfg: Dict[str, Any], refresh_token: str) -> Dict[str, Any]:
    return _post_form(
        OAUTH_TOKEN,
        {
            "client_id": str(cfg["client_id"]),
            "client_secret": str(cfg["client_secret"]),
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )


def fetch_me(access_token: str) -> Optional[Dict[str, Any]]:
    req = urllib.request.Request(
        API_ME,
        headers={
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "VexxClonerBot/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def token_expires_at(expires_in: int) -> float:
    return time.time() + max(int(expires_in or 0), 60) - 30


def store_token_payload(token_resp: Dict[str, Any]) -> Tuple[str, str, Optional[float]]:
    access = token_resp.get("access_token") or ""
    refresh = token_resp.get("refresh_token") or ""
    exp = token_expires_at(int(token_resp.get("expires_in") or 3600))
    return f"oauth:{access}", refresh, exp
