from pathlib import Path

project_root = Path(SPECPATH)
datas = [
    (str(project_root / "pomodoro" / "styles.qss"), "pomodoro"),
    (str(project_root / "assets" / "fonts" / "Aleo-Regular.ttf"), "assets/fonts"),
    (str(project_root / "assets" / "fonts" / "JetBrainsMono-Regular.ttf"), "assets/fonts"),
    (str(project_root / "assets" / "fonts" / "JetBrainsMono-OFL.txt"), "assets/fonts"),
]

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PomodoroTimer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
