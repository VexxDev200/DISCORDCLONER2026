@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion
cd /d "%~dp0"
echo === Vexx Cloner: free OAuth for everyone (Cloudflare Workers) ===
echo.

where node >nul 2>&1
if errorlevel 1 (
  echo Install Node.js LTS: https://nodejs.org/
  pause
  exit /b 1
)

if not exist "databaseneon.txt" (
  echo Missing databaseneon.txt - paste Neon URL like God Cloner.
  pause
  exit /b 1
)

if not exist "config.json" (
  echo Missing config.json - add bot section with token, client_id, client_secret.
  pause
  exit /b 1
)

set /p WORKER_NAME=Worker name (unique, latin, e.g. vexx-oauth-smird): 
if "!WORKER_NAME!"=="" set WORKER_NAME=vexx-cloner-oauth-%RANDOM%

cd oauth_worker

powershell -NoProfile -Command "Set-Content -Path wrangler.toml -Encoding utf8 -Value @('name = \"!WORKER_NAME!\"','main = \"src/worker.js\"','compatibility_date = \"2024-11-01\"','workers_dev = true','')"

if not exist node_modules (
  call npm install
  if errorlevel 1 pause & exit /b 1
) else (
  call npm install wrangler@4 --save-dev
)

set REDIRECT_URI=https://!WORKER_NAME!.workers.dev/oauth/callback
echo Worker name: !WORKER_NAME!  (real URL after deploy - step 4)
echo.

echo Step 1: Cloudflare login (free account)...
call npx wrangler login
if errorlevel 1 pause & exit /b 1

echo.
echo Step 2: Neon secret...
for /f "usebackq delims=" %%A in ("..\databaseneon.txt") do set "NEON_URL=%%A"
set "NEON_URL=!NEON_URL:"=!"
echo(!NEON_URL!| npx wrangler secret put DATABASE_URL

echo.
echo Step 3: Deploy worker...
call npx wrangler deploy
if errorlevel 1 pause & exit /b 1

echo.
echo Step 4: Sync URL + Discord secrets...
cd ..
python sync_oauth_worker.py
if errorlevel 1 pause & exit /b 1

echo.
echo === DONE ===
echo Use redirect URL printed above in Discord Portal.
echo Then: python discord_bot.py
pause
