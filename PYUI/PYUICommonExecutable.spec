# -*- mode: python ; coding: utf-8 -*-

import os
import glob

# 1. Name of  well-defined folder
FOLDER_BUILD = os.environ.get('FOLDER')
FOLDET_OUT = os.environ.get('OUT')
PROJECT_NAME = os.environ.get('NAME')
IS_CONSOLE = os.environ.get('CONSOLE')
if IS_CONSOLE == '0':
    IS_CONSOLE = False
else:
    IS_CONSOLE = True

MODULE_FOLDER = 'code'  # Change this to your folder's actual name

dynamic_modules = []

# 2. Automatically scan the folder for all Python files
search_path = os.path.join(MODULE_FOLDER, "**", "*.py")
for file_path in glob.glob(search_path, recursive=True):
    if os.path.basename(file_path) != '__init__.py':
        # Convert file path 'my_custom_folder/sub/module.py' -> 'my_custom_folder.sub.module'
        module_name = os.path.splitext(file_path)[0].replace(os.sep, '.')
        dynamic_modules.append(module_name)

#

a = Analysis(
    ['bootstrap.py'],
    pathex=[],
    binaries=[],
    datas=[('code', 'code'), ('compiled_layouts', 'compiled_layouts'), ('compiled_components', 'compiled_components'), ('layouts', 'layouts'),('settings.bin','.')],
    hiddenimports=dynamic_modules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name=PROJECT_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=IS_CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
