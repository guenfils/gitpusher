# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Git Pusher desktop app.
Build with:  ./build.sh
"""
from PyInstaller.utils.hooks import collect_all

ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=ctk_binaries,
    datas=[
        ("assets", "assets"),
        ("ui",     "ui"),
        ("core",   "core"),
        *ctk_datas,
    ],
    hiddenimports=[
        *ctk_hiddenimports,
        # ── stdlib extras ──────────────────────────────
        "tkinter", "tkinter.ttk", "tkinter.filedialog",
        # ── third-party ────────────────────────────────
        "customtkinter", "darkdetect",
        "PIL", "PIL.Image", "PIL.ImageDraw",
        "PIL.ImageFilter", "PIL.ImageTk",
        "requests", "requests.adapters", "requests.auth",
        "paramiko", "cryptography",
        # ── core ───────────────────────────────────────
        "core.git_manager",
        "core.ssh_manager",
        "core.github_api",
        "core.gitlab_api",
        "core.config_manager",
        "core.gitignore_manager",
        "core.secret_scanner",
        # ── ui base ────────────────────────────────────
        "ui.app",
        "ui.theme",
        "ui.manage_view",
        "ui.widgets.common",
        # ── wizard steps ───────────────────────────────
        "ui.steps.step_check",
        "ui.steps.step_platform",
        "ui.steps.step_project",
        "ui.steps.step_readme",
        "ui.steps.step_branch",
        "ui.steps.step_upload",
        # ── panels (20) ────────────────────────────────
        "ui.panels.panel_repos",
        "ui.panels.panel_clone",
        "ui.panels.panel_sync",
        "ui.panels.panel_tags",
        "ui.panels.panel_commits",
        "ui.panels.panel_ssh",
        "ui.panels.panel_templates",
        "ui.panels.panel_webhooks",
        "ui.panels.panel_collaborators",
        "ui.panels.panel_issues",
        "ui.panels.panel_accounts",
        "ui.panels.panel_scheduled",
        "ui.panels.panel_watch",
        "ui.panels.panel_stats",
        "ui.panels.panel_export",
        "ui.panels.panel_stash",
        "ui.panels.panel_branches",
        "ui.panels.panel_diff",
        "ui.panels.panel_settings",
        "ui.panels.panel_gitflow",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "scipy", "pandas", "jupyter", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="git-pusher",
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon="assets/icon.png",
)
