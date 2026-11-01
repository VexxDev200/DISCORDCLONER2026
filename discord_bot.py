#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vexx Cloner — Discord-бот: первый раз user token, дальше /clone из Neon.
"""

from __future__ import annotations

import asyncio
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional

import boot_db

boot_db.boot()

import discord
from discord import app_commands
from discord.ui import Button, Modal, TextInput, View

import bot_config
import bot_oauth
import bot_pending
import cloner_runner
from discordcloner import init_neon_store, persist_login
from oauth_server import start_oauth_server

_CFG = bot_config.load_bot_config()
_EXEC = ThreadPoolExecutor(max_workers=2, thread_name_prefix="clone")
_STORE = None


def _get_store():
    global _STORE
    if _STORE is None:
        _STORE = init_neon_store()
    return _STORE


def _schedule_after_oauth(discord_user_id: str) -> None:
    pending = bot_pending.pop_pending_clone(discord_user_id)
    if not pending:
        asyncio.run_coroutine_threadsafe(
            _notify_oauth_ok(discord_user_id),
            bot.loop,
        )
        return
    asyncio.run_coroutine_threadsafe(
        _run_pending_clone_dm(discord_user_id, pending),
        bot.loop,
    )


def _on_oauth_linked(
    discord_user_id: str,
    token_resp: dict,
    flow: Optional[dict] = None,
) -> None:
    store = _get_store()
    token, refresh, exp_ts = bot_oauth.store_token_payload(token_resp)
    me = bot_oauth.fetch_me(token_resp.get("access_token") or "")
    if not me:
        print(f"OAuth: users/@me failed for {discord_user_id}")
        return
    exp_dt = (
        datetime.fromtimestamp(exp_ts, tz=timezone.utc) if exp_ts else None
    )
    ok = store.upsert_account(
        discord_user_id,
        token,
        username=me.get("username") or "",
        global_name=me.get("global_name") or "",
        lang="ru",
        refresh_token=refresh,
        token_expires_at=exp_dt,
    )
    if not ok:
        print(f"OAuth: Neon save failed: {store.last_error}")
        return
    persist_login(store, discord_user_id, token, me, "ru")
    print(f"OAuth OK: {me.get('username')} ({discord_user_id})")
    if flow and flow.get("source_id") and flow.get("target_id"):
        bot_pending.set_pending_clone(
            discord_user_id,
            flow["source_id"],
            flow["target_id"],
            flow.get("strategy") or "2",
        )
    _schedule_after_oauth(discord_user_id)


class ClonerBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = False
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        registered = [c.name for c in self.tree.get_commands()]
        gid = bot_config.sync_guild_id(_CFG)
        if gid.isdigit():
            guild = discord.Object(id=int(gid))
            self.tree.copy_global_to(guild=guild)
            try:
                synced_guild = await self.tree.sync(guild=guild)
                gnames = [c.name for c in synced_guild]
                print(
                    f"Slash на сервере {gid} ({len(gnames)}): {', '.join(gnames)}"
                )
            except discord.Forbidden:
                print(
                    f"WARN: guild {gid} — бот не на сервере (50001). "
                    "Пригласи Patched Cloner на сервер или убери bot.sync_guild_id."
                )
            except discord.HTTPException as e:
                print(f"WARN: guild slash sync: {e}")
        try:
            synced = await self.tree.sync()
            names = [c.name for c in synced]
            print(f"Slash global ({len(names)}): {', '.join(names)}")
        except discord.HTTPException as e:
            print(f"WARN: global slash sync: {e}")
            names = registered
        if set(registered) - set(names):
            print(
                "На сервере команды могут обновиться до ~1ч (global). "
                "Для мгновенно: пригласи бота и sync_guild_id."
            )

    async def on_ready(self):
        print(f"Бот онлайн: {self.user} (id={self.user.id})")
        if not getattr(self, "_queue_started", False):
            self._queue_started = True
            asyncio.create_task(_clone_queue_loop())


bot = ClonerBot()


class UserTokenModal(Modal, title="Discord user token"):
    user_token = TextInput(
        label="User token (только ты видишь)",
        style=discord.TextStyle.paragraph,
        placeholder="См. /tokenhelp — ссылка на инструкцию DevTools",
        min_length=20,
        max_length=512,
        required=True,
    )

    async def _save(self, interaction: discord.Interaction) -> str:
        loop = asyncio.get_running_loop()
        raw = str(self.user_token.value).strip()

        def link():
            return cloner_runner.link_user_token(_get_store(), str(interaction.user.id), raw)

        return await loop.run_in_executor(_EXEC, link)


class SetTokenModal(UserTokenModal, title="Сменить user token"):
    user_token = TextInput(
        label="Новый user token",
        style=discord.TextStyle.paragraph,
        placeholder="Заменит сохранённый токен",
        min_length=20,
        max_length=512,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        uid = str(interaction.user.id)
        try:
            name = await self._save(interaction)
        except RuntimeError as e:
            if str(e) == "token_invalid":
                await interaction.followup.send("❌ Токен не прошёл проверку.", ephemeral=True)
            elif str(e).startswith("save_failed"):
                await interaction.followup.send(f"❌ Neon: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return

        pending = bot_pending.pop_pending_clone(uid)
        if pending:
            await interaction.followup.send(
                f"✅ Токен: **{name}**. Запускаю клон…",
                ephemeral=True,
            )
            await _run_clone_followup(
                interaction,
                pending.source_id,
                pending.target_id,
                pending.strategy,
            )
            return
        await interaction.followup.send(
            f"✅ Токен обновлён: **{name}**. Можно **`/clone`**.",
            ephemeral=True,
        )


class CloneTokenModal(UserTokenModal, title="Первый вход — user token"):
    def __init__(self, source_id: str, target_id: str, strategy: str):
        super().__init__()
        self._source_id = source_id.strip()
        self._target_id = target_id.strip()
        self._strategy = strategy

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            name = await self._save(interaction)
            await interaction.followup.send(
                f"✅ Сохранено: **{name}**. Запускаю клон…",
                ephemeral=True,
            )
        except RuntimeError as e:
            if str(e) == "token_invalid":
                await interaction.followup.send("❌ Токен не прошёл проверку.", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return
        await _run_clone_followup(
            interaction, self._source_id, self._target_id, self._strategy
        )


def _token_help_view() -> View:
    guide = bot_config.token_guide_url(_CFG)
    view = View(timeout=600)
    view.add_item(
        Button(
            style=discord.ButtonStyle.link,
            label="Discord в браузере",
            url="https://discord.com/app",
            emoji="🌐",
        )
    )
    view.add_item(
        Button(
            style=discord.ButtonStyle.link,
            label="Как найти token (F12)",
            url=guide,
            emoji="📋",
        )
    )
    return view


def _login_view(
    user_id: int,
    *,
    source_id: str = "",
    target_id: str = "",
    strategy: str = "2",
) -> View:
    url = bot_oauth.build_authorize_url(
        _CFG,
        str(user_id),
        _get_store(),
        source_id=source_id,
        target_id=target_id,
        strategy=strategy,
    )
    view = View(timeout=900)
    view.add_item(
        Button(
            style=discord.ButtonStyle.link,
            label="Authorize (один раз)",
            url=url,
            emoji="🔐",
        )
    )
    return view


def _oauth_user_hint() -> str:
    if bot_config.oauth_uses_worker(_CFG):
        return (
            "🆓 **Бесплатный OAuth** — Authorize с телефона или любого ПК.\n\n"
        )
    if bot_config.oauth_is_local(_CFG):
        return (
            "⚠️ Сейчас **localhost** — только ПК с ботом. "
            "Запусти **`SETUP_FREE_OAUTH.bat`** один раз (бесплатно, без домена).\n\n"
        )
    return "Authorize в браузере — с любого устройства.\n\n"


async def _clone_queue_loop() -> None:
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            jobs = await asyncio.get_running_loop().run_in_executor(
                _EXEC, lambda: _get_store().claim_clone_jobs(2)
            )
            for job in jobs:
                await _run_neon_clone_job(job)
        except Exception as e:
            print(f"clone queue: {e}")
        await asyncio.sleep(2)


async def _run_neon_clone_job(job: dict) -> None:
    job_id = int(job["id"])
    uid = str(job["discord_user_id"])
    source_id = str(job["source_id"])
    target_id = str(job["target_id"])
    strategy = str(job.get("strategy") or "2")
    try:
        user = await bot.fetch_user(int(uid))
    except Exception:
        user = None
    if user:
        try:
            await user.send("✅ **Authorize OK.** Клон из очереди…")
        except Exception:
            pass

    loop = asyncio.get_running_loop()

    def work():
        return cloner_runner.run_full_clone(
            uid, source_id, target_id, triad_strategy=strategy, lang_code="ru"
        )

    store = _get_store()
    try:
        label = await loop.run_in_executor(_EXEC, work)
        store.finish_clone_job(job_id, True)
        if user:
            await user.send(f"✅ **Клон завершён:** {label}")
    except Exception as e:
        store.finish_clone_job(job_id, False, str(e))
        if user:
            msg = str(e)
            if "guild_access" in msg:
                msg = (
                    "❌ **Нет доступа к серверам.**\n"
                    "OAuth не даёт права клонировать — добавь бота **Patched Cloner** на **оба** сервера.\n"
                    "На **target** — **Administrator**. Проверь ID source/target.\n"
                    f"`{msg}`"
                )
            else:
                msg = f"❌ Ошибка клона: {e}"
            await user.send(msg[:1900])
        traceback.print_exc()


async def _notify_oauth_ok(discord_user_id: str) -> None:
    try:
        user = await bot.fetch_user(int(discord_user_id))
        await user.send(
            "✅ **Аккаунт привязан.** Теперь можно **`/clone`** — токен больше не спрашиваю."
        )
    except Exception as e:
        print(f"DM after OAuth: {e}")


async def _run_pending_clone_dm(discord_user_id: str, pending: bot_pending.PendingClone) -> None:
    try:
        user = await bot.fetch_user(int(discord_user_id))
    except Exception as e:
        print(f"fetch_user {discord_user_id}: {e}")
        return
    try:
        await user.send("✅ **Authorize готов.** Запускаю клон… (может занять время)")
    except Exception:
        pass

    loop = asyncio.get_running_loop()

    def work():
        return cloner_runner.run_full_clone(
            discord_user_id,
            pending.source_id,
            pending.target_id,
            triad_strategy=pending.strategy,
            lang_code="ru",
        )

    try:
        label = await loop.run_in_executor(_EXEC, work)
        await user.send(f"✅ **Клон завершён:** {label}")
    except RuntimeError as e:
        code = str(e)
        if code == "guild_access":
            msg = "❌ Нет доступа к серверам или неверные ID."
        elif code == "token_invalid":
            msg = "❌ Токен сбился. `/login` → Authorize снова."
        else:
            msg = f"❌ {code}"
        await user.send(msg)
    except Exception as e:
        await user.send(f"❌ Ошибка клона: {e}")
        traceback.print_exc()


async def _run_clone_followup(
    interaction: discord.Interaction,
    source_id: str,
    target_id: str,
    strategy: str,
) -> None:
    loop = asyncio.get_running_loop()

    def work():
        return cloner_runner.run_full_clone(
            str(interaction.user.id),
            source_id.strip(),
            target_id.strip(),
            triad_strategy=strategy,
            lang_code="ru",
        )

    try:
        label = await loop.run_in_executor(_EXEC, work)
        await interaction.followup.send(f"✅ Клон завершён: **{label}**", ephemeral=True)
    except RuntimeError as e:
        code = str(e)
        if code == "not_linked":
            await interaction.followup.send(
                "❌ Нет user token. Повтори **`/clone`** — откроется форма.",
                ephemeral=True,
            )
        elif code == "token_invalid":
            await interaction.followup.send(
                "❌ Токен недействителен. **`/settoken`** — вставь новый.",
                ephemeral=True,
            )
        elif code == "guild_access":
            await interaction.followup.send(
                "❌ Нет доступа к серверам / неверные ID / токен без прав админа на target.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(f"❌ {code}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}", ephemeral=True)
        traceback.print_exc()


@bot.tree.command(name="start", description="Приветствие")
async def cmd_start(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    linked = await asyncio.get_running_loop().run_in_executor(
        _EXEC, lambda: cloner_runner.has_user_token(uid)
    )
    if linked:
        text = "**Vexx Cloner Bot**\n\nUser token уже сохранён. **`/clone`** source target."
    else:
        text = (
            "**Vexx Cloner Bot**\n\n"
            "1. **`/tokenhelp`** — ссылки: Discord + инструкция F12.\n"
            "2. **`/clone`** — вставь token один раз.\n"
            "Сменить: **`/settoken`**."
        )
    await interaction.response.send_message(text, view=_token_help_view(), ephemeral=True)


@bot.tree.command(name="tokenhelp", description="Ссылка: Discord + как скопировать token (F12)")
async def cmd_tokenhelp(interaction: discord.Interaction):
    guide = bot_config.token_guide_url(_CFG)
    await interaction.response.send_message(
        "**Шаги:** открой Discord в браузере → **F12** → **Network** → фильтр `auth` → "
        "**F5** → заголовок **authorization** → копируй → **`/clone`** или **`/settoken`**.\n\n"
        f"Подробно: {guide}",
        view=_token_help_view(),
        ephemeral=True,
    )


@bot.tree.command(name="settoken", description="Сменить сохранённый user token")
async def cmd_settoken(interaction: discord.Interaction):
    await interaction.response.send_modal(SetTokenModal())


@bot.tree.command(name="login", description="OAuth (опционально, клон через user token)")
async def cmd_login(interaction: discord.Interaction):
    await interaction.response.send_message(
        "Для клона нужен **user token**: **`/clone`** или **`/settoken`**.\n"
        "OAuth опционален:",
        view=_login_view(interaction.user.id),
        ephemeral=True,
    )


@bot.tree.command(name="status", description="Проверить привязку аккаунта")
async def cmd_status(interaction: discord.Interaction):
    store = _get_store()
    acc = store.get_last_account(str(interaction.user.id))
    if cloner_runner.get_stored_user_token(store, str(interaction.user.id)):
        await interaction.response.send_message(
            f"✅ User token: **{acc.get('global_name') or acc.get('username')}**",
            ephemeral=True,
        )
        return
    if acc and acc.get("token"):
        await interaction.response.send_message(
            "⚠️ Есть только OAuth — для клона нужен **user token**: **`/settoken`** или **`/clone`**.",
            ephemeral=True,
        )
        return
    await interaction.response.send_message(
        "❌ Токен не задан. **`/clone`** (форма) или **`/settoken`**.",
        ephemeral=True,
    )


@bot.tree.command(name="logout", description="Удалить сохранённый токен")
async def cmd_logout(interaction: discord.Interaction):
    store = _get_store()
    store.delete_account(str(interaction.user.id))
    bot_pending.clear_pending(str(interaction.user.id))
    await interaction.response.send_message(
        "🗑 User token удалён. Снова **`/clone`** или **`/settoken`**.",
        ephemeral=True,
    )


@bot.tree.command(name="clone", description="Полный клон source → target")
@app_commands.describe(
    source_id="ID исходного сервера",
    target_id="ID целевого сервера (нужны права админа)",
    strategy="Triad: 1=surgical 2=vanilla 3=hard",
)
async def cmd_clone(
    interaction: discord.Interaction,
    source_id: str,
    target_id: str,
    strategy: Optional[int] = 2,
):
    strat = str(strategy or 2)
    if strat not in ("1", "2", "3"):
        strat = "2"

    await interaction.response.defer(ephemeral=True, thinking=True)

    uid = str(interaction.user.id)
    loop = asyncio.get_running_loop()
    has_tok = await loop.run_in_executor(_EXEC, lambda: cloner_runner.has_user_token(uid))
    if not has_tok:
        bot_pending.set_pending_clone(uid, source_id, target_id, strat)
        await interaction.followup.send(
            "Нет user token.\n"
            "1. **`/tokenhelp`** — как скопировать token\n"
            "2. **`/settoken`** — вставь token → **клон стартанёт сам** (ID уже сохранены)",
            view=_token_help_view(),
            ephemeral=True,
        )
        return

    await _run_clone_followup(interaction, source_id, target_id, strat)


def main():
    missing = bot_config.validate_bot_config(_CFG)
    if missing:
        print("Заполни config.json → секция bot:")
        for k in missing:
            print(f"  - {k}")
        print("\nБесплатно для всех: запусти SETUP_FREE_OAUTH.bat")
        sys.exit(1)

    if bot_config.oauth_uses_worker(_CFG):
        print(f"OAuth (бесплатно): {_CFG.get('redirect_uri')}")
        print("Режим Worker — Authorize с любого устройства, бот крутится только у тебя.")
    else:
        start_oauth_server(_CFG, _on_oauth_linked, on_error=lambda m: print(f"OAuth: {m}"))
        print(f"OAuth redirect: {_CFG.get('redirect_uri')}")
        print("LOCAL — для всех без денег запусти: SETUP_FREE_OAUTH.bat")

    print("Neon: персональные токены; очередь клонов после Authorize.")

    bot.run(str(_CFG["token"]))


if __name__ == "__main__":
    main()
