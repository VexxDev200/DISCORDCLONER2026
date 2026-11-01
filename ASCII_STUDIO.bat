@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m pip install pyfiglet Pillow -q
python -c "import studio_brand; studio_brand.ensure_brand_assets()"
python vexx_launcher.py 2
