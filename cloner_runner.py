#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Запуск клона из бота (токен из Neon)."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import bot_config
import bot_oauth
from discordcloner import CONFIG, DiscordAPI, GodCloner, Language, init_neon_store, persist_login

_CONFIG_CLONER_TOKEN: Optional[str] = None
_CONFIG_CLONER_ME: Optional[Dict[str, Any]] = None


def init_config_cloner_token(bot_cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """User token from config — один раз при запуске бота, без форм в Discord."""
    global _CONFIG_CLONER_TOKEN, _CONFIG_CLONER_ME
    raw = str(bot_cfg.get("cloner_token") or "").strip()
    if not raw:
        _CONFIG_CLONER_TOKEN = None
        _CONFIG_CLONER_ME = None
        return None
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    api = DiscordAPI(raw)
    me = api.get("/users/@me")
    if not me:
        raise RuntimeError("cloner_token_invalid")
    _CONFIG_CLONER_TOKEN = raw
    _CONFIG_CLONER_ME = me
    return me


def config_cloner_token() -> Optional[str]:
    return _CONFIG_CLONER_TOKEN


def config_cloner_me() -> Optional[Dict[str, Any]]:
    return _CONFIG_CLONER_ME


def _utc_from_ts(ts: float) -> datetime:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def link_user_token(store, discord_user_id: str, raw_token: str) -> str:
    """Validate user token and save to Neon (no OAuth / no redirect)."""
    token = (raw_token or "").strip()
    if not token:
        raise RuntimeError("empty_token")
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    api = DiscordAPI(token)
    user = api.get("/users/@me")
    if not user:
        raise RuntimeError("token_invalid")
    ok = store.upsert_account(
        discord_user_id,
        token,
        username=user.get("username") or "",
        global_name=user.get("global_name") or "",
        lang="ru",
    )
    if not ok:
        raise RuntimeError(f"save_failed:{store.last_error or 'neon'}")
    persist_login(store, discord_user_id, token, user, "ru")
    return user.get("global_name") or user.get("username") or "ok"


def get_stored_user_token(store, discord_user_id: str) -> Optional[str]:
    acc = store.get_last_account(discord_user_id)
    if not acc:
        return None
    token = str(acc.get("token") or "").strip()
    if not token or token.startswith("oauth:"):
        return None
    return token


def has_user_token(discord_user_id: str) -> bool:
    store = init_neon_store()
    return get_stored_user_token(store, discord_user_id) is not None


def user_is_linked(discord_user_id: str) -> bool:
    return has_user_token(discord_user_id)


def ensure_user_token(store, discord_user_id: str, bot_cfg: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    user_tok = get_stored_user_token(store, discord_user_id)
    if user_tok:
        return user_tok, None
    acc = store.get_last_account(discord_user_id)
    if not acc or not acc.get("token"):
        raise RuntimeError("not_linked")
    token = acc["token"]
    if not str(token).startswith("oauth:"):
        return token, None

    exp = acc.get("token_expires_at")
    refresh = acc.get("refresh_token") or ""
    need = True
    if exp is not None:
        try:
            if hasattr(exp, "timestamp"):
                need = exp.timestamp() < time.time() + 60
            else:
                need = True
        except Exception:
            need = True
    if need and refresh:
        tr = bot_oauth.refresh_access(bot_cfg, refresh)
        if tr.get("access_token"):
            token, refresh, exp_ts = bot_oauth.store_token_payload(tr)
            store.upsert_account(
                discord_user_id,
                token,
                username=acc.get("username") or "",
                global_name=acc.get("global_name") or "",
                lang=acc.get("lang") or "ru",
                refresh_token=refresh,
                token_expires_at=_utc_from_ts(exp_ts) if exp_ts else None,
            )
    return token, acc.get("username")


def _guild_ok(api: DiscordAPI, guild_id: str) -> bool:
    gid = str(guild_id).strip()
    if not gid.isdigit():
        return False
    return bool(api.get(f"/guilds/{gid}"))


def _pick_clone_token(
    store,
    discord_user_id: str,
    bot_cfg: Dict[str, Any],
    source_id: str,
    target_id: str,
) -> Tuple[str, str]:
    """Return (token_for_cloner, mode_label). OAuth alone cannot read /guilds — use bot if invited."""
    user_token, _ = ensure_user_token(store, discord_user_id, bot_cfg)
    user_api = DiscordAPI(user_token)
    src_ok = _guild_ok(user_api, source_id)
    tgt_ok = _guild_ok(user_api, target_id)
    if src_ok and tgt_ok:
        return user_token, "user"

    bot_raw = str(bot_cfg.get("token") or "").strip()
    if bot_raw:
        bot_api = DiscordAPI(bot_raw, bot_auth=True)
        b_src = _guild_ok(bot_api, source_id)
        b_tgt = _guild_ok(bot_api, target_id)
        if b_src and b_tgt:
            return bot_raw, "bot"

    hints = []
    if not src_ok:
        hints.append(f"source: {user_api.last_error or 'no access'}")
    if not tgt_ok:
        hints.append(f"target: {user_api.last_error or 'no access'}")
    if bot_raw:
        bot_api = DiscordAPI(bot_raw, bot_auth=True)
        hints.append(
            "OAuth не клонирует серверы — нужен бот на обоих серверах (Admin на target). "
            f"bot source={_guild_ok(bot_api, source_id)} target={_guild_ok(bot_api, target_id)}"
        )
    raise RuntimeError("guild_access:" + "; ".join(hints))


def run_full_clone(
    discord_user_id: str,
    source_id: str,
    target_id: str,
    triad_strategy: str = "2",
    lang_code: str = "ru",
) -> str:
    bot_cfg = bot_config.load_bot_config()
    store = init_neon_store()
    token, mode = _pick_clone_token(
        store, discord_user_id, bot_cfg, source_id, target_id
    )
    use_bot = mode == "bot"

    api = DiscordAPI(token, bot_auth=use_bot)
    if not use_bot:
        user = api.get("/users/@me")
        if not user:
            raise RuntimeError("token_invalid")
    else:
        user = api.get("/users/@me") or {}

    source = api.get(f"/guilds/{source_id}")
    target = api.get(f"/guilds/{target_id}")
    if not source or not target:
        raise RuntimeError(f"guild_access:{api.last_error or 'missing guild'}")

    acct_token, _ = ensure_user_token(store, discord_user_id, bot_cfg)
    acct_api = DiscordAPI(acct_token)
    acct_user = acct_api.get("/users/@me") or user
    persist_login(
        store, discord_user_id, acct_token, acct_user, lang_code, source_id, target_id
    )
    if store.enabled:
        store.save_clone_context(discord_user_id, source_id, target_id)

    session_id = (
        store.start_session(
            discord_user_id,
            source_id,
            source.get("name", ""),
            target_id,
            target.get("name", ""),
            CONFIG,
        )
        if store.enabled
        else None
    )

    lang = Language(lang_code)
    CONFIG["console_quiet"] = True
    CONFIG["full_wipe_before_clone"] = False
    CONFIG["triad_strategy"] = str(triad_strategy or "2")

    cloner = GodCloner(
        token,
        lang,
        store=store,
        session_id=session_id,
        discord_user_id=discord_user_id,
        source_guild_id=source_id,
        target_guild_id=target_id,
        api_bot_auth=use_bot,
    )
    cloner.copy_everything(int(source_id), int(target_id))
    CONFIG.pop("triad_strategy", None)
    return f"{source.get('name')} → {target.get('name')}"
