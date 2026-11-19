"""Rolling live buffer (stream-copy, near-zero CPU). Manual 'save last N seconds'.

NOT yet implemented: live transcription and automatic interesting-moment detection (see TODO.md).
"""
import subprocess, time
from pathlib import Path
from core import ffmpeg_utils as fu
from core.config import CACHE_DIR

SEG = 2


class RollingBuffer:
    def __init__(self, source_args: list[str], keep_seconds=300):
        self.src, self.keep, self.proc = source_args, keep_seconds, None
        self.dir = CACHE_DIR / "live"; self.dir.mkdir(parents=True, exist_ok=True)

    def start(self):
        fu.require_ffmpeg()
        for f in self.dir.glob("buf_*.ts"):
            f.unlink(missing_ok=True)
        self.proc = subprocess.Popen(
            [fu.FFMPEG, "-hide_banner", "-loglevel", "error", *self.src, "-c:v", "libx264", "-preset", "ultrafast",
             "-g", str(SEG * 30), "-c:a", "aac", "-f", "segment", "-segment_time", str(SEG), "-reset_timestamps", "1",
             "-strftime", "1", str(self.dir / "buf_%Y%m%d%H%M%S.ts")],
            stdin=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=fu.NOWIN)

    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def prune(self):
        files = sorted(self.dir.glob("buf_*.ts"))
        for f in files[:-(self.keep // SEG + 2)]:
            f.unlink(missing_ok=True)

    def save_last(self, seconds: int, out_path: str):
        self.prune()
        files = sorted(self.dir.glob("buf_*.ts"))[:-1]  # last file is still being written
        files = files[-max(1, seconds // SEG):]
        if not files:
            raise RuntimeError("Buffer is empty - wait a few seconds after starting.")
        lst = self.dir / "list.txt"
        lst.write_text("".join(f"file '{f.as_posix()}'\n" for f in files), "utf-8")
        r = subprocess.run([fu.FFMPEG, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                            "-c", "copy", out_path], capture_output=True, text=True, creationflags=fu.NOWIN)
        if r.returncode:
            raise RuntimeError(r.stderr[-300:])
        return out_path

    def stop(self):
        if self.running():
            try:
                self.proc.stdin.write(b"q"); self.proc.stdin.flush()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
