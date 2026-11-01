# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('schema.sql', '.')]
binaries = []
hiddenimports = ['boot_db', 'db_embed', 'schema_embed', 'neon_store', 'app_paths', 'cloner_config', 'cloner_media', 'cloner_genome', 'cloner_dsl', 'cloner_ui', 'cloner_extras', 'psycopg', 'psycopg_binary', 'psycopg.pq', 'psycopg.types.json']
tmp_ret = collect_all('psycopg')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('psycopg_binary')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:/Documents/DISCORDCLONER2026/discordcloner.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['C:/Documents/DISCORDCLONER2026/pyi_rth_db.py'],
    excludes=['tkinter', 'matplotlib', 'PIL', 'pytest', 'IPython', 'numpy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VexxCloner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
