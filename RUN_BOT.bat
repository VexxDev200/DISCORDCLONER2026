@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m pip install discord.py psycopg[binary] -q
python discord_bot.py
pause
