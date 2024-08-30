# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('src/logo-r.png', 'src'),  # 确保图标文件被包含
        ('config.py', '.'),  # 包含配置文件
    ],
    hiddenimports=[
        'PyQt5.sip',
        'qtawesome',
        'qdarkstyle',
        'git',
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AlbumViewer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/logo-r.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AlbumViewer'
)

app = BUNDLE(
    coll,
    name='AlbumViewer.app',
    icon='src/logo-r.png',
    bundle_identifier=None,
    info_plist={
        'NSHighResolutionCapable': 'True'
    },
)