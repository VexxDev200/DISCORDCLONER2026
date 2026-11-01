#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Neon PostgreSQL persistence for Discord God Cloner."""

import base64
import json
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from app_paths import data_path, is_frozen, resource_path

import boot_db
boot_db.boot()

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

_DEFAULT_URL_FILE = data_path("databaseneon.txt")
_SCHEMA_PATH = resource_path("schema.sql")


def _json_dumps(value: Any) -> str:
    def _default(o):
        if isinstance(o, (bytes, bytearray)):
            return base64.b64encode(o).decode("ascii")
        return str(o)

    return json.dumps(value, ensure_ascii=False, default=_default)


def _utcnow():
    return datetime.now(timezone.utc)


def _normalize_db_url(url: str) -> str:
    url = url.strip()
    url = re.sub(r"[&?]channel_binding=[^&]*", "", url)
    return url


def _embedded_url() -> Optional[str]:
    try:
        from db_embed import DATABASE_URL  # type: ignore
        if DATABASE_URL and str(DATABASE_URL).strip():
            return _normalize_db_url(str(DATABASE_URL).strip())
    except ImportError:
        pass
    return None


def load_database_url() -> tuple[Optional[str], str]:
    emb = _embedded_url()
    path = _DEFAULT_URL_FILE
    file_url = None
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            line = f.read().strip()
            if line:
                file_url = _normalize_db_url(line)

    if is_frozen() and emb:
        return emb, "embedded"
    if file_url:
        return file_url, "file"
    if emb:
        return emb, "embedded"

    for key in ("CLONER_DATABASE_URL",):
        env = os.environ.get(key, "").strip()
        if env:
            return _normalize_db_url(env), key
    return None, "none"


def _schema_sql_text() -> Optional[str]:
    try:
        from schema_embed import SCHEMA_SQL  # type: ignore
        if SCHEMA_SQL and SCHEMA_SQL.strip():
            return SCHEMA_SQL
    except ImportError:
        pass
    if os.path.isfile(_SCHEMA_PATH):
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            return f.read()
    return None


def _log_local(msg: str) -> None:
    try:
        p = data_path("cloner.log")
        with open(p, "a", encoding="utf-8") as f:
            f.write(f"{_utcnow().isoformat()} {msg}\n")
    except OSError:
        pass


def database_host_hint(url: Optional[str]) -> str:
    if not url:
        return "не задан"
    try:
        p = urlparse(url)
        db = (p.path or "").lstrip("/") or "?"
        return f"{p.hostname} / {db}"
    except Exception:
        return "скрыто"


