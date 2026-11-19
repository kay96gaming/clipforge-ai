@echo off
setlocal
cd /d "%~dp0\.."
where python >nul 2>nul || (echo Python 3.11+ not found & exit /b 1)
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || exit /b 1
if not exist ffmpeg\ffmpeg.exe (
  echo.
  echo Put ffmpeg.exe and ffprobe.exe into the "ffmpeg" folder first ^(https://www.gyan.dev/ffmpeg/builds/^), then re-run.
  exit /b 1
)
python -m pytest -q tests || exit /b 1
pyinstaller --noconfirm clipforge.spec || exit /b 1
echo.
echo Built: dist\CLIPFORGE_AI\CLIPFORGE_AI.exe
