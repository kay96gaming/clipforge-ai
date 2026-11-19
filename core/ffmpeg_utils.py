"""FFmpeg/ffprobe discovery, media probing/validation, hardware encoder detection."""
import json, os, shutil, subprocess, sys
from dataclasses import dataclass
from pathlib import Path

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _find(name: str):
    exe = name + (".exe" if os.name == "nt" else "")
    bases = [Path(getattr(sys, "_MEIPASS", "")) / "ffmpeg", Path(sys.argv[0]).resolve().parent / "ffmpeg",
             Path(__file__).resolve().parent.parent / "ffmpeg"]
    for b in bases:
        for p in (b / exe, b / "bin" / exe):
            if p.is_file():
                return str(p)
    return shutil.which(name)


FFMPEG = _find("ffmpeg")
FFPROBE = _find("ffprobe")


class MediaError(Exception):
    pass


@dataclass
class MediaInfo:
    path: str
    duration: float
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: str | None
    audio_channels: int
    size_bytes: int


def require_ffmpeg():
    if not FFMPEG or not FFPROBE:
        raise MediaError("FFmpeg not found. Put ffmpeg.exe and ffprobe.exe in the 'ffmpeg' folder next to the app, or add them to PATH.")


def probe(path: str) -> MediaInfo:
    require_ffmpeg()
    p = Path(path)
    if not p.is_file():
        raise MediaError(f"File not found: {path}")
    r = subprocess.run([FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(p)],
                       capture_output=True, text=True, creationflags=NOWIN)
    if r.returncode != 0:
        raise MediaError(f"Unsupported or corrupted media: {r.stderr.strip()[:200]}")
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s["codec_type"] == "video"), None)
    a = next((s for s in d.get("streams", []) if s["codec_type"] == "audio"), None)
    if not v:
        raise MediaError("No video stream found in this file.")
    num, _, den = v.get("avg_frame_rate", "0/1").partition("/")
    fps = float(num) / float(den) if den and float(den) else 0.0
    dur = float(d["format"].get("duration") or v.get("duration") or 0)
    if dur <= 0:
        raise MediaError("Could not determine video duration (file may be corrupted).")
    return MediaInfo(str(p), dur, int(v["width"]), int(v["height"]), fps, v["codec_name"],
                     a["codec_name"] if a else None, int(a.get("channels", 0)) if a else 0,
                     int(d["format"].get("size", p.stat().st_size)))


def _encoder_works(enc: str) -> bool:
    r = subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.2",
                        "-c:v", enc, "-f", "null", "-"], capture_output=True, creationflags=NOWIN)
    return r.returncode == 0


def detect_encoders() -> dict:
    """H.264 encoders that actually work on this machine (test-encodes a tiny clip)."""
    require_ffmpeg()
    out = subprocess.run([FFMPEG, "-hide_banner", "-encoders"], capture_output=True, text=True,
                         creationflags=NOWIN).stdout
    found = {"cpu": "libx264"}
    for key, enc in (("nvenc", "h264_nvenc"), ("qsv", "h264_qsv"), ("amf", "h264_amf")):
        if enc in out and _encoder_works(enc):
            found[key] = enc
    return found


def format_duration(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600:d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"
