"""Clip rendering with FFmpeg: reframe + burned captions + progress/cancel. Writes .part then renames."""
import os, re, subprocess, tempfile
from pathlib import Path
from core import ffmpeg_utils as fu
from captions import formats
from video import reframe

RES = {"720p": 720, "1080p": 1080, "1440p": 1440, "2160p": 2160}


def encoder_args(hw: str, codec="h264", crf=18):
    enc = fu.detect_encoders() if hw != "cpu" else {"cpu": "libx264"}
    name = "cpu" if hw in ("auto", "cpu") and hw == "cpu" else hw
    if hw == "auto":
        name = next((k for k in ("nvenc", "qsv", "amf") if k in enc), "cpu")
    e = enc.get(name, "libx264")
    if codec == "h265":
        e = {"libx264": "libx265", "h264_nvenc": "hevc_nvenc", "h264_qsv": "hevc_qsv", "h264_amf": "hevc_amf"}[e]
    if e in ("libx264", "libx265"):
        return ["-c:v", e, "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p"]
    if "nvenc" in e:
        return ["-c:v", e, "-preset", "p5", "-cq", str(crf), "-pix_fmt", "yuv420p"]
    return ["-c:v", e, "-b:v", "8M", "-pix_fmt", "yuv420p"]


def render_clip(info, clip, words, out_path, aspect="9:16", mode="crop", caption_style="educational",
                hw="auto", codec="h264", crf=18, short_side=1080, progress=None, cancelled=lambda: False,
                burn_captions=True):
    fu.require_ffmpeg()
    out_w, out_h = reframe.parse_aspect(aspect)
    k = short_side / min(out_w, out_h)
    out_w, out_h = int(out_w * k) // 2 * 2, int(out_h * k) // 2 * 2
    dur = clip["end"] - clip["start"]
    cx = reframe.face_center_x(info.path, clip["start"], clip["end"]) if mode == "crop" else 0.5
    vf = reframe.build_filter(info.width, info.height, out_w, out_h, mode, cx)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    part = out_path.with_suffix(".part.mp4")
    with tempfile.TemporaryDirectory() as td:
        if burn_captions:
            cw = shift_words = formats.shift_words(words, clip["start"], clip["end"])
            (Path(td) / "c.ass").write_text(formats.to_ass(cw, caption_style, out_w, out_h), "utf-8")
            vf += (",ass=c.ass" if not vf.startswith("split") else "[v];[v]ass=c.ass")
        flag = "-filter_complex" if vf.startswith("split") else "-vf"
        cmd = [fu.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{clip['start']:.3f}", "-i", info.path,
               "-t", f"{dur:.3f}", flag, vf, *encoder_args(hw, codec, crf), "-c:a", "aac", "-b:a", "192k",
               "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(part)]
        p = subprocess.Popen(cmd, cwd=td, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             creationflags=fu.NOWIN)
        for line in p.stdout:
            if cancelled():
                p.kill(); part.unlink(missing_ok=True)
                raise InterruptedError("Export cancelled")
            m = re.match(r"out_time_(?:us|ms)=(\d+)", line)
            if m and progress:
                progress(min(1.0, int(m.group(1)) / 1e6 / dur))
        err = p.stderr.read()
        if p.wait() != 0:
            part.unlink(missing_ok=True)
            raise RuntimeError(f"FFmpeg failed: {err.strip()[-400:]}")
    os.replace(part, out_path)
    return str(out_path)


def write_sidecars(project_dir: Path, idx: int, clip: dict, words):
    cap = project_dir / "Captions"; cap.mkdir(parents=True, exist_ok=True)
    w = formats.shift_words(words, clip["start"], clip["end"])
    (cap / f"Clip_{idx:02d}.srt").write_text(formats.to_srt(w), "utf-8")
    (cap / f"Clip_{idx:02d}.vtt").write_text(formats.to_vtt(w), "utf-8")


def thumbnail(info, clip, out_path):
    t = clip["start"] + min(1.0, (clip["end"] - clip["start"]) / 3)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([fu.FFMPEG, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", info.path, "-frames:v", "1",
                    "-q:v", "2", str(out_path)], creationflags=fu.NOWIN)
