#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
███████████████████████████████████████████████████████████████████████████████
█  VEXX CLONER — server clone + neon persistence                          █
█  ТЕПЕРЬ РАБОТАЕТ ИДЕАЛЬНО! КОПИРУЕТ АБСОЛЮТНО ВСЕ НАСТРОЙКИ РОЛЕЙ!    █
███████████████████████████████████████████████████████████████████████████████
"""

import boot_db

boot_db.boot()

import time
import json
import urllib.request
import urllib.error
import ssl
import os
import re
import sys
import base64
import hashlib
import threading
from datetime import datetime
from colorama import init, Fore, Style

from cloner_config import apply_file_config, save_default_config
from cloner_log import error as log_error, info as log_info, summary as log_summary
import cloner_media
import cloner_genome
import cloner_dsl
import cloner_ui
import cloner_extras
from neon_store import NeonStore


def fix_windows_console():
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


fix_windows_console()
init(autoreset=True)

# ======================================================================
# КОНФИГУРАЦИЯ
# ======================================================================

VERSION = "Vexx Cloner"
try:
    import vexx_version

    VERSION = f"Vexx Cloner · {vexx_version.__version__}"
except ImportError:
    vexx_version = None
AUTHOR = "𝐈 VexxDev 𝐈"

CONFIG = {
    "delay_min": 0.02,
    "delay_max": 0.08,
    "retry_attempts": 15,
    "save_cache": True,
    "cache_file": "god_clone_cache.json",
    "copy_emojis": True,
    "copy_stickers": True,
    "copy_webhooks": True,
    "copy_banner": True,
    "copy_icon": True,
    "copy_members": True,
    "copy_messages": False,
    "stealth_mode": True,
    "verbose": True,
    "use_neon_db": True,
    "database_url_file": "databaseneon.txt",
    "smart_sync": True,
    "full_wipe_before_clone": False,
    "role_boost_fallback": True,
    "dry_run": False,
    "resume": True,
    "console_quiet": False,
    "delete_orphans": False,
    "parallel_cdn_workers": 4,
    "preflight": True,
    "interactive_modules": True,
    "copy_settings": True,
    "copy_roles": True,
    "copy_channels": True,
    "copy_onboarding": True,
    "copy_automod": True,
    "copy_scheduled_events": True,
    "mapping_profile": "default",
    "turbo_mode": True,
    "genome_delta_only": False,
    "keep_role_colors": True,
    "role_icons_on_boost_only": True,
    "parallel_cdn_workers": 12,
}

apply_file_config(CONFIG)
save_default_config()
if CONFIG.get("turbo_mode"):
    CONFIG["delay_min"] = min(float(CONFIG.get("delay_min", 0.02)), 0.01)
    CONFIG["delay_max"] = min(float(CONFIG.get("delay_max", 0.08)), 0.04)

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# ======================================================================
# ПРАВА DISCORD (ПОЛНЫЙ СПИСОК)
# ======================================================================

PERMISSIONS = {
    "create_instant_invite": 0x0000000000000001,
    "kick_members": 0x0000000000000002,
    "ban_members": 0x0000000000000004,
    "administrator": 0x0000000000000008,
    "manage_channels": 0x0000000000000010,
    "manage_guild": 0x0000000000000020,
    "add_reactions": 0x0000000000000040,
    "view_audit_log": 0x0000000000000080,
    "priority_speaker": 0x0000000000000100,
    "stream": 0x0000000000000200,
    "view_channel": 0x0000000000000400,
    "send_messages": 0x0000000000000800,
    "send_tts_messages": 0x0000000000001000,
    "manage_messages": 0x0000000000002000,
    "embed_links": 0x0000000000004000,
    "attach_files": 0x0000000000008000,
    "read_message_history": 0x0000000000010000,
    "mention_everyone": 0x0000000000020000,
    "use_external_emojis": 0x0000000000040000,
    "view_guild_insights": 0x0000000000080000,
    "connect": 0x0000000000100000,
    "speak": 0x0000000000200000,
    "mute_members": 0x0000000000400000,
    "deafen_members": 0x0000000000800000,
    "move_members": 0x0000000001000000,
    "use_voice_activity": 0x0000000002000000,
    "change_nickname": 0x0000000004000000,
    "manage_nicknames": 0x0000000008000000,
    "manage_roles": 0x0000000010000000,
    "manage_webhooks": 0x0000000020000000,
    "manage_emojis_and_stickers": 0x0000000040000000,
    "use_application_commands": 0x0000000080000000,
    "request_to_speak": 0x0000000100000000,
    "manage_events": 0x0000000200000000,
    "manage_threads": 0x0000000400000000,
    "create_public_threads": 0x0000000800000000,
    "create_private_threads": 0x0000001000000000,
    "use_external_stickers": 0x0000002000000000,
    "send_messages_in_threads": 0x0000004000000000,
    "use_embedded_activities": 0x0000008000000000,
    "moderate_members": 0x0000010000000000
}

PERMISSION_NAMES_RU = {
    "create_instant_invite": "Создание приглашений",
    "kick_members": "Выгонять участников",
    "ban_members": "Банить участников",
    "administrator": "Администратор",
    "manage_channels": "Управление каналами",
    "manage_guild": "Управление сервером",
    "add_reactions": "Добавлять реакции",
    "view_audit_log": "Просмотр аудит-лога",
    "priority_speaker": "Приоритетный режим",
    "stream": "Стримить",
    "view_channel": "Просматривать каналы",
    "send_messages": "Отправлять сообщения",
    "send_tts_messages": "Отправлять TTS",
    "manage_messages": "Управлять сообщениями",
    "embed_links": "Встраивать ссылки",
    "attach_files": "Прикреплять файлы",
    "read_message_history": "Читать историю",
    "mention_everyone": "Упоминать @everyone",
    "use_external_emojis": "Использовать внешние эмодзи",
    "view_guild_insights": "Просмотр статистики",
    "connect": "Подключаться",
    "speak": "Говорить",
    "mute_members": "Отключать микрофон",
    "deafen_members": "Отключать звук",
    "move_members": "Перемещать участников",
    "use_voice_activity": "Использовать голосовую активность",
    "change_nickname": "Менять никнейм",
    "manage_nicknames": "Управлять никнеймами",
    "manage_roles": "Управлять ролями",
    "manage_webhooks": "Управлять вебхуками",
    "manage_emojis_and_stickers": "Управлять эмодзи/стикерами",
    "use_application_commands": "Использовать команды",
    "request_to_speak": "Запросить слово",
    "manage_events": "Управлять событиями",
    "manage_threads": "Управлять тредами",
    "create_public_threads": "Создавать публичные треды",
    "create_private_threads": "Создавать приватные треды",
    "use_external_stickers": "Использовать внешние стикеры",
    "send_messages_in_threads": "Отправлять в тредах",
    "use_embedded_activities": "Использовать активности",
    "moderate_members": "Модерировать участников"
}

PERMISSION_NAMES_EN = {
    "create_instant_invite": "Create Invite",
    "kick_members": "Kick Members",
    "ban_members": "Ban Members",
    "administrator": "Administrator",
    "manage_channels": "Manage Channels",
    "manage_guild": "Manage Server",
    "add_reactions": "Add Reactions",
    "view_audit_log": "View Audit Log",
    "priority_speaker": "Priority Speaker",
    "stream": "Stream",
    "view_channel": "View Channels",
    "send_messages": "Send Messages",
    "send_tts_messages": "Send TTS",
    "manage_messages": "Manage Messages",
    "embed_links": "Embed Links",
    "attach_files": "Attach Files",
    "read_message_history": "Read History",
    "mention_everyone": "Mention @everyone",
    "use_external_emojis": "Use External Emojis",
    "view_guild_insights": "View Insights",
    "connect": "Connect",
    "speak": "Speak",
    "mute_members": "Mute Members",
    "deafen_members": "Deafen Members",
    "move_members": "Move Members",
    "use_voice_activity": "Voice Activity",
    "change_nickname": "Change Nickname",
    "manage_nicknames": "Manage Nicknames",
    "manage_roles": "Manage Roles",
    "manage_webhooks": "Manage Webhooks",
    "manage_emojis_and_stickers": "Manage Emojis/Stickers",
    "use_application_commands": "Use Commands",
    "request_to_speak": "Request to Speak",
    "manage_events": "Manage Events",
    "manage_threads": "Manage Threads",
    "create_public_threads": "Create Public Threads",
    "create_private_threads": "Create Private Threads",
    "use_external_stickers": "Use External Stickers",
    "send_messages_in_threads": "Send in Threads",
    "use_embedded_activities": "Use Activities",
    "moderate_members": "Moderate Members"
}

# ======================================================================
# ЯЗЫКИ
# ======================================================================

class Language:
    def __init__(self, lang='ru'):
        self.lang = lang
        self.permission_names = PERMISSION_NAMES_RU if lang == 'ru' else PERMISSION_NAMES_EN
        self.strings = {
            'ru': {
                'token': '🔑 Введите ваш Discord токен: ',
                'invalid_token': '❌ Неверный токен!',
                'source_id': '📤 Введите ID исходного сервера: ',
                'target_id': '📥 Введите ID целевого сервера: ',
                'logged_in': '✅ Вход выполнен как',
                'source_server': '📌 Исходный сервер',
                'target_server': '📌 Целевой сервер',
                'confirm_clear': '⚡ Умная синхронизация (ничего не удаляется, только добавление/обновление). Начать? (y/n): ',
                'same_guild_error': '❌ Исходный и целевой сервер совпадают — укажи разные ID!',
                'cancelled': '❌ Операция отменена',
                'again': '🔄 Хотите клонировать другой сервер? (y/n): ',
                'clearing': '🧹 ОЧИСТКА СЕРВЕРА...',
                'clear_done': '✅ Очистка завершена',
                'copying_roles': '🎭 КОПИРОВАНИЕ РОЛЕЙ (ПОЛНОСТЬЮ)...',
                'copying_everyone': '  ⚙️ НАСТРОЙКА @EVERYONE:',
                'everyone_perms': '    ✅ @everyone: {count} прав',
                'copying_role': '  📋 КОПИРОВАНИЕ РОЛИ: @{name}',
                'role_name': '    📛 Название: {name}',
                'role_color': '    🎨 Цвет: {color}',
                'role_hoist': '    📌 Отображение отдельно: {hoist}',
                'role_mentionable': '    💬 Упоминаемая: {mentionable}',
                'role_perms': '    🔐 Все права ({count}):',
                'role_perm': '      ✅ {name}',
                'role_icon': '    🖼️ Иконка: {icon}',
                'role_position': '    📍 Позиция: {pos}',
                'role_created': '    ✅ РОЛЬ СОЗДАНА И НАСТРОЕНА!',
                'role_error': '    ❌ Ошибка: {error}',
                'sorting_roles': '  🔄 СОРТИРОВКА РОЛЕЙ ПО ПОЗИЦИЯМ...',
                'role_sorted': '    ✅ @{name} → позиция {pos}',
                'copying_channels': '📁 КОПИРОВАНИЕ КАНАЛОВ С ПРАВАМИ...',
                'creating_categories': '  📂 КАТЕГОРИИ:',
                'creating_category': '    📁 {name}',
                'category_perms': '      🔐 Права категории: {count}',
                'category_created': '      ✅ Создана',
                'creating_channels': '  📝 КАНАЛЫ:',
                'creating_channel': '    {type}: #{name}',
                'channel_perms': '      🔐 Права канала: {count}',
                'channel_created': '      ✅ Создан',
                'channel_error': '      ❌ Ошибка',
                'copying_emojis': '😄 КОПИРОВАНИЕ ЭМОДЗИ...',
                'emoji_copied': '  ✅ {name} скопирован',
                'copying_webhooks': '🔗 КОПИРОВАНИЕ ВЕБХУКОВ...',
                'webhook_copied': '  ✅ Вебхук: {name}',
                'copying_members': '👥 ОБРАБОТКА УЧАСТНИКОВ...',
                'member_processed': '  ✅ {name} обработан',
                'copying_banner': '🖼️ КОПИРОВАНИЕ БАННЕРА...',
                'banner_copied': '  ✅ Баннер скопирован',
                'copying_settings': '⚙️ КОПИРОВАНИЕ НАСТРОЕК...',
                'settings_copied': '  ✅ Настройки скопированы',
                'start_clone': '🚀 УМНАЯ СИНХРОНИЗАЦИЯ (без удаления)',
                'clone_complete': '🎉 КЛОНИРОВАНИЕ ЗАВЕРШЕНО!',
                'voice_channel': '🎤 Голосовой',
                'text_channel': '📝 Текстовый',
                'announce_channel': '📢 Анонсов',
                'stage_channel': '🎭 Сцена',
                'forum_channel': '💬 Форум',
                'stats': '📊 СТАТИСТИКА:',
                'stats_roles': '  🎭 Ролей скопировано: {count}',
                'stats_channels': '  📺 Каналов скопировано: {count}',
                'stats_emojis': '  😄 Эмодзи скопировано: {count}',
                'stats_webhooks': '  🔗 Вебхуков скопировано: {count}',
                'stats_members': '  👥 Участников обработано: {count}',
                'stats_perms': '  🔐 Всего прав скопировано: {count}',
                'stats_time': '  ⏱️ Время: {time}',
                'stats_errors': '  ❌ Ошибок: {count}',
            },
            'en': {
                'token': '🔑 Enter your Discord token: ',
                'invalid_token': '❌ Invalid token!',
                'source_id': '📤 Enter source server ID: ',
                'target_id': '📥 Enter target server ID: ',
                'logged_in': '✅ Logged in as',
                'source_server': '📌 Source server',
                'target_server': '📌 Target server',
                'confirm_clear': '⚡ Smart sync (no deletes, only add/update). Start? (y/n): ',
                'same_guild_error': '❌ Source and target are the same guild ID!',
                'cancelled': '❌ Operation cancelled',
                'again': '🔄 Clone another server? (y/n): ',
                'clearing': '🧹 CLEARING SERVER...',
                'clear_done': '✅ Clear complete',
                'copying_roles': '🎭 COPYING ROLES (FULL)...',
                'copying_everyone': '  ⚙️ CONFIGURING @EVERYONE:',
                'everyone_perms': '    ✅ @everyone: {count} permissions',
                'copying_role': '  📋 COPYING ROLE: @{name}',
                'role_name': '    📛 Name: {name}',
                'role_color': '    🎨 Color: {color}',
                'role_hoist': '    📌 Display separately: {hoist}',
                'role_mentionable': '    💬 Mentionable: {mentionable}',
                'role_perms': '    🔐 All permissions ({count}):',
                'role_perm': '      ✅ {name}',
                'role_icon': '    🖼️ Icon: {icon}',
                'role_position': '    📍 Position: {pos}',
                'role_created': '    ✅ ROLE CREATED AND CONFIGURED!',
                'role_error': '    ❌ Error: {error}',
                'sorting_roles': '  🔄 SORTING ROLES BY POSITION...',
                'role_sorted': '    ✅ @{name} → position {pos}',
                'copying_channels': '📁 COPYING CHANNELS WITH PERMISSIONS...',
                'creating_categories': '  📂 CATEGORIES:',
                'creating_category': '    📁 {name}',
                'category_perms': '      🔐 Category permissions: {count}',
                'category_created': '      ✅ Created',
                'creating_channels': '  📝 CHANNELS:',
                'creating_channel': '    {type}: #{name}',
                'channel_perms': '      🔐 Channel permissions: {count}',
                'channel_created': '      ✅ Created',
                'channel_error': '      ❌ Error',
                'copying_emojis': '😄 COPYING EMOJIS...',
                'emoji_copied': '  ✅ {name} copied',
                'copying_webhooks': '🔗 COPYING WEBHOOKS...',
                'webhook_copied': '  ✅ Webhook: {name}',
                'copying_members': '👥 PROCESSING MEMBERS...',
                'member_processed': '  ✅ {name} processed',
                'copying_banner': '🖼️ COPYING BANNER...',
                'banner_copied': '  ✅ Banner copied',
                'copying_settings': '⚙️ COPYING SETTINGS...',
                'settings_copied': '  ✅ Settings copied',
                'start_clone': '🚀 SMART SYNC (no wipe)',
                'clone_complete': '🎉 CLONING COMPLETED!',
                'voice_channel': '🎤 Voice',
                'text_channel': '📝 Text',
                'announce_channel': '📢 Announce',
                'stage_channel': '🎭 Stage',
                'forum_channel': '💬 Forum',
                'stats': '📊 STATISTICS:',
                'stats_roles': '  🎭 Roles copied: {count}',
                'stats_channels': '  📺 Channels copied: {count}',
                'stats_emojis': '  😄 Emojis copied: {count}',
                'stats_webhooks': '  🔗 Webhooks copied: {count}',
                'stats_members': '  👥 Members processed: {count}',
                'stats_perms': '  🔐 Total permissions copied: {count}',
                'stats_time': '  ⏱️ Time: {time}',
                'stats_errors': '  ❌ Errors: {count}',
            }
        }
    
    def get(self, key, **kwargs):
        text = self.strings[self.lang].get(key, key)
        if kwargs:
            text = text.format(**kwargs)
        return text

# ======================================================================
# БАННЕР
# ======================================================================

_BANNER_ANSI = re.compile(r"\033\[[0-9;]*m")

_BANNER_LINES = (
    "\033[0;31m \033[0;91m▄█\033[0;31m \033[0;91m█▀█\033[0;37m \033[0;31m \033[0;91m▄▀▀▀▀\033[0;31m█\033[0;37m \033[0;31m \033[0;91m▄\033[0;31m█ \033[0;91m█▀\033[0;31m█\033[0;37m \033[0;31m \033[0;91m▄\033[0;31m█ \033[0;91m█▀\033[0;31m█\033[0;37m \033[0;91m█▀▀▀▄\033[0;31m  \033[0;37m \033[0;31m \033[0;91m▄▀▀▀▀\033[0;31m█\033[0;37m \033[0;31m \033[0;91m▄█\033[0;31m \033[0;91m█▀█\033[0m",
    "\033[0;91;41m▓\033[0;31m █ █ █\033[0;37m \033[0;91;41m▓\033[0;31m ▄▀▀\033[0;90m▀▀\033[0;37m \033[0;91;41m▓\033[0;31m █ \033[0;91m█\033[0;31m █\033[0;37m \033[0;91;41m▓\033[0;31m █ \033[0;91m█\033[0;31m █\033[0;37m \033[0;91;41m▓\033[0;31m \033[0;90m█\033[0;31m▄ ▀▄\033[0;37m \033[0;91;41m▓\033[0;31m ▄▀▀\033[0;90m▀▀\033[0;37m \033[0;91;41m▓\033[0;31m █ █ █\033[0m",
    "\033[0;91;41m▒\033[0;31m \033[0;90m▓\033[0;31m \033[0;91m█\033[0;31m \033[0;90m█\033[0;37m \033[0;91;41m▒\033[0;31m \033[0;90;41m▄\033[0;91;41m▀▀\033[0;31m  \033[0;37m \033[0;91m▀▄\033[0;31m ▀ ▄▀\033[0;37m \033[0;91m▀▄\033[0;31m ▀ ▄▀\033[0;37m \033[0;91;41m▒\033[0;31m \033[0;90m█\033[0;31m \033[0;91m█\033[0;31m █\033[0;37m \033[0;91;41m▒\033[0;31m \033[0;90;41m▄\033[0;91;41m▀▀\033[0;31m  \033[0;37m \033[0;91;41m▒\033[0;31m \033[0;90m▓\033[0;31m \033[0;91m█\033[0;31m \033[0;90m█\033[0m",
    "\033[0;31m▐▌▀\033[0;91m▄▀\033[0;31m \033[0;90m█\033[0;37m \033[0;91;41m░\033[0;31m \033[0;90m█▄\033[0;31m▄▄\033[0;90m▄\033[0;37m \033[0;31m█ \033[0;90m▄▀▄\033[0;31m \033[0;90m█\033[0;37m \033[0;31m█ \033[0;90m▄▀▄\033[0;31m \033[0;90m█\033[0;37m \033[0;91;41m░\033[0;31m █\033[0;91m▀\033[0;31m \033[0;90m▄▀\033[0;37m \033[0;91;41m░\033[0;31m \033[0;90m█▄\033[0;31m▄▄\033[0;90m▄\033[0;37m \033[0;31m▐▌▀\033[0;91m▄▀\033[0;31m \033[0;90m█\033[0m",
    "\033[0;31m ▀\033[0;90m▄▄▄▀\033[0;31m \033[0;37m \033[0;31m█▄▄\033[0;90m▄▄▀\033[0;31m \033[0;37m \033[0;31m█\033[0;90m▄█\033[0;31m \033[0;90m█▀\033[0;31m \033[0;37m \033[0;31m█\033[0;90m▄█\033[0;31m \033[0;90m█▀\033[0;31m \033[0;37m \033[0;31m█▄▄\033[0;90m▄▀\033[0;31m  \033[0;37m \033[0;31m█▄▄\033[0;90m▄▄▀\033[0;31m \033[0;37m \033[0;31m ▀\033[0;90m▄▄▄▀\033[0;31m \033[0m",
)


def _banner_visible_len(line: str) -> int:
    return len(_BANNER_ANSI.sub("", line))


def _banner_center(line: str, cols: int) -> str:
    vis = _banner_visible_len(line)
    if vis >= cols:
        return line
    return " " * ((cols - vis) // 2) + line


def print_banner():
    if sys.platform == "win32":
        try:
            import ctypes
            h = ctypes.windll.kernel32.GetStdHandle(-11)
            ctypes.windll.kernel32.SetConsoleMode(h, 7)
        except Exception:
            pass
    try:
        cols = os.get_terminal_size().columns
    except OSError:
        cols = 100
    cols = max(cols, 72)
    art_w = max(_banner_visible_len(ln) for ln in _BANNER_LINES)
    pad_cols = min(cols, max(art_w + 4, 80))
    print()
    for line in _BANNER_LINES:
        print(_banner_center(line, pad_cols))
    print(Style.RESET_ALL)
    print(Fore.CYAN + f"  {VERSION}  ·  {AUTHOR}" + Style.RESET_ALL)
    print()

# ======================================================================
# DISCORD API 
# ======================================================================

def normalize_auth_token(token: str) -> str:
    """User token as-is; OAuth stored as oauth:ACCESS → Bearer."""
    t = (token or "").strip()
    if t.startswith("oauth:"):
        return f"Bearer {t[6:]}"
    if t.lower().startswith("bearer "):
        return t
    return t


class DiscordAPI:
    def __init__(self, token, *, bot_auth: bool = False):
        self.token = (token or "").strip()
        if bot_auth:
            raw = self.token
            if raw.lower().startswith("bot "):
                raw = raw[4:].strip()
            auth = f"Bot {raw}"
        else:
            auth = normalize_auth_token(self.token)
        self.headers = {
            "Authorization": auth,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        self.base_url = "https://discord.com/api/v10"
        self.delay = 0.2
        self.rate_limit_hits = 0
        self.total_requests = 0
        self.last_error = None
        self.read_only = False
        self.planned_writes = []
        self._rate_lock = threading.Lock()
        self._next_request_at = 0.0

    def _rate_wait(self):
        with self._rate_lock:
            now = time.time()
            if now < self._next_request_at:
                time.sleep(self._next_request_at - now)

    def _rate_update(self, headers):
        try:
            remaining = headers.get("X-RateLimit-Remaining") or headers.get(
                "x-ratelimit-remaining"
            )
            if remaining is not None and str(remaining) == "0":
                reset = headers.get("X-RateLimit-Reset-After") or headers.get(
                    "x-ratelimit-reset-after"
                )
                if reset is not None:
                    with self._rate_lock:
                        self._next_request_at = time.time() + float(reset) + 0.05
        except (TypeError, ValueError):
            pass

    def _json_body(self, payload):
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    def _format_http_error(self, code: int, raw: str) -> str:
        if raw:
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    msg = parsed.get("message") or parsed.get("code")
                    if msg:
                        return f"{code}: {msg}"
            except json.JSONDecodeError:
                pass
            return f"{code}: {raw[:300]}"
        return f"HTTP {code}"

    def _request(self, method, endpoint, payload=None, retry_count=0):
        url = f"{self.base_url}{endpoint}"
        self.total_requests += 1
        body = self._json_body(payload) if payload is not None else None

        try:
            self._rate_wait()
            req = urllib.request.Request(url, data=body, headers=self.headers, method=method)

            with urllib.request.urlopen(req, context=ssl_context, timeout=30) as r:
                self._rate_update(r.headers)
                self.last_error = None
                if r.status in [200, 201, 204]:
                    if r.status == 204:
                        return r.status, None
                    return r.status, json.loads(r.read().decode())
                return r.status, None

        except urllib.error.HTTPError as e:
            try:
                err_raw = e.read().decode("utf-8", errors="replace")
            except Exception:
                err_raw = ""
            self.last_error = self._format_http_error(e.code, err_raw)
            if e.code == 429:
                self.rate_limit_hits += 1
                try:
                    retry_after = json.loads(err_raw).get("retry_after", 3) if err_raw else 3
                except Exception:
                    retry_after = 3

                print(Fore.YELLOW + f"  ⚠️ Rate limit! Waiting {retry_after:.1f}s...")
                time.sleep(retry_after + 0.5)
                return self._request(method, endpoint, payload, retry_count + 1)

            elif e.code == 403:
                msg_low = err_raw.lower()
                try:
                    parsed = json.loads(err_raw)
                    if isinstance(parsed, dict) and parsed.get("message"):
                        msg_low = str(parsed["message"]).lower()
                except (json.JSONDecodeError, TypeError):
                    pass
                if not any(
                    k in msg_low
                    for k in ("boost", "буст", "nitro", "premium", "необхідно", "більше")
                ):
                    print(Fore.RED + "  ❌ Forbidden (недостаточно прав)")
                return e.code, None

            elif e.code == 404:
                return e.code, None

            else:
                if retry_count < CONFIG["retry_attempts"]:
                    time.sleep(1)
                    return self._request(method, endpoint, payload, retry_count + 1)
                return e.code, None

        except Exception as e:
            self.last_error = str(e)
            if retry_count < 3:
                time.sleep(2)
                return self._request(method, endpoint, payload, retry_count + 1)
            print(Fore.RED + f"  ❌ Ошибка: {e}")
            return None, None

    def get(self, endpoint):
        status, data = self._request("GET", endpoint)
        if CONFIG["stealth_mode"]:
            time.sleep(CONFIG["delay_min"])
        return data if status in [200, 201] else None

    def post(self, endpoint, data):
        if self.read_only:
            self.planned_writes.append(("POST", endpoint, data))
            return {"id": "dry-run", "name": (data or {}).get("name", "")}
        status, data = self._request("POST", endpoint, data)
        if CONFIG["stealth_mode"]:
            time.sleep(CONFIG["delay_min"])
        return data if status in [200, 201] else None

    def delete(self, endpoint):
        if self.read_only:
            self.planned_writes.append(("DELETE", endpoint, None))
            return
        self._request("DELETE", endpoint)
        if CONFIG["stealth_mode"]:
            time.sleep(CONFIG["delay_min"])

    def patch(self, endpoint, data):
        if self.read_only:
            self.planned_writes.append(("PATCH", endpoint, data))
            return data
        status, data = self._request("PATCH", endpoint, data)
        if CONFIG["stealth_mode"]:
            time.sleep(CONFIG["delay_min"])
        return data if status == 200 else None

    def put(self, endpoint, data=None):
        if self.read_only:
            self.planned_writes.append(("PUT", endpoint, data))
            return data
        status, data = self._request("PUT", endpoint, data)
        if CONFIG["stealth_mode"]:
            time.sleep(CONFIG["delay_min"])
        return data if status in [200, 201, 204] else None

# ======================================================================
# КЭШ
# ======================================================================

class CloneCache:
    def __init__(self, file="god_clone_cache.json", store=None, session_id=None,
                 source_guild_id="", target_guild_id=""):
        self.file = file
        self.store = store
        self.session_id = session_id
        self.source_guild_id = str(source_guild_id) if source_guild_id else ""
        self.target_guild_id = str(target_guild_id) if target_guild_id else ""
        self.data = self.load()
    
    def load(self):
        if os.path.exists(self.file):
            try:
                with open(self.file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save(self):
        try:
            with open(self.file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def set_mapping(self, old_id, new_id, type_name):
        if 'mappings' not in self.data:
            self.data['mappings'] = {}
        self.data['mappings'][old_id] = {'new_id': new_id, 'type': type_name}
        self.save()
        if self.store and self.store.enabled:
            self.store.save_mapping(
                self.session_id, old_id, new_id, type_name,
                self.source_guild_id, self.target_guild_id,
                profile_name=CONFIG.get("mapping_profile", "default"),
            )
    
    def get_mapping(self, old_id, type_name="role"):
        if 'mappings' in self.data:
            hit = self.data['mappings'].get(old_id, {}).get('new_id')
            if hit:
                return hit
        if self.store and self.store.enabled:
            return self.store.get_pair_mapping(
                old_id, type_name, self.source_guild_id, self.target_guild_id,
                profile_name=CONFIG.get("mapping_profile", "default"),
            )
        return None

# ======================================================================
# МЕГА-КЛОНЕР
# ======================================================================

class VexxCloner:
    def __init__(
        self,
        token,
        lang,
        store=None,
        session_id=None,
        discord_user_id="",
        source_guild_id="",
        target_guild_id="",
        api_bot_auth: bool = False,
    ):
        self.api = DiscordAPI(token, bot_auth=api_bot_auth)
        self.lang = lang
        self.store = store
        self.session_id = session_id
        self.discord_user_id = str(discord_user_id) if discord_user_id else ""
        self.source_guild_id = str(source_guild_id) if source_guild_id else ""
        self.target_guild_id = str(target_guild_id) if target_guild_id else ""
        self.role_map = {}
        self.category_map = {}
        self.channel_name_map = {}
        self.emoji_map = {}
        self._target_channels_cache = None
        self._dsl_roles = {}
        self._chimera_roles_override = None
        self._chimera_channels_extra = None
        self._snapshot_override = None
        from app_paths import data_path
        self.cache = CloneCache(
            data_path(CONFIG["cache_file"]),
            store=store,
            session_id=session_id,
            source_guild_id=source_guild_id,
            target_guild_id=target_guild_id,
        )
        self.total_perms_copied = 0
        self.stats = {
            'roles': 0,
            'channels': 0,
            'emojis': 0,
            'stickers': 0,
            'webhooks': 0,
            'members': 0,
            'errors': 0,
            'start_time': 0,
            'rate_limits': 0,
            'api_requests': 0,
            'roles_updated': 0,
            'channels_updated': 0,
            'roles_kept': 0,
            'channels_kept': 0,
            'failed_items': [],
            'dry_writes': 0,
            'onboarding': 0,
            'automod_rules': 0,
            'scheduled_events': 0,
            'orphans_removed': 0,
        }
        self._preload_pair_mappings()

    def _say(self, text, color=Fore.WHITE, force=False):
        log_info(text)
        if CONFIG.get("console_quiet") and not force:
            return
        print(color + text)

    def _fail(self, kind: str, name: str, reason: str, endpoint: str = "", payload=None):
        self.stats["errors"] += 1
        item = {"kind": kind, "name": name, "reason": (reason or "")[:500]}
        self.stats["failed_items"].append(item)
        log_error(f"{kind} {name}: {reason}")
        if self.store and self.store.enabled and self.session_id:
            aid = self.store.save_anomaly(
                self.session_id, kind, name, endpoint, payload or {}, reason
            )
            if aid:
                item["anomaly_id"] = aid

    def _target_channels(self, target_id, refresh=False):
        if refresh or self._target_channels_cache is None:
            self._target_channels_cache = self.api.get(f"/guilds/{target_id}/channels") or []
        return self._target_channels_cache

    def _record_genome(self, guild_id, session_label=""):
        roles = self.api.get(f"/guilds/{guild_id}/roles") or []
        channels = self.api.get(f"/guilds/{guild_id}/channels") or []
        emojis = self.api.get(f"/guilds/{guild_id}/emojis") or []
        genome = cloner_genome.build_genome(guild_id, roles, channels, emojis)
        gh = cloner_genome.genome_digest(genome)
        self.stats["genome_hash"] = gh
        if self.store and self.store.enabled and self.session_id:
            self.store.save_genome(self.session_id, guild_id, gh, genome)
        return genome, gh

    def shadow_sync(self, source_id, target_id):
        cloner_ui.section("Shadow Sync")
        src_g, _ = self._record_genome(source_id, "source")
        tgt_g, _ = self._record_genome(target_id, "target")
        pct, notes = cloner_genome.compare_genomes(src_g, tgt_g)
        cloner_ui.show_genome_result(pct)
        for n in notes[:12]:
            self._say(Fore.WHITE + "  · " + n)
        if pct >= 99.0:
            self._say(Fore.GREEN + "  ✅ Зеркало актуально", force=True)
            return
        self._say(Fore.YELLOW + "  ⚡ Пatching delta...", force=True)
        self.copy_everything(source_id, target_id)
        gh = self.stats.get("genome_hash", "")
        if self.store and self.store.enabled:
            self.store.touch_shadow_sync(
                source_id, target_id, CONFIG.get("mapping_profile", "default"), gh
            )

    def copy_chimera(self, source_a, source_b, target_id):
        cloner_ui.section("Chimera Merge")
        tag_a, tag_b = "A", "B"
        roles_a = self.api.get(f"/guilds/{source_a}/roles") or []
        roles_b = self.api.get(f"/guilds/{source_b}/roles") or []
        merged = []
        names = set()
        for r in roles_a:
            if r.get("managed") or r["name"] == "@everyone":
                continue
            nr = dict(r)
            nr["name"] = cloner_extras.chimera_role_name(r["name"], tag_a)
            merged.append(nr)
            names.add(nr["name"])
        for r in roles_b:
            if r.get("managed") or r["name"] == "@everyone":
                continue
            base = cloner_extras.chimera_role_name(r["name"], tag_b)
            if base in names:
                base = cloner_extras.chimera_role_name(r["name"] + "2", tag_b)
            nr = dict(r)
            nr["name"] = base
            merged.append(nr)
        self._chimera_roles_override = merged
        self.copy_everything(source_a, target_id)
        self._chimera_roles_override = None
        self._say(Fore.CYAN + "  Chimera pass B (channels prefix B)...", force=True)
        ch_b = self.api.get(f"/guilds/{source_b}/channels") or []
        for ch in ch_b:
            ch = dict(ch)
            ch["name"] = cloner_extras.chimera_role_name(ch["name"], tag_b)[:100]
        self._chimera_channels_extra = ch_b
        self.copy_channels(source_b, target_id)
        self._chimera_channels_extra = None

    def restore_from_snapshot(self, snapshot_id: int, target_id: int):
        if not self.store or not self.store.enabled:
            self._say(Fore.RED + "  Neon недоступен", force=True)
            return
        payload = self.store.get_snapshot_payload(snapshot_id)
        if not payload:
            self._say(Fore.RED + "  Снимок не найден", force=True)
            return
        gid = (payload.get("guild") or {}).get("id") or ""
        cloner_ui.section(f"Time Machine · snapshot #{snapshot_id}")
        self._snapshot_override = payload
        self.copy_roles(gid, target_id)
        self.copy_emojis(gid, target_id)
        self.copy_channels(gid, target_id)
        self._snapshot_override = None

    def retry_anomaly(self, anomaly_id: int):
        if not self.store:
            return
        row = self.store.get_anomaly(anomaly_id)
        if not row:
            self._say(Fore.RED + "  Anomaly не найдена", force=True)
            return
        ep = row.get("endpoint") or ""
        payload = row.get("payload") or {}
        if isinstance(payload, str):
            payload = json.loads(payload)
        if ep.startswith("POST "):
            path = ep[5:]
            res = self.api.post(path, payload)
        elif ep.startswith("PATCH "):
            path = ep[6:]
            res = self.api.patch(path, payload)
        else:
            self._say(Fore.RED + "  Неподдерживаемый endpoint", force=True)
            return
        if res:
            self.store.resolve_anomaly(anomaly_id)
            self._say(Fore.GREEN + f"  ✅ Anomaly #{anomaly_id} исправлена", force=True)
        else:
            self._say(Fore.RED + f"  ❌ {self.api.last_error}", force=True)

    def preflight(self, source_id, target_id):
        if not CONFIG.get("preflight", True):
            return True
        self._say(Fore.CYAN + "\n📋 Preflight — лимиты целевого сервера", force=True)
        tgt = self.api.get(f"/guilds/{target_id}?with_counts=true") or {}
        tier = int(tgt.get("premium_tier") or 0)
        src_roles = self.api.get(f"/guilds/{source_id}/roles") or []
        tgt_roles = self.api.get(f"/guilds/{target_id}/roles") or []
        src_emojis = self.api.get(f"/guilds/{source_id}/emojis") or []
        tgt_emojis = self.api.get(f"/guilds/{target_id}/emojis") or []
        src_stickers = self.api.get(f"/guilds/{source_id}/stickers") or []
        tgt_stickers = self.api.get(f"/guilds/{target_id}/stickers") or []
        role_cap = 250 if tier < 3 else 250
        emoji_cap = 50 + tier * 50
        sticker_cap = 5 + tier * 5
        need_roles = len([r for r in src_roles if r.get("name") != "@everyone" and not r.get("managed")])
        self._say(
            Fore.WHITE
            + f"  Буст: ур.{tier} | роли {len(tgt_roles)}/{role_cap} (нужно ~{need_roles}) | "
            f"emoji {len(tgt_emojis)}/{emoji_cap} | stickers {len(tgt_stickers)}/{sticker_cap}",
            force=True,
        )
        if tier < 2:
            self._say(
                Fore.YELLOW + "  Цвета/иконки ролей — только базовый вид (см. role_boost_fallback)",
                force=True,
            )
        if len(tgt_roles) + need_roles > role_cap + 5:
            self._say(Fore.YELLOW + "  ⚠️ Ролей может не хватить слотов на target", force=True)
        if len(tgt_emojis) + len(src_emojis) > emoji_cap:
            self._say(Fore.YELLOW + "  ⚠️ Emoji slots могут переполниться", force=True)
        return True

    def dry_run_report(self):
        n = len(self.api.planned_writes)
        self.stats["dry_writes"] = n
        self._say(Fore.MAGENTA + f"\n══ Dry-run: запланировано изменений: {n} ══", force=True)
        for method, ep, payload in self.api.planned_writes[:40]:
            name = (payload or {}).get("name", "") if isinstance(payload, dict) else ""
            self._say(Fore.WHITE + f"  {method} {ep} {name}", force=True)
        if n > 40:
            self._say(Fore.WHITE + f"  ... ещё {n - 40}", force=True)

    def remove_orphans(self, source_id, target_id):
        if not CONFIG.get("delete_orphans") or self.api.read_only:
            return
        self._say(Fore.YELLOW + "\n🧹 Удаление лишних ролей/каналов на target (нет на source)...", force=True)
        src_roles = self.api.get(f"/guilds/{source_id}/roles") or []
        src_names = {r["name"] for r in src_roles if r.get("name") != "@everyone"}
        tgt_roles = self.api.get(f"/guilds/{target_id}/roles") or []
        for r in tgt_roles:
            if r.get("managed") or r["name"] == "@everyone":
                continue
            if r["name"] not in src_names:
                self.api.delete(f"/guilds/{target_id}/roles/{r['id']}")
                self.stats["orphans_removed"] += 1
                self._say(Fore.WHITE + f"  🗑️ роль @{r['name']}")
        src_ch = self.api.get(f"/guilds/{source_id}/channels") or []
        src_ch_names = {(c["type"], c["name"]) for c in src_ch}
        tgt_ch = self.api.get(f"/guilds/{target_id}/channels") or []
        for c in tgt_ch:
            key = (c["type"], c["name"])
            if key not in src_ch_names:
                self.api.delete(f"/channels/{c['id']}")
                self.stats["orphans_removed"] += 1
                self._say(Fore.WHITE + f"  🗑️ канал {c['name']}")

    def copy_onboarding(self, source_id, target_id):
        if not CONFIG.get("copy_onboarding", True):
            return
        src = self.api.get(f"/guilds/{source_id}/onboarding")
        if not src:
            return
        self._say(Fore.CYAN + "\n📋 Onboarding...", force=True)
        payload = {
            k: src[k]
            for k in ("prompts_enabled", "default_channel_ids", "mode", "enabled")
            if k in src
        }
        if not payload:
            return
        if self.api.put(f"/guilds/{target_id}/onboarding", payload):
            self.stats["onboarding"] = 1
            self._say(Fore.GREEN + "  ✅ Onboarding", force=True)
        else:
            self._fail("onboarding", str(target_id), self.api.last_error or "fail")

    def copy_automod(self, source_id, target_id):
        if not CONFIG.get("copy_automod", True):
            return
        rules = self.api.get(f"/guilds/{source_id}/auto-moderation/rules") or []
        if not rules:
            return
        self._say(Fore.CYAN + f"\n🛡️ AutoMod ({len(rules)} правил)...", force=True)
        for rule in rules:
            body = {
                k: rule[k]
                for k in (
                    "name",
                    "event_type",
                    "trigger_type",
                    "trigger_metadata",
                    "actions",
                    "enabled",
                    "exempt_roles",
                    "exempt_channels",
                )
                if k in rule
            }
            body["name"] = (body.get("name") or "rule")[:100]
            created = self.api.post(f"/guilds/{target_id}/auto-moderation/rules", body)
            if created:
                self.stats["automod_rules"] += 1
            else:
                self._fail("automod", body.get("name", "?"), self.api.last_error or "fail")

    def copy_scheduled_events(self, source_id, target_id):
        if not CONFIG.get("copy_scheduled_events", True):
            return
        events = self.api.get(f"/guilds/{source_id}/scheduled-events") or []
        if not events:
            return
        self._say(Fore.CYAN + f"\n📅 Events ({len(events)})...", force=True)
        for ev in events:
            body = {
                k: ev[k]
                for k in (
                    "name",
                    "description",
                    "scheduled_start_time",
                    "scheduled_end_time",
                    "privacy_level",
                    "entity_type",
                    "channel_id",
                )
                if k in ev and ev[k] is not None
            }
            if body.get("channel_id"):
                mapped = self.channel_name_map.get(str(body["channel_id"]))
                if mapped:
                    body["channel_id"] = mapped
                else:
                    body.pop("channel_id", None)
            created = self.api.post(f"/guilds/{target_id}/scheduled-events", body)
            if created:
                self.stats["scheduled_events"] += 1
            else:
                self._fail("event", body.get("name", "?"), self.api.last_error or "fail")

    def _preload_pair_mappings(self):
        if not (self.store and self.store.enabled):
            return
        maps = self.store.load_pair_mappings(
            self.source_guild_id,
            self.target_guild_id,
            profile_name=CONFIG.get("mapping_profile", "default"),
        )
        if not maps:
            return
        self.cache.data.setdefault("mappings", {})
        self.cache.data["mappings"].update(maps)

    def _db_log(self, level, message, **meta):
        if self.store and self.store.enabled and self.session_id:
            self.store.log(self.session_id, level, message, meta or None)

    def _snapshot_guild(self, guild_id, snapshot_type):
        if not (self.store and self.store.enabled and self.session_id):
            return
        payload = {
            "guild": self.api.get(f"/guilds/{guild_id}"),
            "roles": self.api.get(f"/guilds/{guild_id}/roles"),
            "channels": self.api.get(f"/guilds/{guild_id}/channels"),
            "emojis": self.api.get(f"/guilds/{guild_id}/emojis"),
            "stickers": self.api.get(f"/guilds/{guild_id}/stickers"),
        }
        self.store.save_guild_snapshot(self.session_id, guild_id, snapshot_type, payload)
        self._db_log("info", f"Snapshot saved: {snapshot_type}", guild_id=guild_id)

    def print_progress(self, text, color=Fore.GREEN):
        print(color + f"  {text}")

    def clear_server(self, guild_id):
        """СУПЕР-ОЧИСТКА"""
        print(Fore.YELLOW + f"\n{self.lang.get('clearing')}")
        
        # Удаляем каналы
        channels = self.api.get(f"/guilds/{guild_id}/channels") or []
        for ch in reversed(channels):
            print(Fore.YELLOW + f"  🗑️ Удаление: #{ch['name']} ({ch['id']})")
            self.api.delete(f"/channels/{ch['id']}")
        
        # Удаляем роли
        roles = self.api.get(f"/guilds/{guild_id}/roles") or []
        for role in sorted(roles, key=lambda x: x['position'], reverse=True):
            if not role.get('managed', False) and role['name'] != '@everyone':
                print(Fore.YELLOW + f"  🗑️ Удаление роли: @{role['name']} ({role['id']})")
                self.api.delete(f"/guilds/{guild_id}/roles/{role['id']}")
        
        print(Fore.GREEN + self.lang.get('clear_done'))

    def get_permission_names(self, permissions_int):
        """Получение списка включенных прав - ИСПРАВЛЕНО!"""
        # Конвертируем в int если пришла строка
        if isinstance(permissions_int, str):
            try:
                permissions_int = int(permissions_int)
            except:
                permissions_int = 0
        
        perms = []
        for perm_name, perm_value in PERMISSIONS.items():
            if permissions_int & perm_value:
                # Получаем название на выбранном языке
                name = self.lang.permission_names.get(perm_name, perm_name)
                perms.append(name)
        return perms

    def _resolve_target_role_id(self, source_role, target_id):
        sid = str(source_role["id"])
        mapped = self.cache.get_mapping(sid, "role")
        target_roles = self.api.get(f"/guilds/{target_id}/roles") or []
        if mapped and any(str(r["id"]) == str(mapped) for r in target_roles):
            return str(mapped)
        for tr in target_roles:
            if tr.get("managed") or tr["name"] == "@everyone":
                continue
            if tr["name"] == source_role["name"]:
                self.cache.set_mapping(sid, tr["id"], "role")
                return str(tr["id"])
        return None

    def _role_icon_data_uri(self, guild_id, role):
        icon_hash = role.get("icon")
        if not icon_hash or not isinstance(icon_hash, str):
            return None
        return cloner_media.role_icon_uri(str(role["id"]), icon_hash)

    def _map_forum_tags(self, tags):
        if not tags:
            return tags
        out = []
        for tag in tags:
            t = dict(tag)
            eid = t.get("emoji_id")
            if eid is not None:
                mapped = self.emoji_map.get(str(eid))
                if mapped:
                    t["emoji_id"] = mapped
            out.append(t)
        return out

    def _role_payload(self, role, source_guild_id=None):
        perms = role.get("permissions", 0)
        data = {
            "name": role["name"],
            "permissions": str(perms),
            "color": int(role.get("color") or 0),
            "hoist": role.get("hoist", False),
            "mentionable": role.get("mentionable", False),
        }
        dsl = getattr(self, "_dsl_roles", {}).get(role["name"])
        if dsl:
            data.update({k: v for k, v in dsl.items() if k in ("permissions", "hoist", "mentionable", "color")})
        uni = role.get("unicode_emoji")
        if uni:
            data["unicode_emoji"] = uni
        tier = getattr(self, "_target_premium_tier", 3)
        icons_ok = tier >= 2 or not CONFIG.get("role_icons_on_boost_only", True)
        if source_guild_id and role.get("icon") and icons_ok:
            icon_uri = self._role_icon_data_uri(source_guild_id, role)
            if icon_uri:
                data["icon"] = icon_uri
        return data

    @staticmethod
    def _is_boost_limit_error(err: str) -> bool:
        if not err:
            return False
        low = err.lower()
        if low.startswith("403") or "http 403" in low:
            return True
        return any(
            k in low
            for k in (
                "boost",
                "буст",
                "бустів",
                "nitro",
                "premium",
                "рівень",
                "рівня",
                "більше",
                "необхідно",
            )
        )

    def _strip_boost_role_extras(self, data: dict, strip_color: bool = False) -> dict:
        out = dict(data)
        out.pop("icon", None)
        out.pop("unicode_emoji", None)
        out.pop("colors", None)
        if strip_color:
            out["color"] = 0
        return out

    def _strip_role_icons_only(self, data: dict) -> dict:
        out = dict(data)
        out.pop("icon", None)
        out.pop("unicode_emoji", None)
        out.pop("colors", None)
        return out

    def _role_payload_minimal(self, data: dict) -> dict:
        return {
            "name": str(data.get("name", "role"))[:100],
            "permissions": str(data.get("permissions", "0")),
            "color": int(data.get("color") or 0),
            "hoist": False,
            "mentionable": bool(data.get("mentionable", False)),
        }

    def _role_payload_variants(self, role_data: dict) -> list:
        variants = [role_data]
        if not CONFIG.get("role_boost_fallback", True):
            return variants
        slim = self._strip_role_icons_only(role_data)
        minimal = self._role_payload_minimal(role_data)
        no_color = self._strip_boost_role_extras(role_data, strip_color=True)
        seen = {json.dumps(role_data, sort_keys=True)}
        for item in (slim, minimal, no_color):
            key = json.dumps(item, sort_keys=True)
            if key not in seen:
                seen.add(key)
                variants.append(item)
        return variants

    def _save_role(self, target_id, source_role_id, role_data, existing_id=None):
        base = f"/guilds/{target_id}/roles"
        variants = self._role_payload_variants(role_data)
        warned = False

        for idx, payload in enumerate(variants):
            if existing_id:
                result = self.api.patch(f"{base}/{existing_id}", payload)
                if result:
                    return result, existing_id, idx > 0
            else:
                result = self.api.post(base, payload)
                if result:
                    return result, result["id"], idx > 0

            err = self.api.last_error or ""
            if idx + 1 < len(variants) and self._is_boost_limit_error(err):
                if not warned:
                    print(
                        Fore.YELLOW
                        + "    ⚠️ Бустов мало — пробуем роль без оформления/упрощённую"
                    )
                    warned = True
                continue
            break

        return None, existing_id, warned

    def _find_target_channel(self, source_ch, target_channels):
        sid = str(source_ch["id"])
        mapped = self.cache.get_mapping(sid, "channel" if source_ch["type"] != 4 else "category")
        if mapped:
            for t in target_channels:
                if str(t["id"]) == str(mapped):
                    return t
        want_parent = None
        if source_ch.get("parent_id"):
            want_parent = self.category_map.get(source_ch["parent_id"])
        for t in target_channels:
            if t["type"] != source_ch["type"] or t["name"] != source_ch["name"]:
                continue
            if want_parent and str(t.get("parent_id") or "") != str(want_parent):
                continue
            if not want_parent and t.get("parent_id") and source_ch["type"] != 4:
                continue
            et = "category" if source_ch["type"] == 4 else "channel"
            self.cache.set_mapping(sid, t["id"], et)
            return t
        return None

    def copy_roles(self, source_id, target_id):
        """МЕГА-КОПИРОВАНИЕ РОЛЕЙ СО ВСЕМИ НАСТРОЙКАМИ"""
        if not CONFIG.get("copy_roles", True):
            return
        print(Fore.CYAN + f"\n{self.lang.get('copying_roles')}")

        target_guild = self.api.get(f"/guilds/{target_id}") or {}
        self._target_premium_tier = int(target_guild.get("premium_tier") or 0)
        if self._target_premium_tier < 2 and CONFIG.get("role_boost_fallback", True):
            print(
                Fore.YELLOW
                + f"  ℹ️ Бустов сервера: ур.{self._target_premium_tier} — иконки ролей пропускаем, цвета копируем"
            )

        override = getattr(self, "_chimera_roles_override", None)
        snap = getattr(self, "_snapshot_override", None)
        if override is not None:
            source_roles = override
        elif snap:
            source_roles = snap.get("roles") or []
        else:
            source_roles = self.api.get(f"/guilds/{source_id}/roles") or []
        self._dsl_roles = cloner_dsl.load_roles_dsl(perm_map=PERMISSIONS)
        source_roles_sorted = sorted(source_roles, key=lambda x: x['position'], reverse=True)
        
        # ================================================================
        # 1. НАСТРОЙКА @EVERYONE
        # ================================================================
        print(Fore.YELLOW + self.lang.get('copying_everyone'))
        
        for role in source_roles_sorted:
            if role['name'] == '@everyone':
                target_roles = self.api.get(f"/guilds/{target_id}/roles") or []
                for t_role in target_roles:
                    if t_role['name'] == '@everyone':
                        # Копируем ВСЕ права @everyone
                        perms = role.get('permissions', 0)
                        result = self.api.patch(f"/guilds/{target_id}/roles/{t_role['id']}", {
                            "permissions": str(perms),
                            "color": role.get('color', 0)
                        })
                        if result:
                            # Показываем все права @everyone
                            perm_list = self.get_permission_names(perms)
                            print(Fore.GREEN + f"    ✅ @everyone: {len(perm_list)} прав")
                            for p in perm_list[:10]:
                                print(Fore.WHITE + f"      • {p}")
                            if len(perm_list) > 10:
                                print(Fore.WHITE + f"      • ... и ещё {len(perm_list)-10} прав")
                        self.role_map[role['id']] = t_role['id']
                        break
                break
        
        # ================================================================
        # 2. КОПИРОВАНИЕ ВСЕХ РОЛЕЙ
        # ================================================================
        
        roles_to_create = [r for r in source_roles_sorted if not r.get('managed', False) and r['name'] != '@everyone']
        total_roles = len(roles_to_create)
        
        for idx, role in enumerate(roles_to_create, 1):
            cloner_ui.progress("Роли", idx, total_roles)
            print(Fore.YELLOW + f"\n{self.lang.get('copying_role', name=role['name'])}")
            
            existing_id = self._resolve_target_role_id(role, target_id)
            if CONFIG.get("resume") and existing_id:
                self._say(
                    Fore.CYAN + f"    ↪ Resume: @{role['name']} → ID {existing_id}",
                    force=False,
                )
            # ПОЛНАЯ ИНФОРМАЦИЯ О РОЛИ
            # ============================================================
            
            # Название
            print(Fore.WHITE + self.lang.get('role_name', name=role['name']))
            
            # Цвет
            color_hex = f"#{role['color']:06x}" if role.get('color', 0) > 0 else "none"
            print(Fore.WHITE + self.lang.get('role_color', color=color_hex))
            
            # Отображение отдельно
            print(Fore.WHITE + self.lang.get('role_hoist', hoist=role.get('hoist', False)))
            
            # Упоминаемость
            print(Fore.WHITE + self.lang.get('role_mentionable', mentionable=role.get('mentionable', False)))
            
            # Позиция
            print(Fore.WHITE + self.lang.get('role_position', pos=role.get('position', 0)))
            
            # Иконка
            icon_status = "✅ есть" if role.get('icon') else "❌ нет"
            print(Fore.WHITE + self.lang.get('role_icon', icon=icon_status))
            
            # ============================================================
            # ВСЕ ПРАВА РОЛИ (ПОЛНЫЙ СПИСОК)
            # ============================================================
            perms = role.get('permissions', 0)
            perm_list = self.get_permission_names(perms)
            
            print(Fore.WHITE + self.lang.get('role_perms', count=len(perm_list)))
            if not CONFIG.get("console_quiet"):
                for p in perm_list:
                    print(Fore.CYAN + f"      ✅ {p}")
            
            self.total_perms_copied += len(perm_list)
            
            try:
                role_data = self._role_payload(role, source_guild_id=source_id)
            except Exception as e:
                self.stats["errors"] += 1
                print(Fore.RED + self.lang.get("role_error", error=str(e)))
                continue

            saved, new_id, used_fallback = self._save_role(
                target_id, role["id"], role_data, existing_id=existing_id
            )
            if saved and new_id:
                self.role_map[role["id"]] = new_id
                if not existing_id:
                    self.cache.set_mapping(role["id"], new_id, "role")
                    self.stats["roles"] += 1
                    print(Fore.GREEN + self.lang.get("role_created"))
                    print(Fore.GREEN + f"    🆔 Новый ID: {new_id}")
                else:
                    self.stats["roles_kept"] += 1
                    self.stats["roles_updated"] += 1
                    note = " (без буст-оформления)" if used_fallback else ""
                    print(Fore.GREEN + f"    ✅ Роль уже есть — обновлена (ID: {new_id}){note}")
                continue

            if existing_id:
                self.role_map[role["id"]] = existing_id
                self.stats["roles_kept"] += 1
                err = self.api.last_error or "без изменений"
                if self.api.last_error:
                    self.stats["errors"] += 1
                    print(Fore.RED + self.lang.get("role_error", error=err))
                else:
                    print(Fore.CYAN + f"    ↪ Роль без изменений (ID: {existing_id})")
            else:
                self.stats["errors"] += 1
                err = self.api.last_error or "Неизвестная ошибка"
                print(Fore.RED + self.lang.get("role_error", error=err))
        
        # ================================================================
        # 3. СОРТИРОВКА РОЛЕЙ ПО ПОЗИЦИЯМ
        # ================================================================
        if self.role_map:
            print(Fore.YELLOW + f"\n{self.lang.get('sorting_roles')}")
            
            # Сортируем по исходным позициям
            sorted_roles = []
            for role in source_roles_sorted:
                if role['name'] != '@everyone' and not role.get('managed', False):
                    new_id = self.role_map.get(role['id'])
                    if new_id:
                        sorted_roles.append({
                            'name': role['name'],
                            'id': new_id,
                            'position': role['position']
                        })
            
            sorted_roles.sort(key=lambda x: x['position'], reverse=True)
            
            current_pos = 1
            for role_info in sorted_roles:
                result = self.api.patch(f"/guilds/{target_id}/roles/{role_info['id']}", {
                    "position": current_pos
                })
                if result:
                    print(Fore.GREEN + self.lang.get('role_sorted', name=role_info['name'], pos=current_pos))
                    current_pos += 1
                time.sleep(0.1)

    def _convert_overwrites(self, overwrites):
        """Конвертация прав с полным маппингом ролей"""
        result = []
        for ow in overwrites:
            ow_id = ow['id']
            if ow['type'] == 0 and ow_id in self.role_map:
                ow_id = self.role_map[ow_id]
            result.append({
                "id": ow_id,
                "type": ow['type'],
                "allow": str(ow['allow']),
                "deny": str(ow['deny'])
            })
        return result

    def copy_channels(self, source_id, target_id):
        """КОПИРОВАНИЕ КАНАЛОВ С ПРАВАМИ"""
        if not CONFIG.get("copy_channels", True):
            return
        print(Fore.CYAN + f"\n{self.lang.get('copying_channels')}")

        channels = self.api.get(f"/guilds/{source_id}/channels") or []
        extra = getattr(self, "_chimera_channels_extra", None)
        if extra:
            channels = list(channels) + list(extra)
        snap = getattr(self, "_snapshot_override", None)
        if snap:
            channels = snap.get("channels") or channels
        target_channels = self._target_channels(target_id, refresh=True)
        
        # ================================================================
        # 1. КАТЕГОРИИ
        # ================================================================
        categories = [c for c in channels if c['type'] == 4]
        categories.sort(key=lambda x: x['position'])

        print(Fore.YELLOW + self.lang.get('creating_categories'))
        for cat in categories:
            print(Fore.YELLOW + self.lang.get('creating_category', name=cat['name']))
            
            overwrites = self._convert_overwrites(cat.get('permission_overwrites', []))
            print(Fore.WHITE + self.lang.get('category_perms', count=len(overwrites)))
            cat_payload = {
                "name": cat['name'],
                "type": 4,
                "position": cat['position'],
                "permission_overwrites": overwrites,
            }
            existing = self._find_target_channel(cat, target_channels)
            if existing:
                self.category_map[cat['id']] = existing['id']
                patched = self.api.patch(f"/channels/{existing['id']}", cat_payload)
                self.stats['channels_kept'] += 1
                if patched:
                    self.stats['channels_updated'] += 1
                    print(Fore.GREEN + f"      ✅ Категория обновлена: {cat['name']}")
                else:
                    print(Fore.CYAN + f"      ↪ Категория без изменений: {cat['name']}")
                continue

            new_cat = self.api.post(f"/guilds/{target_id}/channels", cat_payload)
            if new_cat:
                self.category_map[cat['id']] = new_cat['id']
                self.cache.set_mapping(cat['id'], new_cat['id'], 'category')
                target_channels.append(new_cat)
                self.stats['channels'] += 1
                print(Fore.GREEN + self.lang.get('category_created'))
            else:
                self.stats['errors'] += 1
        
        # ================================================================
        # 2. ВСЕ КАНАЛЫ
        # ================================================================
        other = [c for c in channels if c['type'] != 4]
        other.sort(key=lambda x: x['position'])
        
        print(Fore.YELLOW + self.lang.get('creating_channels'))
        for ch in other:
            type_map = {
                0: self.lang.get('text_channel'),
                2: self.lang.get('voice_channel'),
                5: self.lang.get('announce_channel'),
                13: self.lang.get('stage_channel'),
                15: self.lang.get('forum_channel')
            }
            type_name = type_map.get(ch['type'], "Unknown")
            
            print(Fore.YELLOW + self.lang.get('creating_channel', type=type_name, name=ch['name']))
            
            # Права канала
            overwrites = self._convert_overwrites(ch.get('permission_overwrites', []))
            print(Fore.WHITE + self.lang.get('channel_perms', count=len(overwrites)))
            
            # Базовые данные
            ch_data = {
                "name": ch['name'],
                "type": ch['type'],
                "position": ch['position'],
                "permission_overwrites": overwrites
            }
            
            # Категория
            if ch.get('parent_id') and ch['parent_id'] in self.category_map:
                ch_data["parent_id"] = self.category_map[ch['parent_id']]
            
            # Специфичные настройки
            if ch['type'] == 0:
                if ch.get('topic'):
                    ch_data["topic"] = ch['topic']
                ch_data["nsfw"] = ch.get('nsfw', False)
                ch_data["rate_limit_per_user"] = ch.get('rate_limit_per_user', 0)
                if ch.get('default_auto_archive_duration'):
                    ch_data["default_auto_archive_duration"] = ch['default_auto_archive_duration']
                    
            elif ch['type'] == 2:
                ch_data["bitrate"] = min(ch.get('bitrate', 64000), 384000)
                ch_data["user_limit"] = ch.get('user_limit', 0)
                if ch.get('rtc_region'):
                    ch_data["rtc_region"] = ch['rtc_region']
                ch_data["video_quality_mode"] = ch.get('video_quality_mode', 1)
                
            elif ch['type'] == 5:
                if ch.get('topic'):
                    ch_data["topic"] = ch['topic']
                ch_data["nsfw"] = ch.get('nsfw', False)
                if ch.get('default_auto_archive_duration'):
                    ch_data["default_auto_archive_duration"] = ch['default_auto_archive_duration']
                
            elif ch['type'] == 13:
                ch_data["bitrate"] = min(ch.get('bitrate', 64000), 384000)
                ch_data["user_limit"] = ch.get('user_limit', 0)
                if ch.get('rtc_region'):
                    ch_data["rtc_region"] = ch['rtc_region']
                
            elif ch['type'] == 15:
                ch_data["nsfw"] = ch.get('nsfw', False)
                if ch.get('default_auto_archive_duration'):
                    ch_data["default_auto_archive_duration"] = ch['default_auto_archive_duration']
                if ch.get('default_reaction_emoji'):
                    ch_data["default_reaction_emoji"] = ch['default_reaction_emoji']
                if ch.get('default_thread_rate_limit_per_user'):
                    ch_data["default_thread_rate_limit_per_user"] = ch['default_thread_rate_limit_per_user']
                if ch.get('available_tags'):
                    ch_data["available_tags"] = self._map_forum_tags(ch['available_tags'])
            
            existing = self._find_target_channel(ch, target_channels)
            if existing:
                self.channel_name_map[ch['id']] = existing['id']
                patched = self.api.patch(f"/channels/{existing['id']}", ch_data)
                self.stats['channels_kept'] += 1
                if patched:
                    self.stats['channels_updated'] += 1
                    print(Fore.GREEN + self.lang.get('channel_created') + " (обновлён)")
                else:
                    print(Fore.CYAN + f"      ↪ Канал без изменений: #{ch['name']}")
                continue

            new_ch = self.api.post(f"/guilds/{target_id}/channels", ch_data)
            if new_ch:
                self.channel_name_map[ch['id']] = new_ch['id']
                self.cache.set_mapping(ch['id'], new_ch['id'], 'channel')
                target_channels.append(new_ch)
                self.stats['channels'] += 1
                print(Fore.GREEN + self.lang.get('channel_created'))
                print(Fore.GREEN + f"    🆔 ID: {new_ch['id']}")
            else:
                self.stats['errors'] += 1
                err = self.api.last_error or ""
                print(Fore.RED + self.lang.get('channel_error') + (f": {err}" if err else ""))

    def copy_emojis(self, source_id, target_id):
        """КОПИРОВАНИЕ ЭМОДЗИ"""
        if not CONFIG["copy_emojis"]:
            return

        print(Fore.CYAN + f"\n{self.lang.get('copying_emojis')}")

        emojis = self.api.get(f"/guilds/{source_id}/emojis") or []
        target_emojis = self.api.get(f"/guilds/{target_id}/emojis") or []
        existing_names = {e["name"] for e in target_emojis}
        for e in target_emojis:
            for se in emojis:
                if se["name"] == e["name"]:
                    self.emoji_map[str(se["id"])] = str(e["id"])

        todo = [e for e in emojis if e["name"] not in existing_names]
        workers = int(CONFIG.get("parallel_cdn_workers") or 4)

        def _uri(em):
            return cloner_media.emoji_uri(str(em["id"]), bool(em.get("animated")))

        uri_map = cloner_media.parallel_map(
            todo, _uri, workers=workers, key_fn=lambda em: str(em["id"])
        )

        for emoji in todo:
            image = uri_map.get(str(emoji["id"]))
            if not image:
                self._fail("emoji", emoji.get("name", "?"), "cdn")
                continue
            new_emoji = self.api.post(
                f"/guilds/{target_id}/emojis",
                {"name": emoji["name"], "image": image},
            )
            if new_emoji:
                self.emoji_map[str(emoji["id"])] = str(new_emoji["id"])
                print(Fore.GREEN + self.lang.get("emoji_copied", name=emoji["name"]))
                self.stats["emojis"] += 1
            else:
                self._fail("emoji", emoji.get("name", "?"), self.api.last_error or "fail")

    def copy_stickers(self, source_id, target_id):
        if not CONFIG.get("copy_stickers", True):
            return
        print(Fore.CYAN + "\n🎨 КОПИРОВАНИЕ СТИКЕРОВ...")
        stickers = self.api.get(f"/guilds/{source_id}/stickers") or []
        workers = int(CONFIG.get("parallel_cdn_workers") or 4)

        def _st_uri(st):
            return cloner_media.sticker_uri(str(st["id"]), int(st.get("format_type") or 1))

        file_map = cloner_media.parallel_map(
            stickers, _st_uri, workers=workers, key_fn=lambda st: str(st["id"])
        )

        for sticker in stickers:
            file_uri = file_map.get(str(sticker["id"]))
            if not file_uri:
                self._fail("sticker", sticker.get("name", "?"), "cdn")
                continue
            new_sticker = self.api.post(
                f"/guilds/{target_id}/stickers",
                {
                    "name": sticker.get("name", "sticker")[:30],
                    "description": (sticker.get("description") or "")[:100],
                    "tags": sticker.get("tags", "tag")[:200],
                    "file": file_uri,
                },
            )
            if new_sticker:
                self.stats["stickers"] += 1
                print(Fore.GREEN + f"  ✅ Стикер: {sticker.get('name')}")
            else:
                self._fail("sticker", sticker.get("name", "?"), self.api.last_error or "fail")

    def copy_icon(self, source_id, target_id):
        if not CONFIG.get("copy_icon", True):
            return
        print(Fore.CYAN + "\n🖼️ КОПИРОВАНИЕ ИКОНКИ СЕРВЕРА...")
        source_guild = self.api.get(f"/guilds/{source_id}")
        if not source_guild or not source_guild.get("icon"):
            return
        icon_uri = cloner_media.guild_icon_uri(str(source_id), source_guild["icon"])
        if not icon_uri:
            self._fail("guild_icon", str(source_id), "cdn")
            return
        result = self.api.patch(f"/guilds/{target_id}", {"icon": icon_uri})
        if result:
            print(Fore.GREEN + "  ✅ Иконка скопирована")
        else:
            self._fail("guild_icon", "icon", self.api.last_error or "fail")

    def copy_webhooks(self, source_id, target_id):
        """КОПИРОВАНИЕ ВЕБХУКОВ"""
        if not CONFIG["copy_webhooks"]:
            return
        
        print(Fore.CYAN + f"\n{self.lang.get('copying_webhooks')}")
        
        channels = self.api.get(f"/guilds/{source_id}/channels") or []
        target_list = self._target_channels(target_id)
        
        for ch in channels:
            if ch['type'] == 0:
                try:
                    webhooks = self.api.get(f"/channels/{ch['id']}/webhooks") or []
                    for wh in webhooks:
                        target_ch_id = self.channel_name_map.get(ch['id'])
                        target_ch = None
                        if target_ch_id:
                            for t_ch in target_list:
                                if t_ch['id'] == target_ch_id:
                                    target_ch = t_ch
                                    break
                        if not target_ch:
                            for t_ch in target_list:
                                if t_ch['name'] == ch['name'] and t_ch['type'] == ch['type']:
                                    target_ch = t_ch
                                    break
                        
                        if not target_ch:
                            continue
                        
                        wh_data = {"name": wh["name"]}
                        if wh.get("avatar"):
                            av = cloner_media.webhook_avatar_uri(
                                str(wh["id"]), wh["avatar"]
                            )
                            if av:
                                wh_data["avatar"] = av
                        new_wh = self.api.post(f"/channels/{target_ch['id']}/webhooks", wh_data)
                        if new_wh:
                            print(Fore.GREEN + self.lang.get('webhook_copied', name=wh['name']))
                            self.stats['webhooks'] += 1
                            
                except:
                    pass

    def copy_members(self, source_id, target_id):
        """КОПИРОВАНИЕ УЧАСТНИКОВ"""
        if not CONFIG["copy_members"]:
            return
        
        print(Fore.CYAN + f"\n{self.lang.get('copying_members')}")
        
        try:
            members = self.api.get(f"/guilds/{source_id}/members?limit=1000") or []
            
            processed = 0
            for member in members:
                try:
                    user_id = member['user']['id']
                    
                    if member['user'].get('bot', False):
                        continue
                    
                    target_member = self.api.get(f"/guilds/{target_id}/members/{user_id}")
                    if not target_member:
                        continue
                    
                    if member.get('nick'):
                        self.api.patch(f"/guilds/{target_id}/members/{user_id}", {
                            "nick": member['nick']
                        })
                    
                    if member.get('roles'):
                        roles = [self.role_map.get(r) for r in member['roles'] if r in self.role_map]
                        if roles:
                            self.api.patch(f"/guilds/{target_id}/members/{user_id}", {
                                "roles": roles
                            })
                    
                    processed += 1
                    if processed % 10 == 0:
                        print(Fore.WHITE + f"  📊 Обработано {processed} участников")
                        
                except:
                    pass
            
            self.stats['members'] = processed
            print(Fore.GREEN + f"  ✅ Обработано: {processed} участников")
            
        except:
            pass

    def copy_server_settings(self, source_id, target_id):
        """КОПИРОВАНИЕ НАСТРОЕК"""
        if not CONFIG.get("copy_settings", True):
            return
        print(Fore.CYAN + f"\n{self.lang.get('copying_settings')}")
        
        source_guild = self.api.get(f"/guilds/{source_id}")
        if source_guild:
            settings = {
                "name": source_guild.get('name'),
                "verification_level": source_guild.get('verification_level', 0),
                "default_message_notifications": source_guild.get('default_message_notifications', 0),
                "explicit_content_filter": source_guild.get('explicit_content_filter', 0),
                "afk_timeout": source_guild.get('afk_timeout', 300),
                "preferred_locale": source_guild.get('preferred_locale', 'en-US')
            }
            
            settings = {k: v for k, v in settings.items() if v is not None}
            
            result = self.api.patch(f"/guilds/{target_id}", settings)
            if result:
                print(Fore.GREEN + self.lang.get('settings_copied'))

    def copy_banner(self, source_id, target_id):
        """КОПИРОВАНИЕ БАННЕРА"""
        if not CONFIG["copy_banner"]:
            return
        
        print(Fore.CYAN + f"\n{self.lang.get('copying_banner')}")
        
        source_guild = self.api.get(f"/guilds/{source_id}")
        if source_guild and source_guild.get('banner'):
            banner_uri = cloner_media.fetch_data_uri(
                f"https://cdn.discordapp.com/banners/{source_id}/{source_guild['banner']}.png",
                "image/png",
            )
            if banner_uri:
                result = self.api.patch(f"/guilds/{target_id}", {"banner": banner_uri})
                if result:
                    print(Fore.GREEN + self.lang.get('banner_copied'))
            else:
                self._fail("banner", str(source_id), "cdn")

    def copy_everything(self, source_id, target_id):
        """ЗАПУСК ПОЛНОГО КЛОНИРОВАНИЯ"""
        self.stats['start_time'] = time.time()
        self.api.read_only = bool(CONFIG.get("dry_run"))
        self.api.planned_writes = []
        triad = CONFIG.get("triad_strategy")
        if triad:
            for k, v in cloner_extras.apply_triad(str(triad), {}).items():
                CONFIG[k] = v
        self._db_log("info", "Clone started", source=source_id, target=target_id)

        print(Fore.MAGENTA + "\n" + "═"*70)
        print(Fore.GREEN + self.lang.get('start_clone'))
        if self.api.read_only:
            print(Fore.YELLOW + "  🧪 DRY-RUN — запросы POST/PATCH/DELETE не отправляются")
        print(Fore.MAGENTA + "═"*70)

        try:
            self.preflight(source_id, target_id)
            self._snapshot_guild(source_id, "source_before")
            print(Fore.CYAN + "\n🧠 Режим: только синхронизация. Удаление каналов/ролей отключено.")

            self.copy_server_settings(source_id, target_id)
            self.copy_roles(source_id, target_id)
            self.copy_emojis(source_id, target_id)
            self.copy_channels(source_id, target_id)
            self.copy_stickers(source_id, target_id)
            self.copy_webhooks(source_id, target_id)
            self.copy_banner(source_id, target_id)
            self.copy_icon(source_id, target_id)
            self.copy_onboarding(source_id, target_id)
            self.copy_automod(source_id, target_id)
            self.copy_scheduled_events(source_id, target_id)
            self.copy_members(source_id, target_id)
            self.remove_orphans(source_id, target_id)

            if self.api.read_only:
                self.dry_run_report()

            self._snapshot_guild(target_id, "target_after")
            src_g = cloner_genome.build_genome(
                source_id,
                self.api.get(f"/guilds/{source_id}/roles") or [],
                self.api.get(f"/guilds/{source_id}/channels") or [],
                self.api.get(f"/guilds/{source_id}/emojis") or [],
            )
            tgt_g = cloner_genome.build_genome(
                target_id,
                self.api.get(f"/guilds/{target_id}/roles") or [],
                self.api.get(f"/guilds/{target_id}/channels") or [],
                self.api.get(f"/guilds/{target_id}/emojis") or [],
            )
            pct, _ = cloner_genome.compare_genomes(src_g, tgt_g)
            self.stats["genome_match_pct"] = pct
            gh = cloner_genome.genome_digest(src_g)
            self.stats["genome_hash"] = gh
            if self.store and self.store.enabled and self.session_id:
                self.store.save_genome(self.session_id, source_id, gh, src_g)
            seal = cloner_extras.entropy_seal(gh, self.discord_user_id, self.session_id or 0)
            self.stats["entropy_seal"] = seal
            cloner_ui.show_genome_result(pct, seal)

            elapsed = time.time() - self.stats['start_time']
            self.stats['rate_limits'] = self.api.rate_limit_hits
            self.stats['api_requests'] = self.api.total_requests
            self.stats['elapsed_sec'] = round(elapsed, 2)

            print(Fore.MAGENTA + "\n" + "═"*70)
            print(Fore.CYAN + self.lang.get('stats'))
            print(Fore.WHITE + self.lang.get('stats_roles', count=self.stats['roles']))
            print(Fore.WHITE + f"  🔄 Ролей обновлено/оставлено: {self.stats['roles_updated']}/{self.stats['roles_kept']}")
            print(Fore.WHITE + self.lang.get('stats_channels', count=self.stats['channels']))
            print(Fore.WHITE + f"  🔄 Каналов обновлено/оставлено: {self.stats['channels_updated']}/{self.stats['channels_kept']}")
            print(Fore.WHITE + self.lang.get('stats_emojis', count=self.stats['emojis']))
            print(Fore.WHITE + f"  🎨 Стикеров скопировано: {self.stats['stickers']}")
            print(Fore.WHITE + self.lang.get('stats_webhooks', count=self.stats['webhooks']))
            print(Fore.WHITE + self.lang.get('stats_members', count=self.stats['members']))
            print(Fore.WHITE + f"  📋 Onboarding: {self.stats.get('onboarding', 0)} | AutoMod: {self.stats.get('automod_rules', 0)} | Events: {self.stats.get('scheduled_events', 0)}")
            if self.stats.get("orphans_removed"):
                print(Fore.WHITE + f"  🧹 Удалено лишнего: {self.stats['orphans_removed']}")
            if self.stats.get("dry_writes"):
                print(Fore.WHITE + f"  🧪 Dry-run writes: {self.stats['dry_writes']}")
            print(Fore.WHITE + self.lang.get('stats_perms', count=self.total_perms_copied))
            print(Fore.WHITE + self.lang.get('stats_time', time=f"{elapsed:.1f} сек ({elapsed/60:.1f} мин)"))
            print(Fore.WHITE + self.lang.get('stats_errors', count=self.stats['errors']))
            if self.stats.get("failed_items"):
                print(Fore.YELLOW + f"  ⚠️ Ошибок детально: {len(self.stats['failed_items'])} (см. cloner.log / Neon stats)")
            print(Fore.WHITE + f"  🚀 Rate limits: {self.api.rate_limit_hits}")
            print(Fore.WHITE + f"  📡 Всего запросов: {self.api.total_requests}")
            print(Fore.MAGENTA + "═"*70)

            log_summary(self.stats)
            print(Fore.GREEN + f"\n🎉🎉🎉 {self.lang.get('clone_complete')} 🎉🎉🎉")
            if self.store and self.store.enabled and self.session_id:
                self.store.finish_session(self.session_id, "completed", self.stats)
                self._db_log("info", "Clone completed")
            
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n\n⚠️ Прервано пользователем")
            if self.store and self.store.enabled and self.session_id:
                self.store.finish_session(self.session_id, "cancelled", self.stats, "KeyboardInterrupt")
            raise
        except Exception as e:
            print(Fore.RED + f"\n❌ Ошибка: {e}")
            if self.store and self.store.enabled and self.session_id:
                self.store.finish_session(self.session_id, "failed", self.stats, str(e))
                self._db_log("error", str(e))
            raise

# ======================================================================
# ГЛАВНАЯ ФУНКЦИЯ
# ======================================================================

def init_neon_store():
    """Фоновое хранилище — без вывода в консоль."""
    store = NeonStore()
    if not CONFIG.get("use_neon_db", True):
        store.enabled = False
        return store
    if store.bootstrap():
        from app_paths import data_path
        store.import_json_cache(data_path(CONFIG["cache_file"]))
        store.import_json_cache(data_path("clone_cache.json"))
    return store


def persist_login(store, user_id, token, user, lang_code, source_id="", target_id=""):
    if not store or not CONFIG.get("use_neon_db", True):
        return
    for attempt in range(5):
        if store.upsert_account(
            user_id,
            token,
            username=user.get("username", ""),
            global_name=user.get("global_name") or user.get("display_name") or "",
            lang=lang_code,
            source_guild_id=source_id or "",
            target_guild_id=target_id or "",
        ):
            return
        time.sleep(1.0 + attempt * 0.7)
    _log = getattr(store, "last_error", "")
    try:
        from app_paths import data_path
        with open(data_path("cloner.log"), "a", encoding="utf-8") as f:
            f.write(f"login save failed: {_log}\n")
    except OSError:
        pass


GodCloner = VexxCloner


def prompt_clone_modules():
    if not CONFIG.get("interactive_modules"):
        return
    toggles = [
        ("copy_settings", "Настройки сервера"),
        ("copy_roles", "Роли"),
        ("copy_emojis", "Emoji"),
        ("copy_channels", "Каналы"),
        ("copy_stickers", "Стикеры"),
        ("copy_webhooks", "Вебхуки"),
        ("copy_banner", "Баннер"),
        ("copy_icon", "Иконка"),
        ("copy_onboarding", "Onboarding"),
        ("copy_automod", "AutoMod"),
        ("copy_scheduled_events", "Events"),
        ("copy_members", "Участники"),
    ]
    print(Fore.CYAN + "\nМодули (Enter = все вкл, 0 = быстрый выбор):")
    for i, (key, label) in enumerate(toggles, 1):
        state = "ON" if CONFIG.get(key, True) else "OFF"
        print(Fore.WHITE + f"  {i}. [{state}] {label}")
    raw = input(Fore.YELLOW + "Номера OFF через запятую (пусто = все): ").strip()
    if not raw:
        return
    off = {x.strip() for x in raw.replace(";", ",").split(",") if x.strip()}
    for i, (key, _) in enumerate(toggles, 1):
        if str(i) in off:
            CONFIG[key] = False


def main():
    try:
        print_banner()
        store = init_neon_store()
        
        print(Fore.CYAN + "🌐 Select language / Выберите язык:")
        print(Fore.YELLOW + "  1 🇷🇺 Русский")
        print(Fore.YELLOW + "  2 🇬🇧 English")
        lang_choice = input(Fore.WHITE + "> ").strip()
        lang = Language('en' if lang_choice == '2' else 'ru')
        lang_code = lang.lang
        
        while True:
            print()
            token = input(Fore.YELLOW + lang.get('token')).strip()
            if not token:
                print(Fore.RED + lang.get('invalid_token'))
                continue
            
            api = DiscordAPI(token)
            user = api.get("/users/@me")
            if not user:
                print(Fore.RED + lang.get('invalid_token'))
                continue
            
            user_id = str(user.get("id", ""))
            persist_login(store, user_id, token, user, lang_code)

            print(Fore.GREEN + f"\n✅ {lang.get('logged_in')}: {user.get('username', 'Unknown')}#{user.get('discriminator', '0')}")
            print(Fore.CYAN + f"   🆔 ID: {user.get('id', 'Unknown')}")

            source_id = input(Fore.YELLOW + lang.get("source_id")).strip()
            target_id = input(Fore.YELLOW + lang.get("target_id")).strip()
            if not source_id or not target_id or source_id == target_id:
                print(Fore.RED + "❌ Проверь ID source/target")
                continue
            source = api.get(f"/guilds/{source_id}")
            target = api.get(f"/guilds/{target_id}")
            if not source or not target:
                print(Fore.RED + "❌ Сервер не найден или нет доступа")
                continue
            
            cloner_ui.section("Серверы")
            print(Fore.CYAN + f"  Source: {source.get('name')} ({source_id})")
            print(Fore.CYAN + f"  Target: {target.get('name')} ({target_id})")

            while True:
                mode = cloner_ui.menu_hub()
                if mode == "0":
                    break
                if mode == "6":
                    prof = input(Fore.YELLOW + "Профиль mappings [default]: ").strip() or "default"
                    CONFIG["mapping_profile"] = prof
                    print(Fore.GREEN + f"  Профиль: {prof}")
                    continue
                if mode == "7":
                    import vexx_updater

                    print(Fore.CYAN + vexx_updater.format_report(vexx_updater.check_updates(force=True)))
                    if input(Fore.YELLOW + "Установить? (y/n): ").lower() in ("y", "yes", "д", "да"):
                        print(Fore.CYAN + vexx_updater.format_report(vexx_updater.apply_updates()))
                        print(Fore.YELLOW + "Перезапусти Vexx Cloner после обновления.")
                    continue

                persist_login(store, user_id, token, user, lang_code, source_id, target_id)
                if store.enabled:
                    store.save_clone_context(user_id, source_id, target_id)
                session_id = store.start_session(
                    user_id, source_id, source.get("name", ""),
                    target_id, target.get("name", ""), CONFIG,
                ) if store.enabled else None

                cloner = VexxCloner(
                    token, lang,
                    store=store,
                    session_id=session_id,
                    discord_user_id=user_id,
                    source_guild_id=source_id,
                    target_guild_id=target_id,
                )
                CONFIG["full_wipe_before_clone"] = False

                if mode == "1":
                    strat = cloner_ui.pick_triad()
                    CONFIG["triad_strategy"] = strat
                    prompt_clone_modules()
                    if input(Fore.YELLOW + lang.get("confirm_clear")).lower() in ("y", "yes", "д", "да"):
                        cloner.copy_everything(int(source_id), int(target_id))
                    CONFIG.pop("triad_strategy", None)
                elif mode == "2":
                    src_b = input(Fore.YELLOW + "ID второго source (B): ").strip()
                    if src_b:
                        cloner.copy_chimera(int(source_id), int(src_b), int(target_id))
                elif mode == "3":
                    if store.enabled:
                        snaps = store.list_snapshots(source_id)
                        for s in snaps[:10]:
                            print(Fore.WHITE + f"  #{s['id']} {s['snapshot_type']} {s['created_at']}")
                        sid = input(Fore.YELLOW + "ID снимка: ").strip()
                        if sid.isdigit():
                            cloner.restore_from_snapshot(int(sid), int(target_id))
                elif mode == "4":
                    cloner.shadow_sync(int(source_id), int(target_id))
                elif mode == "5":
                    if store.enabled and session_id:
                        rows = store.list_anomalies(session_id)
                        for r in rows:
                            print(Fore.WHITE + f"  #{r['id']} {r['kind']} {r['name']}: {r['error_text'][:60]}")
                    aid = input(Fore.YELLOW + "Anomaly ID: ").strip()
                    if aid.isdigit():
                        cloner.retry_anomaly(int(aid))
                else:
                    prompt_clone_modules()
                    if input(Fore.YELLOW + lang.get("confirm_clear")).lower() in ("y", "yes", "д", "да"):
                        cloner.copy_everything(int(source_id), int(target_id))

            again = input(Fore.YELLOW + lang.get("again")).lower()
            if again not in ("y", "yes", "д", "да"):
                break
            
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n\n⚠️ Программа остановлена")
    except Exception as e:
        print(Fore.RED + f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        import multiprocessing
        multiprocessing.freeze_support()
    main()