# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for QR Attendance Scanner

import sys
from pathlib import Path

block_cipher = None

# Find pyzbar DLLs
pyzbar_path = Path(sys.base_prefix) / 'Lib' / 'site-packages' / 'pyzbar'
binaries = []

if pyzbar_path.exists():
    # Include pyzbar DLLs
    for dll in pyzbar_path.glob('*.dll'):
        binaries.append((str(dll), 'pyzbar'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=[],
    hiddenimports=['PySide6', 'pyzbar', 'pyzbar.wrapper'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='QR Attendance Scanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
