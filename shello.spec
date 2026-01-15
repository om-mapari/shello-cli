# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],  # Removed - code is already collected via hiddenimports
    hiddenimports=[
        'shello_cli',
        'shello_cli.cli',
        'shello_cli.agent',
        'shello_cli.agent.shello_agent',
        'shello_cli.chat',
        'shello_cli.chat.chat_session',
        'shello_cli.ui',
        'shello_cli.ui.ui_renderer',
        'shello_cli.ui.user_input',
        'shello_cli.utils',
        'shello_cli.utils.settings_manager',
        'shello_cli.tools',
        'shello_cli.api',
        'shello_cli.commands',
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
        # Pygments components for syntax highlighting
        'pygments',
        'pygments.lexers',
        'pygments.styles',
        'pygments.formatters',
        'pygments.filters',
        'pygments.token',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Testing
        'pytest',
        'hypothesis',
        'test',
        'tests',
        '_pytest',
        'coverage',
        # Unused stdlib modules (heavy)
        'tkinter',
        'tk',
        'tcl',
        'unittest',
        'xmlrpc',
        'multiprocessing',
        'pydoc',
        'doctest',
        'sqlite3',
        # Build tools
        'distutils',
        'setuptools',
        'pkg_resources',
        'pip',
        'wheel',
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
    strip=False,  # Disabled on Windows (no GNU strip available)
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
