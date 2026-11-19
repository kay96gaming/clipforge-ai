"""App paths and persisted settings (JSON)."""
import json
from pathlib import Path

APP_DIR = Path.home() / "ClipForgeAI"
CACHE_DIR = APP_DIR / "cache"
LOG_FILE = APP_DIR / "clipforge.log"
SETTINGS_FILE = APP_DIR / "settings.json"
DEFAULT_EXPORT_DIR = Path.home() / "Videos" / "CLIPFORGE_EXPORTS"

DEFAULTS = {
    "whisper_model": "small",
    "device": "auto",
    "language": "en",
    "aspect": "9:16",
    "caption_style": "educational",
    "clip_count": 10,
    "clip_seconds": 45,
    "export_dir": str(DEFAULT_EXPORT_DIR),
    "hw_encoder": "auto",
}

for d in (APP_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    s = dict(DEFAULTS)
    try:
        s.update(json.loads(SETTINGS_FILE.read_text("utf-8")))
    except (OSError, ValueError):
        pass
    return s


def save_settings(s: dict) -> None:
    SETTINGS_FILE.write_text(json.dumps(s, indent=2), "utf-8")
