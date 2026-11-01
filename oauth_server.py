#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Локальный HTTP callback для Discord OAuth."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse

import bot_oauth

try:
    import bot_config
except ImportError:
    bot_config = None  # type: ignore

OnLinked = Callable[[str, Dict[str, Any], Optional[Dict[str, Any]]], None]

_HTML_OK = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>Vexx Cloner</title>
<style>body{{background:#08080e;color:#eaeaf4;font-family:Segoe UI,sans-serif;text-align:center;padding:48px}}
h1{{color:#bf5fff}}p{{color:#00d9ff}}</style></head>
<body><h1>Аккаунт привязан</h1><p>Закрой вкладку и вернись в Discord — бот продолжит в ЛС.</p></body></html>"""
_HTML_FAIL = """<!DOCTYPE html><html><body style="background:#111;color:#f88;text-align:center;padding:48px">
<h1>Ошибка авторизации</h1><p>Вернись в Discord и нажми /login снова.</p></body></html>"""


class OAuthHTTPServer(HTTPServer):
    def __init__(
        self,
        bind_host: str,
        port: int,
        cfg: Dict[str, Any],
        on_linked: OnLinked,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self.cfg = cfg
        self.on_linked = on_linked
        self.on_error = on_error
        super().__init__((bind_host, port), _Handler)


class _Handler(BaseHTTPRequestHandler):
    server: OAuthHTTPServer  # type: ignore

    def log_message(self, *_args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        if not parsed.path.rstrip("/").endswith("/oauth/callback"):
            self.send_error(404)
            return
        qs = parse_qs(parsed.query)
        code = (qs.get("code") or [None])[0]
        state = (qs.get("state") or [None])[0]
        err = (qs.get("error") or [None])[0]
        if err or not code or not state:
            self._html(400, _HTML_FAIL)
            return
        store = None
        try:
            from discordcloner import init_neon_store

            store = init_neon_store()
        except Exception:
            store = None
        flow = bot_oauth.consume_oauth_flow(state, store)
        if not flow:
            self._html(400, _HTML_FAIL)
            return
        user_id = flow.get("discord_user_id")
        try:
            token_resp = bot_oauth.exchange_code(self.server.cfg, code)
            access = token_resp.get("access_token")
            if not access:
                raise RuntimeError(token_resp.get("error_description") or "no access_token")
            me = bot_oauth.fetch_me(access)
            if not me:
                raise RuntimeError("users/@me failed")
            if str(me.get("id")) != str(user_id):
                raise RuntimeError("user id mismatch")
            self.server.on_linked(user_id, token_resp, flow)
            self._html(200, _HTML_OK)
        except Exception as ex:
            if self.server.on_error:
                self.server.on_error(str(ex))
            self._html(500, _HTML_FAIL)

    def _html(self, code: int, body: str):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def start_oauth_server(
    cfg: Dict[str, Any],
    on_linked: OnLinked,
    on_error: Optional[Callable[[str], None]] = None,
) -> threading.Thread:
    if bot_config:
        host = bot_config.oauth_bind_host(cfg)
        port = bot_config.oauth_port(cfg)
    else:
        host = "127.0.0.1"
        port = int(cfg.get("oauth_port") or 8765)

    def run():
        srv = OAuthHTTPServer(host, port, cfg, on_linked, on_error)
        print(f"OAuth HTTP слушает {host}:{port}")
        srv.serve_forever()

    th = threading.Thread(target=run, name="oauth-http", daemon=True)
    th.start()
    return th