class NeonStore:
    def __init__(self, database_url: Optional[str] = None):
        if database_url:
            self.database_url = database_url
            self.url_source = "argument"
        else:
            self.database_url, self.url_source = load_database_url()
        self.enabled = bool(self.database_url and psycopg is not None)
        self._last_error: Optional[str] = None
        self._schema_ready = False

    def bootstrap(self) -> bool:
        """Повторная инициализация перед записью (exe / холодный Neon)."""
        boot_db.boot()
        if not self.database_url:
            self.database_url, self.url_source = load_database_url()
        self.enabled = bool(self.database_url and psycopg is not None)
        if not self.enabled:
            self._last_error = "no database url or psycopg driver"
            _log_local(self._last_error)
            return False
        for attempt in range(5):
            if self.ping():
                return True
            self._schema_ready = False
            time.sleep(1.2 + attempt * 0.5)
        _log_local(f"bootstrap failed: {self.last_error}")
        return False

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def host_hint(self) -> str:
        return database_host_hint(self.database_url)

    @contextmanager
    def _conn(self):
        if not self.enabled:
            raise RuntimeError("Neon store disabled (no URL or psycopg)")
        with psycopg.connect(self.database_url, row_factory=dict_row, connect_timeout=15) as conn:
            yield conn

    def ensure_schema(self) -> bool:
        if not self.enabled:
            return False
        if self._schema_ready:
            return True
        raw = _schema_sql_text()
        if not raw:
            self._last_error = f"schema missing: {_SCHEMA_PATH}"
            return False
        try:
            statements = [
                s.strip()
                for s in raw.split(";")
                if s.strip() and not s.strip().startswith("--")
            ]
            with self._conn() as conn:
                with conn.cursor() as cur:
                    for stmt in statements:
                        cur.execute(stmt)
                    cur.execute(
                        "ALTER TABLE cloner_accounts ADD COLUMN IF NOT EXISTS refresh_token TEXT"
                    )
                    cur.execute(
                        "ALTER TABLE cloner_accounts ADD COLUMN IF NOT EXISTS "
                        "token_expires_at TIMESTAMPTZ"
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS oauth_flows (
                          state TEXT PRIMARY KEY,
                          discord_user_id TEXT NOT NULL,
                          source_id TEXT,
                          target_id TEXT,
                          strategy TEXT DEFAULT '2',
                          expires_at TIMESTAMPTZ NOT NULL
                        )
                        """
                    )
                    cur.execute(
                        """
                        CREATE TABLE IF NOT EXISTS bot_clone_queue (
                          id BIGSERIAL PRIMARY KEY,
                          discord_user_id TEXT NOT NULL,
                          source_id TEXT NOT NULL,
                          target_id TEXT NOT NULL,
                          strategy TEXT DEFAULT '2',
                          status TEXT NOT NULL DEFAULT 'pending',
                          created_at TIMESTAMPTZ DEFAULT NOW(),
                          finished_at TIMESTAMPTZ,
                          error_message TEXT
                        )
                        """
                    )
                conn.commit()
            self._schema_ready = True
            self._last_error = None
            return True
        except Exception as e:
            self._last_error = str(e)
            _log_local(f"schema: {e}")
            return False

    def ping(self) -> bool:
        if not self.enabled:
            self._last_error = "psycopg not installed or databaseneon.txt missing"
            return False
        try:
            if not self.ensure_schema():
                return False
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 AS ok")
                    cur.fetchone()
            self._last_error = None
            return True
        except Exception as e:
            self._last_error = str(e)
            _log_local(f"ping: {e}")
            return False

    def get_stats(self) -> Dict[str, int]:
        if not self.enabled or not self.ensure_schema():
            return {}
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    out = {}
                    for table in (
                        "cloner_accounts",
                        "clone_sessions",
                        "global_id_mappings",
                        "guild_snapshots",
                        "clone_logs",
                    ):
                        cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
                        out[table] = int(cur.fetchone()["n"])
                    return out
        except Exception as e:
            self._last_error = str(e)
            return {}

    def save_clone_context(
        self,
        discord_user_id: str,
        source_guild_id: str,
        target_guild_id: str,
    ) -> bool:
        if not self.bootstrap():
            return False
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE cloner_accounts
                        SET last_source_guild_id = %s,
                            last_target_guild_id = %s,
                            last_used_at = %s,
                            updated_at = %s
                        WHERE discord_user_id = %s
                        """,
                        (
                            str(source_guild_id),
                            str(target_guild_id),
                            _utcnow(),
                            _utcnow(),
                            str(discord_user_id),
                        ),
                    )
                conn.commit()
            return True
        except Exception as e:
            self._last_error = str(e)
            _log_local(f"save_clone_context: {e}")
            return False

    def upsert_account(
        self,
        discord_user_id: str,
        token: str,
        username: str = "",
        global_name: str = "",
        lang: str = "ru",
        source_guild_id: str = "",
        target_guild_id: str = "",
        refresh_token: str = "",
        token_expires_at=None,
    ) -> bool:
        if not self.bootstrap():
            return False
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO cloner_accounts
                            (discord_user_id, username, global_name, token, lang,
                             last_source_guild_id, last_target_guild_id,
                             refresh_token, token_expires_at,
                             last_used_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (discord_user_id) DO UPDATE SET
                            username = EXCLUDED.username,
                            global_name = EXCLUDED.global_name,
                            token = EXCLUDED.token,
                            lang = EXCLUDED.lang,
                            last_source_guild_id = COALESCE(EXCLUDED.last_source_guild_id, cloner_accounts.last_source_guild_id),
                            last_target_guild_id = COALESCE(EXCLUDED.last_target_guild_id, cloner_accounts.last_target_guild_id),
                            refresh_token = COALESCE(NULLIF(EXCLUDED.refresh_token, ''), cloner_accounts.refresh_token),
                            token_expires_at = COALESCE(EXCLUDED.token_expires_at, cloner_accounts.token_expires_at),
                            last_used_at = EXCLUDED.last_used_at,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            str(discord_user_id),
                            username or "",
                            global_name or "",
                            token,
                            lang,
                            str(source_guild_id) or None,
                            str(target_guild_id) or None,
                            refresh_token or None,
                            token_expires_at,
                            _utcnow(),
                            _utcnow(),
                        ),
                    )
                    cur.execute(
                        "SELECT discord_user_id FROM cloner_accounts WHERE discord_user_id = %s",
                        (str(discord_user_id),),
                    )
                    ok = cur.fetchone()
                conn.commit()
            if not ok:
                self._last_error = "upsert verify failed"
                _log_local(self._last_error)
                return False
            return True
        except Exception as e:
            self._last_error = str(e)
            _log_local(f"upsert_account: {e}")
            return False

    def save_oauth_flow(
        self,
        state: str,
        discord_user_id: str,
        source_id: str = "",
        target_id: str = "",
        strategy: str = "2",
        ttl_sec: int = 600,
    ) -> bool:
        if not self.bootstrap():
            return False
        exp = _utcnow() + timedelta(seconds=ttl_sec)
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM oauth_flows WHERE expires_at < NOW()")
                    cur.execute(
                        """
                        INSERT INTO oauth_flows
                            (state, discord_user_id, source_id, target_id, strategy, expires_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (state) DO UPDATE SET
                            discord_user_id = EXCLUDED.discord_user_id,
                            source_id = EXCLUDED.source_id,
                            target_id = EXCLUDED.target_id,
                            strategy = EXCLUDED.strategy,
                            expires_at = EXCLUDED.expires_at
                        """,
                        (
                            state,
                            str(discord_user_id),
                            source_id or None,
                            target_id or None,
                            str(strategy or "2"),
                            exp,
                        ),
                    )
                conn.commit()
            return True
        except Exception as e:
            self._last_error = str(e)
            _log_local(f"save_oauth_flow: {e}")
            return False

    def consume_oauth_flow(self, state: str) -> Optional[Dict[str, Any]]:
        if not self.ensure_schema():
            return None
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM oauth_flows
                        WHERE state = %s AND expires_at >= NOW()
                        RETURNING discord_user_id, source_id, target_id, strategy
                        """,
                        (state,),
                    )
                    row = cur.fetchone()
                conn.commit()
            return dict(row) if row else None
        except Exception as e:
            self._last_error = str(e)
            _log_local(f"consume_oauth_flow: {e}")
            return None

    def enqueue_clone_job(
        self,
        discord_user_id: str,
        source_id: str,
        target_id: str,
        strategy: str = "2",
    ) -> bool:
        if not self.bootstrap():
            return False
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO bot_clone_queue
                            (discord_user_id, source_id, target_id, strategy, status)
                        VALUES (%s, %s, %s, %s, 'pending')
                        """,
                        (
                            str(discord_user_id),
                            str(source_id),
                            str(target_id),
                            str(strategy or "2"),
                        ),
                    )
                conn.commit()
            return True
        except Exception as e:
            self._last_error = str(e)
            _log_local(f"enqueue_clone_job: {e}")
            return False

    def claim_clone_jobs(self, limit: int = 3) -> list:
        if not self.ensure_schema():
            return []
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE bot_clone_queue
                        SET status = 'running'
                        WHERE id IN (
                            SELECT id FROM bot_clone_queue
                            WHERE status = 'pending'
                            ORDER BY created_at ASC
                            LIMIT %s
                            FOR UPDATE SKIP LOCKED
                        )
                        RETURNING id, discord_user_id, source_id, target_id, strategy
                        """,
                        (limit,),
                    )
                    rows = cur.fetchall()
                conn.commit()
            return [dict(r) for r in rows]
        except Exception as e:
            self._last_error = str(e)
            _log_local(f"claim_clone_jobs: {e}")
            return []

    def finish_clone_job(self, job_id: int, ok: bool, error: str = "") -> None:
        if not self.enabled:
            return
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE bot_clone_queue
                        SET status = %s, finished_at = NOW(), error_message = %s
                        WHERE id = %s
                        """,
                        ("done" if ok else "failed", error or None, job_id),
                    )
                conn.commit()
        except Exception as e:
            _log_local(f"finish_clone_job: {e}")

    def get_last_account_token(self, discord_user_id: Optional[str] = None) -> Optional[str]:
        acc = self.get_last_account(discord_user_id)
        return acc.get("token") if acc else None

    def get_last_account(self, discord_user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self.enabled or not self.ensure_schema():
            return None
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    if discord_user_id:
                        cur.execute(
                            """
                            SELECT discord_user_id, username, global_name, token, lang,
                                   refresh_token, token_expires_at, last_used_at
                            FROM cloner_accounts WHERE discord_user_id = %s
                            """,
                            (str(discord_user_id),),
                        )
                    else:
                        cur.execute(
                            """
                            SELECT discord_user_id, username, global_name, token, lang,
                                   refresh_token, token_expires_at, last_used_at
                            FROM cloner_accounts
                            ORDER BY last_used_at DESC
                            LIMIT 1
                            """
                        )
                    row = cur.fetchone()
            if not row:
                return None
            return dict(row)
        except Exception as e:
            self._last_error = str(e)
            return None

    def delete_account(self, discord_user_id: str) -> bool:
        if not self.bootstrap():
            return False
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM cloner_accounts WHERE discord_user_id = %s",
                        (str(discord_user_id),),
                    )
                conn.commit()
            return True
        except Exception as e:
            self._last_error = str(e)
            return False

    def start_session(
        self,
        discord_user_id: str,
        source_guild_id: str,
        source_guild_name: str,
        target_guild_id: str,
        target_guild_name: str,
        config: Dict[str, Any],
    ) -> Optional[int]:
        if not self.bootstrap():
            return None
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO clone_sessions
                            (discord_user_id, source_guild_id, source_guild_name,
                             target_guild_id, target_guild_name, status, config)
                        VALUES (%s, %s, %s, %s, %s, 'running', %s::jsonb)
                        RETURNING id
                        """,
                        (
                            str(discord_user_id),
                            str(source_guild_id),
                            source_guild_name or "",
                            str(target_guild_id),
                            target_guild_name or "",
                            _json_dumps(config),
                        ),
                    )
                    row = cur.fetchone()
                conn.commit()
            return int(row["id"]) if row else None
        except Exception as e:
            self._last_error = str(e)
            _log_local(f"start_session: {e}")
            return None

    def finish_session(
        self,
        session_id: int,
        status: str,
        stats: Dict[str, Any],
        error_message: Optional[str] = None,
    ) -> None:
        if not self.enabled or not session_id or not self.ensure_schema():
            return
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE clone_sessions
                        SET status = %s, stats = %s::jsonb, error_message = %s, finished_at = %s,
                            genome_hash = COALESCE(%s, genome_hash),
                            entropy_seal = COALESCE(%s, entropy_seal)
                        WHERE id = %s
                        """,
                        (
                            status,
                            _json_dumps(stats),
                            error_message,
                            _utcnow(),
                            stats.get("genome_hash"),
                            stats.get("entropy_seal"),
                            session_id,
                        ),
                    )
                conn.commit()
        except Exception as e:
            self._last_error = str(e)

    def log(self, session_id: Optional[int], level: str, message: str, meta: Optional[Dict] = None) -> None:
        if not self.enabled or not session_id or not self.ensure_schema():
            return
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO clone_logs (session_id, level, message, meta)
                        VALUES (%s, %s, %s, %s::jsonb)
                        """,
                        (
                            session_id,
                            level,
                            message[:4000],
                            _json_dumps(meta or {}),
                        ),
                    )
                conn.commit()
        except Exception:
            pass

    def save_mapping(
        self,
        session_id: Optional[int],
        old_id: str,
        new_id: str,
        entity_type: str,
        source_guild_id: str = "",
        target_guild_id: str = "",
        profile_name: str = "default",
    ) -> None:
        if not self.bootstrap():
            return
        old_id, new_id = str(old_id), str(new_id)
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    if session_id:
                        cur.execute(
                            """
                            INSERT INTO id_mappings
                                (session_id, source_guild_id, target_guild_id, old_id, new_id, entity_type)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (session_id, old_id, entity_type) DO UPDATE SET
                                new_id = EXCLUDED.new_id
                            """,
                            (
                                session_id,
                                str(source_guild_id),
                                str(target_guild_id),
                                old_id,
                                new_id,
                                entity_type,
                            ),
                        )
                    if source_guild_id and target_guild_id:
                        cur.execute(
                            """
                            INSERT INTO pair_mapping_profiles
                                (source_guild_id, target_guild_id, profile_name, old_id, new_id, entity_type, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (source_guild_id, target_guild_id, profile_name, old_id, entity_type) DO UPDATE SET
                                new_id = EXCLUDED.new_id,
                                updated_at = EXCLUDED.updated_at
                            """,
                            (
                                str(source_guild_id),
                                str(target_guild_id),
                                profile_name or "default",
                                old_id,
                                new_id,
                                entity_type,
                                _utcnow(),
                            ),
                        )
                        if (profile_name or "default") == "default":
                            cur.execute(
                                """
                                INSERT INTO pair_mappings
                                    (source_guild_id, target_guild_id, old_id, new_id, entity_type, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (source_guild_id, target_guild_id, old_id, entity_type) DO UPDATE SET
                                    new_id = EXCLUDED.new_id,
                                    updated_at = EXCLUDED.updated_at
                                """,
                                (
                                    str(source_guild_id),
                                    str(target_guild_id),
                                    old_id,
                                    new_id,
                                    entity_type,
                                    _utcnow(),
                                ),
                            )
                    cur.execute(
                        """
                        INSERT INTO global_id_mappings
                            (old_id, new_id, entity_type, source_guild_id, target_guild_id, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (old_id, entity_type) DO UPDATE SET
                            new_id = EXCLUDED.new_id,
                            source_guild_id = EXCLUDED.source_guild_id,
                            target_guild_id = EXCLUDED.target_guild_id,
                            updated_at = EXCLUDED.updated_at
                        """,
                        (
                            old_id,
                            new_id,
                            entity_type,
                            str(source_guild_id),
                            str(target_guild_id),
                            _utcnow(),
                        ),
                    )
                conn.commit()
        except Exception as e:
            self._last_error = str(e)

    def get_pair_mapping(
        self,
        old_id: str,
        entity_type: str,
        source_guild_id: str,
        target_guild_id: str,
        profile_name: str = "default",
    ) -> Optional[str]:
        if not self.enabled or not self.ensure_schema():
            return None
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    if source_guild_id and target_guild_id:
                        cur.execute(
                            """
                            SELECT new_id FROM pair_mapping_profiles
                            WHERE old_id = %s AND entity_type = %s
                              AND source_guild_id = %s AND target_guild_id = %s
                              AND profile_name = %s
                            """,
                            (
                                str(old_id),
                                entity_type,
                                str(source_guild_id),
                                str(target_guild_id),
                                profile_name or "default",
                            ),
                        )
                        row = cur.fetchone()
                        if row:
                            return row["new_id"]
                        if (profile_name or "default") == "default":
                            cur.execute(
                                """
                                SELECT new_id FROM pair_mappings
                                WHERE old_id = %s AND entity_type = %s
                                  AND source_guild_id = %s AND target_guild_id = %s
                                """,
                                (
                                    str(old_id),
                                    entity_type,
                                    str(source_guild_id),
                                    str(target_guild_id),
                                ),
                            )
                            row = cur.fetchone()
                            if row:
                                return row["new_id"]
                    cur.execute(
                        """
                        SELECT new_id FROM global_id_mappings
                        WHERE old_id = %s AND entity_type = %s
                        ORDER BY updated_at DESC
                        LIMIT 1
                        """,
                        (str(old_id), entity_type),
                    )
                    row = cur.fetchone()
                    return row["new_id"] if row else None
        except Exception:
            return None

    def load_pair_mappings(
        self, source_guild_id: str, target_guild_id: str, profile_name: str = "default"
    ) -> Dict[str, Dict[str, str]]:
        if not self.enabled or not self.ensure_schema():
            return {}
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT old_id, new_id, entity_type FROM pair_mapping_profiles
                        WHERE source_guild_id = %s AND target_guild_id = %s AND profile_name = %s
                        """,
                        (str(source_guild_id), str(target_guild_id), profile_name or "default"),
                    )
                    rows = cur.fetchall()
            out = {}
            for row in rows:
                out[str(row["old_id"])] = {
                    "new_id": str(row["new_id"]),
                    "type": row["entity_type"],
                }
            return out
        except Exception as e:
            _log_local(f"load_pair_mappings: {e}")
            return {}

    def get_global_mapping(self, old_id: str, entity_type: str = "role") -> Optional[str]:
        return self.get_pair_mapping(old_id, entity_type, "", "")

    def save_guild_snapshot(
        self,
        session_id: int,
        guild_id: str,
        snapshot_type: str,
        payload: Any,
    ) -> None:
        if not self.enabled or not session_id or not self.ensure_schema():
            return
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO guild_snapshots (session_id, guild_id, snapshot_type, payload)
                        VALUES (%s, %s, %s, %s::jsonb)
                        """,
                        (
                            session_id,
                            str(guild_id),
                            snapshot_type,
                            _json_dumps(payload),
                        ),
                    )
                conn.commit()
        except Exception as e:
            self._last_error = str(e)

    def import_json_cache(self, cache_path: str) -> int:
        if not self.enabled or not self.ensure_schema():
            return 0
        if not os.path.isfile(cache_path):
            return 0
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return 0
        mappings = data.get("mappings") or {}
        rows = []
        for old_id, info in mappings.items():
            if not isinstance(info, dict):
                continue
            new_id = info.get("new_id")
            entity_type = info.get("type") or "role"
            if new_id:
                rows.append((str(old_id), str(new_id), entity_type, "", "", _utcnow()))
        if not rows:
            return 0
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO global_id_mappings
                        (old_id, new_id, entity_type, source_guild_id, target_guild_id, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (old_id, entity_type) DO UPDATE SET
                        new_id = EXCLUDED.new_id,
                        updated_at = EXCLUDED.updated_at
                    """,
                    rows,
                )
            conn.commit()
        return len(rows)

    def save_genome(self, session_id: int, guild_id: str, genome_hash: str, genome_json: dict) -> None:
        if not self.enabled or not session_id:
            return
        if not self.ensure_schema():
            return
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO server_genomes (session_id, guild_id, genome_hash, genome_json)
                        VALUES (%s, %s, %s, %s::jsonb)
                        """,
                        (session_id, str(guild_id), genome_hash, _json_dumps(genome_json)),
                    )
                conn.commit()
        except Exception as e:
            self._last_error = str(e)

    def save_anomaly(
        self,
        session_id: int,
        kind: str,
        name: str,
        endpoint: str,
        payload: Any,
        error_text: str,
    ) -> Optional[int]:
        if not self.enabled or not session_id or not self.ensure_schema():
            return None
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO clone_anomalies (session_id, kind, name, endpoint, payload, error_text)
                        VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                        RETURNING id
                        """,
                        (
                            session_id,
                            kind,
                            name[:200],
                            endpoint[:500],
                            _json_dumps(payload or {}),
                            (error_text or "")[:2000],
                        ),
                    )
                    row = cur.fetchone()
                conn.commit()
            return int(row["id"]) if row else None
        except Exception as e:
            self._last_error = str(e)
            return None

    def list_anomalies(self, session_id: int, limit: int = 20) -> list:
        if not self.enabled or not self.ensure_schema():
            return []
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, kind, name, endpoint, error_text, created_at
                        FROM clone_anomalies
                        WHERE session_id = %s AND resolved_at IS NULL
                        ORDER BY id DESC LIMIT %s
                        """,
                        (session_id, limit),
                    )
                    return list(cur.fetchall())
        except Exception:
            return []

    def get_anomaly(self, anomaly_id: int) -> Optional[dict]:
        if not self.enabled or not self.ensure_schema():
            return None
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM clone_anomalies WHERE id = %s", (anomaly_id,))
                    return cur.fetchone()
        except Exception:
            return None

    def resolve_anomaly(self, anomaly_id: int) -> None:
        if not self.enabled or not self.ensure_schema():
            return
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE clone_anomalies SET resolved_at = %s WHERE id = %s",
                        (_utcnow(), anomaly_id),
                    )
                conn.commit()
        except Exception:
            pass

    def list_snapshots(self, guild_id: str, limit: int = 15) -> list:
        if not self.enabled or not self.ensure_schema():
            return []
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, session_id, snapshot_type, created_at
                        FROM guild_snapshots
                        WHERE guild_id = %s
                        ORDER BY id DESC LIMIT %s
                        """,
                        (str(guild_id), limit),
                    )
                    return list(cur.fetchall())
        except Exception:
            return []

    def get_snapshot_payload(self, snapshot_id: int) -> Optional[dict]:
        if not self.enabled or not self.ensure_schema():
            return None
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT payload FROM guild_snapshots WHERE id = %s",
                        (snapshot_id,),
                    )
                    row = cur.fetchone()
                    if row and row.get("payload"):
                        p = row["payload"]
                        return p if isinstance(p, dict) else json.loads(p)
        except Exception:
            pass
        return None

    def touch_shadow_sync(
        self, source_guild_id: str, target_guild_id: str, profile_name: str, genome_hash: str
    ) -> None:
        if not self.enabled or not self.ensure_schema():
            return
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO shadow_sync_state
                            (source_guild_id, target_guild_id, profile_name, last_genome_hash, last_sync_at)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (source_guild_id, target_guild_id, profile_name) DO UPDATE SET
                            last_genome_hash = EXCLUDED.last_genome_hash,
                            last_sync_at = EXCLUDED.last_sync_at
                        """,
                        (
                            str(source_guild_id),
                            str(target_guild_id),
                            profile_name or "default",
                            genome_hash,
                            _utcnow(),
                        ),
                    )
                conn.commit()
        except Exception as e:
            self._last_error = str(e)
