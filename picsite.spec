# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 收集 git 模块的所有子模块
git_hidden_imports = collect_submodules('git')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),  # 包含模板文件
        ('config.py', '.'),         # 包含配置文件
    ] + collect_data_files('git'),  # 添加 git 模块的数据文件
    hiddenimports=[
        'git',
        'yaml',
        'flask',
        'werkzeug',
        'jinja2',
        'gitdb',
        'smmap',
    ] + git_hidden_imports,  # 添加 git 的所有子模块
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='picsite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name='picsite.app',
    icon=None,
    bundle_identifier='com.gloridust.picsite',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'LSBackgroundOnly': 'False',
        'CFBundleShortVersionString': '1.0.0',
    },
) 