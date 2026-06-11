# -*- mode: python ; coding: utf-8 -*-
import pkgutil
import rich._unicode_data
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

block_cipher = None

# Automatically discover and bundle all submodules under shello_cli folder
shello_submodules = collect_submodules('shello_cli')

# Dynamically collect all unicode submodules required by the rich console renderer
rich_unicode_imports = [f"rich._unicode_data.{m.name}" for m in pkgutil.iter_modules(rich._unicode_data.__path__)] + ["rich._unicode_data"]

# Bundle metadata for fastmcp to satisfy runtime importlib.metadata requirements
fastmcp_metadata = copy_metadata('fastmcp') + copy_metadata('fastmcp-slim')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=fastmcp_metadata,
    hiddenimports=[
        # Core third-party dependencies
        'click',
        'rich',
        'prompt_toolkit',
        'pydantic',
        'requests',
        'urllib3',
        'dotenv',
        'keyring',
        'pyperclip',
        'openai',
        'fastmcp',
        'anyio',
    ] + shello_submodules + rich_unicode_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy testing frameworks only
        'pytest',
        'hypothesis',
        'test',
        'tests',
        '_pytest',
        'coverage',
        'unittest',
        # Exclude unused standard library GUI frameworks
        'tkinter',
        'tk',
        'tcl',
        'pydoc',
        'doctest',
    ],
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
    name='shello',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Disabled on Windows
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
