"""High-level jobs used by the UI: analyse a video, export clips."""
from pathlib import Path
from ai import transcriber, clip_engine
from core import ffmpeg_utils as fu
from database import db
from export import exporter


def analyse(pid, info, s, progress=lambda f, m="": None, cancelled=lambda: False):
    words = db.load_transcript(pid)  # resume: reuse transcript if already done
    if words is None:
        progress(0.0, "Transcribing (first run downloads the Whisper model)…")
        words = transcriber.transcribe(info.path, s["whisper_model"], s["language"], s["device"],
                                       lambda f: progress(f * 0.9, "Transcribing…"), cancelled)
        db.save_transcript(pid, words)
    progress(0.92, "Finding the best moments…")
    clips = clip_engine.select_clips(words, int(s["clip_count"]), float(s["clip_seconds"]))
    db.save_clips(pid, [c.as_dict() for c in clips])
    progress(1.0, f"Found {len(clips)} clips")
    return words, clips


def export_clips(pid, info, clips, words, s, project_name, progress=lambda f, m="": None, cancelled=lambda: False):
    root = Path(s["export_dir"]) / project_name.replace(" ", "_")
    done = []
    for n, c in enumerate(clips, 1):
        base, span = (n - 1) / len(clips), 1 / len(clips)
        out = root / f"Clip_{n:02d}.mp4"
        exporter.render_clip(info, c, words, out, s["aspect"], s.get("reframe_mode", "crop"), s["caption_style"],
                             s["hw_encoder"], progress=lambda f: progress(base + f * span, f"Rendering clip {n}/{len(clips)}"),
                             cancelled=cancelled)
        exporter.write_sidecars(root, n, c, words)
        exporter.thumbnail(info, c, root / "Thumbnails" / f"Clip_{n:02d}.jpg")
        db.record_export(pid, str(out))
        done.append(str(out))
    progress(1.0, "Export complete")
    return done
