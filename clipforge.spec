# PyInstaller spec: pyinstaller --noconfirm clipforge.spec
from PyInstaller.utils.hooks import collect_all
datas, binaries, hidden = [], [], []
for pkg in ("faster_whisper", "ctranslate2", "av", "cv2"):
    d, b, h = collect_all(pkg); datas += d; binaries += b; hidden += h
datas += [("ffmpeg", "ffmpeg")]
a = Analysis(["main.py"], pathex=["."], binaries=binaries, datas=datas, hiddenimports=hidden)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="CLIPFORGE_AI", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="CLIPFORGE_AI")
