@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Vexx: publish to GitHub ===
echo Нужны: update_publish.json, git remote, gh auth login
echo.
if not exist update_publish.json (
  copy /Y update_publish.example.json update_publish.json
  echo Создан update_publish.json — укажи github_repo и запусти снова.
  pause
  exit /b 1
)
python publish_update.py --bump %*
pause
