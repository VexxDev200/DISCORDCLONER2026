# Vexx Cloner — Discord Bot

**Ты один крутишь бота.** Все остальные — `/clone` в Discord, без своих конфигов.

## Бесплатно, без домена (рекомендуется)

1. Уже есть: `config.json` (bot token, client_id, client_secret) + `databaseneon.txt`
2. Дважды кликни **`SETUP_FREE_OAUTH.bat`**
   - бесплатный аккаунт Cloudflare (если спросит)
   - уникальное имя worker → URL вида `https://ИМЯ.workers.dev/oauth/callback`
   - секреты в Worker, деплой, патч `config.json`
3. Discord Portal → **OAuth2 → Redirects** → вставь URL из конца bat-файла (один раз)
4. `python discord_bot.py` — держи процесс включённым

После этого **любой** пользователь: первый `/clone` → **Authorize** (телефон/ПК) → клон в **ЛС**. Дальше только `/clone`.

Техника: OAuth callback на **Cloudflare Workers** (free `*.workers.dev`), state и токены в **Neon**, клон на **твоём** ПК через очередь.

## Локально (только ты на этом ПК)

Redirect `http://127.0.0.1:8765/oauth/callback` — без SETUP_FREE_OAUTH.

## Команды

| Команда | Описание |
|---------|----------|
| `/start` | Authorize |
| `/login` | Повтор |
| `/status` | Привязка |
| `/logout` | Сброс |
| `/clone` | source_id target_id [strategy] |

## Зависимости

```powershell
pip install -r requirements.txt
```

Worker: Node.js LTS (для `SETUP_FREE_OAUTH.bat` один раз).
