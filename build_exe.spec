# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for QR Attendance Scanner

import sys
from pathlib import Path

block_cipher = None

# Find pyzbar DLLs
pyzbar_path = Path(sys.base_prefix) / 'Lib' / 'site-packages' / 'pyzbar'
binaries = []

# Explicitly include required pyzbar DLLs
required_dlls = ['libiconv.dll', 'libzbar-64.dll']

if pyzbar_path.exists():
    for dll_name in required_dlls:
        dll_path = pyzbar_path / dll_name
        if dll_path.exists():
            binaries.append((str(dll_path), 'pyzbar'))
    
    # Also include any other DLLs found
    for dll in pyzbar_path.glob('*.dll'):
        dll_tuple = (str(dll), 'pyzbar')
        if dll_tuple not in binaries:
            binaries.append(dll_tuple)

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

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='QR Attendance Scanner',
)
