# GitHub автообновление

## У тебя (релиз)

1. `copy update_publish.example.json → update_publish.json` → **`github_repo": "USER/REPO"`**
2. Один раз:
   ```bat
   git init
   git remote add origin https://github.com/USER/REPO.git
   gh auth login
   ```
3. После правок кода: **`PUBLISH_UPDATE.bat`**
   - `--bump` поднимает `2026.11.01.N`
   - собирает zip
   - пишет `updates/manifest.json` с URL **GitHub Releases**
   - `git commit` + `push` + `gh release create` с zip

## У игроков / клиентов

В комплекте лежит `updates/github_target.json` (repo + branch).

`update_config.json`:
- **`auto_apply": true`** — при старте Vexx скачает **bundle** zip, если версия в manifest новее
- **`manifest_url"`** можно оставить пустым — подставится raw GitHub manifest
- Если папка — **git clone** того же repo и `git_pull_if_repo`: сначала пробует **`git pull`**

После авто-установки **перезапусти** Vexx (версия в памяти обновится из файлов).

## Проверка

```bat
python vexx_updater.py --force
python vexx_updater.py --apply
```

Manifest: `https://raw.githubusercontent.com/USER/REPO/main/updates/manifest.json`
