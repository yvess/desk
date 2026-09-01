# -*- mode: python ; coding: utf-8 -*-
# PyInstaller >= 6 (see docker/worker/requirements-build.txt)


a = Analysis(['worker.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             noarchive=False)
pyz = PYZ(a.pure)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.datas,
          [],
          name='dworker',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )
