# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

pyqt5libs_datas, pyqt5libs_binaries, pyqt5libs_hiddenimports = collect_all("pyqt5libs")
libs_datas, libs_binaries, libs_hiddenimports = collect_all("libs")
controller_hiddenimports = collect_submodules("controladores")

runtime_datas = [
    ('imagenes', 'imagenes'),
    ('temas', 'temas'),
    ('sistema.ini', '.'),
    ('rnd.ini', '.'),
]

runtime_hiddenimports = [
    'win32crypt',
    'win32com.shell.shell',
    'win32event',
    'win32process',
    'vistas.ConfigurarCredencialDB',
]

a = Analysis(['main.py'],
             pathex=[],
             binaries=pyqt5libs_binaries + libs_binaries,
             datas=runtime_datas + pyqt5libs_datas + libs_datas,
             hiddenimports=(
                 pyqt5libs_hiddenimports
                 + libs_hiddenimports
                 + runtime_hiddenimports
                 + controller_hiddenimports
             ),
             hookspath=[],
             hooksconfig={},
             runtime_hooks=['hooks\\rthook_pymysql.py'],
             excludes=['matplotlib'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts, 
          [],
          exclude_binaries=True,
          name='main',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None,
          contents_directory='.',
          version='version.txt',
          icon='imagenes\\vogel_consultoria_oficial.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas, 
               strip=False,
               upx=True,
               upx_exclude=[],
               name='main')
