@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -c "import vexx_updater; vexx_updater.ensure_config_from_example()"
echo === Vexx Update (check) ===
python vexx_updater.py --force
echo.
echo Установить: python vexx_updater.py --apply
echo Или: CHECK_UPDATES.bat apply
if /i "%~1"=="apply" (
  python vexx_updater.py --apply
)
pause
