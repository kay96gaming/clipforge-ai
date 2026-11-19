# CLIPFORGE AI — status

## Working (tested here on Linux with real FFmpeg, synthetic video)
- Media probe/validation, SQLite projects, transcript caching (resume), sentence-aligned clip selection + scoring,
  titles/hashtags, SRT/VTT/ASS captions (7 styles, karaoke/emphasis), reframing (crop/blur/fit, custom aspect),
  H.264/H.265 + NVENC/QSV/AMF encoder detection, export w/ progress, cancel, .part recovery, thumbnails.

## Written but NOT run (no PySide6 / Windows / GPU in the build sandbox)
- PySide6 UI (Dashboard, Create Clips, Live Clipping, Settings), Faster-Whisper transcription, live rolling buffer.

## Not implemented yet (and not shown in the UI)
- Caption Studio (live style preview, per-word editing), Clip Editor (timeline/split/merge/undo), Templates saving,
  Export Center (history UI, 1440p/4K selector, H.265 toggle), YouTube URL import, setup wizard, speaker (active-talker)
  tracking, per-frame face following (currently one smoothed position per clip), live transcription + auto-detect,
  CPU/GPU usage meters, AI thumbnail frame picking, PySceneDetect integration, MediaPipe.
- Face detection uses OpenCV Haar; falls back to centre crop if cascade data is missing (as in this sandbox).
- Installer (.exe wrapper like Inno Setup) and the .exe itself: must be built on Windows.
