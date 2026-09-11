# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

pyqt5libs_datas, pyqt5libs_binaries, pyqt5libs_hiddenimports = collect_all("pyqt5libs")
libs_datas, libs_binaries, libs_hiddenimports = collect_all("libs")
controller_hiddenimports = collect_submodules("controladores")

runtime_datas = [
    ("../imagenes", "imagenes"),
    ("../temas", "temas"),
    ("../sistema.demo.ini", "."),
    ("../rnd.ini", "."),
]

hidden = (
    pyqt5libs_hiddenimports
    + libs_hiddenimports
    + controller_hiddenimports
    + ["demo_seed"]
)

a = Analysis(
    ["../demo_main.py"],
    pathex=[".."],
    binaries=pyqt5libs_binaries + libs_binaries,
    datas=runtime_datas + pyqt5libs_datas + libs_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RND Demo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon="../imagenes/vogel_consultoria_oficial.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="RND Demo",
)
