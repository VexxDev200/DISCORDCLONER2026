@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m pip install pyfiglet Pillow discord.py psycopg[binary] -q 2>nul
python -c "import studio_brand; studio_brand.ensure_brand_assets()" 2>nul
python vexx_launcher.py
pause
