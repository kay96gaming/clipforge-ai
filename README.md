# CLIPFORGE AI
Local, offline-first AI video clipper (Python + PySide6 + FFmpeg + Faster-Whisper).

## Run from source (Windows 10/11)
1. Install Python 3.11+ and create a venv: `python -m venv .venv && .venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. Download an FFmpeg "full" build (e.g. gyan.dev), copy `ffmpeg.exe` and `ffprobe.exe` into `ffmpeg\` (or add to PATH).
4. `python main.py`. The first transcription downloads the Whisper model (needs internet once, then fully offline).

## Build the .exe
Run `scripts\build_windows.bat`. Output: `dist\CLIPFORGE_AI\CLIPFORGE_AI.exe`. Only claim success if that file exists and launches.
Wrap in an installer with Inno Setup if desired.

## Notes
- GPU: NVIDIA CUDA speeds transcription; NVENC/QSV/AMF speed rendering. CPU always works (slower). Use the `small` Whisper model on ordinary PCs.
- Only import videos you have rights to use. No DRM/access-control bypassing.
- See TODO.md for what is and isn't implemented.

## One-click installer (no Windows PC needed)
Push this folder to a GitHub repo (branch `main`). The "build-windows-installer" Action builds
`CLIPFORGE_AI_Setup.exe` (FFmpeg bundled) — download it from the run's Artifacts.
