import json, os, subprocess, sys, time
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame,
    QStackedWidget, QFileDialog, QComboBox, QSpinBox, QTableWidget, QTableWidgetItem, QProgressBar, QMessageBox,
    QGroupBox, QFormLayout, QLineEdit, QListWidget, QInputDialog, QHeaderView, QPlainTextEdit)
from core import config, ffmpeg_utils as fu
from core.pipeline import analyse, export_clips
from captions import formats
from database import db
from live.buffer import RollingBuffer
from ui.theme import QSS
from ui.workers import Worker

VIDEO_FILTER = "Video (*.mp4 *.mov *.mkv *.webm *.avi *.m4v *.flv *.ts);;All files (*.*)"
ASPECTS = ["9:16", "16:9", "1:1", "4:5"]


def card(title=None):
    g = QGroupBox(title or ""); g.setLayout(QVBoxLayout()); return g


class CreatePage(QWidget):
    def __init__(self, win):
        super().__init__(); self.win = win
        self.info = self.pid = self.words = None; self.clips = []; self.worker = None
        self.setAcceptDrops(True)
        L = QVBoxLayout(self)
        t = QLabel("Create Clips"); t.setObjectName("title"); L.addWidget(t)
        src = card("1 · Source video (drag & drop supported)"); row = QHBoxLayout()
        self.path = QLineEdit(); self.path.setReadOnly(True); self.path.setPlaceholderText("No video selected")
        b = QPushButton("Import video…"); b.clicked.connect(self.pick)
        row.addWidget(self.path, 1); row.addWidget(b); src.layout().addLayout(row)
        self.meta = QLabel(""); self.meta.setObjectName("muted"); src.layout().addWidget(self.meta); L.addWidget(src)
        opt = card("2 · Clip settings"); f = QFormLayout(); opt.layout().addLayout(f)
        s = win.settings
        self.count = QComboBox(); self.count.setEditable(True)
        self.count.addItems(["5", "10", "15", "20", "30", "50"]); self.count.setCurrentText(str(s["clip_count"]))
        self.secs = QComboBox(); self.secs.setEditable(True)
        self.secs.addItems(["15", "30", "45", "60", "90", "120"]); self.secs.setCurrentText(str(s["clip_seconds"]))
        self.aspect = QComboBox(); self.aspect.setEditable(True); self.aspect.addItems(ASPECTS); self.aspect.setCurrentText(s["aspect"])
        self.style = QComboBox(); self.style.addItems(list(formats.STYLES)); self.style.setCurrentText(s["caption_style"])
        self.mode = QComboBox(); self.mode.addItems(["crop", "blur", "fit"])
        self.lang = QComboBox(); self.lang.addItems(["en", "ur", "hi", "ar", "es", "fr", "de", "pt", "auto"]); self.lang.setCurrentText(s["language"])
        for lab, w in (("Number of clips", self.count), ("Target duration (s)", self.secs), ("Aspect (ratio or WxH)", self.aspect),
                       ("Caption style", self.style), ("Reframe mode (crop follows faces)", self.mode), ("Language", self.lang)):
            f.addRow(lab, w)
        L.addWidget(opt)
        row = QHBoxLayout()
        self.go = QPushButton("GENERATE VIRAL CLIPS"); self.go.setObjectName("primary"); self.go.clicked.connect(self.generate)
        self.cancel = QPushButton("Cancel"); self.cancel.clicked.connect(lambda: self.worker and self.worker.cancel())
        self.bar = QProgressBar(); self.status = QLabel(""); self.status.setObjectName("muted")
        row.addWidget(self.go); row.addWidget(self.cancel); row.addWidget(self.bar, 1); L.addLayout(row); L.addWidget(self.status)
        self.table = QTableWidget(0, 5); self.table.setHorizontalHeaderLabels(["Export", "Start–End", "Score", "Title (editable)", "Why selected"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch); self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        L.addWidget(self.table, 1)
        row = QHBoxLayout()
        self.exp = QPushButton("Export selected clips"); self.exp.setObjectName("primary"); self.exp.clicked.connect(self.export)
        self.regen = QPushButton("Regenerate selected row"); self.regen.clicked.connect(self.regenerate)
        self.of = QPushButton("Open export folder"); self.of.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(win.settings["export_dir"])))
        row.addWidget(self.exp); row.addWidget(self.regen); row.addWidget(self.of); L.addLayout(row)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        self.load(e.mimeData().urls()[0].toLocalFile())

    def pick(self):
        p, _ = QFileDialog.getOpenFileName(self, "Import video", "", VIDEO_FILTER)
        if p: self.load(p)

    def load(self, p):
        try:
            self.info = fu.probe(p)
        except fu.MediaError as e:
            QMessageBox.warning(self, "Cannot import", str(e)); return
        i = self.info; self.path.setText(p)
        self.meta.setText(f"{fu.format_duration(i.duration)} · {i.width}x{i.height} · {i.fps:.0f} fps · {i.video_codec}/"
                          f"{i.audio_codec or 'no audio'} · {i.size_bytes / 1e6:.1f} MB")
        self.pid = db.create_project(Path(p).stem, p, self.win.settings); self.words = None
        self.table.setRowCount(0); self.clips = []

    def cur(self):
        s = dict(self.win.settings)
        s.update(clip_count=int(self.count.currentText()), clip_seconds=float(self.secs.currentText()), aspect=self.aspect.currentText(),
                 caption_style=self.style.currentText(), reframe_mode=self.mode.currentText(), language=self.lang.currentText())
        return s

    def busy(self, on):
        for w in (self.go, self.exp, self.regen): w.setEnabled(not on)

    def run(self, fn, done):
        self.busy(True); self.bar.setValue(0)
        self.worker = Worker(fn)
        self.worker.progress.connect(lambda f, m: (self.bar.setValue(int(f * 100)), self.status.setText(m)))
        self.worker.done.connect(lambda r: (self.busy(False), done(r)))
        self.worker.failed.connect(lambda m: (self.busy(False), self.status.setText(m), QMessageBox.warning(self, "Stopped", m)))
        self.worker.start()

    def generate(self):
        if not self.info: QMessageBox.information(self, "ClipForge", "Import a video first."); return
        s = self.cur(); self.run(lambda p, c: analyse(self.pid, self.info, s, p, c), self.show_clips)

    def show_clips(self, res):
        self.words, clips = res; self.clips = [c.as_dict() for c in clips]; self.fill()
        if not self.clips: QMessageBox.information(self, "ClipForge", "No suitable segments found for these settings.")

    def fill(self):
        self.table.setRowCount(len(self.clips))
        for r, c in enumerate(self.clips):
            it = QTableWidgetItem(); it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled); it.setCheckState(Qt.Checked)
            self.table.setItem(r, 0, it)
            self.table.setItem(r, 1, QTableWidgetItem(f"{fu.format_duration(c['start'])}–{fu.format_duration(c['end'])} ({c['duration']:.0f}s)"))
            self.table.setItem(r, 2, QTableWidgetItem(f"{c['score']:.0f}"))
            self.table.setItem(r, 3, QTableWidgetItem(c["title"])); self.table.setItem(r, 4, QTableWidgetItem(c["reason"]))

    def regenerate(self):
        r = self.table.currentRow()
        if r < 0 or not self.words: QMessageBox.information(self, "ClipForge", "Select a clip row first."); return
        from ai.clip_engine import select_clips
        s = self.cur(); others = [(c["start"], c["end"]) for i, c in enumerate(self.clips)]
        alt = select_clips(self.words, 1, s["clip_seconds"], exclude=others)
        if not alt: QMessageBox.information(self, "ClipForge", "No other non-overlapping segment is available."); return
        self.clips[r] = alt[0].as_dict(); self.fill()

    def export(self):
        sel = []
        for r, c in enumerate(self.clips):
            if self.table.item(r, 0).checkState() == Qt.Checked:
                c = dict(c); c["title"] = self.table.item(r, 3).text(); sel.append(c)
        if not sel: QMessageBox.information(self, "ClipForge", "Nothing selected."); return
        s = self.cur(); name = f"{Path(self.info.path).stem}_{time.strftime('%Y%m%d_%H%M')}"
        self.run(lambda p, c: export_clips(self.pid, self.info, sel, self.words, s, name, p, c),
                 lambda r: QMessageBox.information(self, "Export complete", f"{len(r)} clips saved to:\n{Path(r[0]).parent}") if r else None)


class ProjectsPage(QWidget):
    def __init__(self, win):
        super().__init__(); self.win = win; L = QVBoxLayout(self)
        t = QLabel("Dashboard · Projects"); t.setObjectName("title"); L.addWidget(t)
        self.list = QListWidget(); L.addWidget(self.list, 1)
        row = QHBoxLayout()
        for lab, fn in (("Refresh", self.refresh), ("Rename", self.rename), ("Delete project (keeps video files)", self.delete)):
            b = QPushButton(lab); b.clicked.connect(fn); row.addWidget(b)
        L.addLayout(row); self.refresh()

    def refresh(self):
        self.list.clear()
        for p in db.list_projects():
            self.list.addItem(f"{p['id']} · {p['name']} · {p['status']} · {time.strftime('%Y-%m-%d %H:%M', time.localtime(p['created']))}")

    def sel(self):
        it = self.list.currentItem(); return int(it.text().split(" · ")[0]) if it else None

    def rename(self):
        pid = self.sel()
        if pid:
            n, ok = QInputDialog.getText(self, "Rename project", "New name:")
            if ok and n.strip(): db.rename_project(pid, n.strip()); self.refresh()

    def delete(self):
        pid = self.sel()
        if pid and QMessageBox.question(self, "Delete", "Remove this project from ClipForge? Your video files are NOT deleted.") == QMessageBox.Yes:
            db.delete_project(pid); self.refresh()


class LivePage(QWidget):
    def __init__(self, win):
        super().__init__(); self.win = win; self.buf = None; L = QVBoxLayout(self)
        t = QLabel("Live Clipping (rolling buffer)"); t.setObjectName("title"); L.addWidget(t)
        n = QLabel("Records a rolling buffer from any FFmpeg input. Click a button to save the last N seconds.\n"
                   "Automatic moment detection and live transcription are not implemented yet."); n.setObjectName("muted"); L.addWidget(n)
        self.src = QLineEdit(); self.src.setPlaceholderText("rtmp://… | srt://… | video=OBS Virtual Camera (dshow) | path/to/growing_file.mp4")
        L.addWidget(self.src)
        row = QHBoxLayout(); self.start = QPushButton("Start buffer"); self.stop = QPushButton("Stop")
        self.start.clicked.connect(self.begin); self.stop.clicked.connect(self.end); row.addWidget(self.start); row.addWidget(self.stop); L.addLayout(row)
        row = QHBoxLayout()
        for s in (30, 60, 90):
            b = QPushButton(f"Save last {s}s"); b.clicked.connect(lambda _=0, s=s: self.save(s)); row.addWidget(b)
        self.custom = QSpinBox(); self.custom.setRange(5, 600); self.custom.setValue(45)
        b = QPushButton("Save last (custom)"); b.clicked.connect(lambda: self.save(self.custom.value()))
        row.addWidget(self.custom); row.addWidget(b); L.addLayout(row)
        self.status = QLabel(""); L.addWidget(self.status); L.addStretch()

    def begin(self):
        s = self.src.text().strip()
        if not s: return
        args = ["-f", "dshow", "-i", s] if s.startswith(("video=", "audio=")) else ["-i", s]
        try:
            self.buf = RollingBuffer(args, 600); self.buf.start(); self.status.setText("Buffering…")
        except Exception as e: QMessageBox.warning(self, "Live", str(e))

    def end(self):
        if self.buf: self.buf.stop(); self.status.setText("Stopped.")

    def save(self, sec):
        if not self.buf or not self.buf.running(): QMessageBox.information(self, "Live", "Start the buffer first."); return
        out = Path(self.win.settings["export_dir"]) / "Live"; out.mkdir(parents=True, exist_ok=True)
        try:
            self.status.setText("Saved: " + self.buf.save_last(sec, str(out / f"live_{time.strftime('%H%M%S')}_{sec}s.mp4")))
        except Exception as e: QMessageBox.warning(self, "Live", str(e))


class SettingsPage(QWidget):
    def __init__(self, win):
        super().__init__(); self.win = win; L = QVBoxLayout(self)
        t = QLabel("Settings"); t.setObjectName("title"); L.addWidget(t)
        g = card(); f = QFormLayout(); g.layout().addLayout(f); s = win.settings
        self.model = QComboBox(); self.model.addItems(["tiny", "base", "small", "medium", "large-v3"]); self.model.setCurrentText(s["whisper_model"])
        self.dev = QComboBox(); self.dev.addItems(["auto", "cpu", "cuda"]); self.dev.setCurrentText(s["device"])
        self.hw = QComboBox(); self.hw.addItems(["auto", "cpu", "nvenc", "qsv", "amf"]); self.hw.setCurrentText(s["hw_encoder"])
        self.out = QLineEdit(s["export_dir"])
        bb = QPushButton("Browse…"); bb.clicked.connect(lambda: self.out.setText(QFileDialog.getExistingDirectory(self, "Export folder") or self.out.text()))
        r = QHBoxLayout(); r.addWidget(self.out, 1); r.addWidget(bb)
        for lab, w in (("Whisper model", self.model), ("Transcription device", self.dev), ("Video encoder", self.hw)): f.addRow(lab, w)
        f.addRow("Export folder", r); L.addWidget(g)
        row = QHBoxLayout()
        sv = QPushButton("Save settings"); sv.setObjectName("primary"); sv.clicked.connect(self.save)
        cl = QPushButton("Clear cache"); cl.clicked.connect(self.clear)
        det = QPushButton("Detect hardware encoders"); det.clicked.connect(self.detect)
        for b in (sv, cl, det): row.addWidget(b)
        L.addLayout(row); self.info = QLabel(""); self.info.setObjectName("muted"); L.addWidget(self.info)
        self.info.setText(f"FFmpeg: {fu.FFMPEG or 'NOT FOUND'}"); L.addStretch()

    def save(self):
        self.win.settings.update(whisper_model=self.model.currentText(), device=self.dev.currentText(), hw_encoder=self.hw.currentText(),
                                 export_dir=self.out.text()); config.save_settings(self.win.settings); self.info.setText("Saved.")

    def clear(self):
        n = 0
        for f in (config.CACHE_DIR / "live").glob("*"):
            f.unlink(missing_ok=True); n += 1
        self.info.setText(f"Removed {n} cache files.")

    def detect(self):
        try: self.info.setText("Working encoders: " + ", ".join(fu.detect_encoders().values()))
        except Exception as e: self.info.setText(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.settings = config.load_settings(); self.setWindowTitle("CLIPFORGE AI"); self.resize(1280, 820)
        root = QWidget(); root.setObjectName("root"); self.setCentralWidget(root); H = QHBoxLayout(root); H.setContentsMargins(0, 0, 0, 0)
        side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(220); S = QVBoxLayout(side)
        lg = QLabel("CLIPFORGE AI"); lg.setObjectName("logo"); S.addWidget(lg)
        self.stack = QStackedWidget(); self.btns = []
        pages = [("Dashboard", ProjectsPage), ("Create Clips", CreatePage), ("Live Clipping", LivePage), ("Settings", SettingsPage)]
        for i, (name, cls) in enumerate(pages):
            self.stack.addWidget(cls(self)); b = QPushButton(name); b.setObjectName("nav"); b.setCheckable(True)
            b.clicked.connect(lambda _=0, i=i: self.go(i)); S.addWidget(b); self.btns.append(b)
        S.addStretch(); H.addWidget(side); H.addWidget(self.stack, 1); self.go(1)
        if not fu.FFMPEG:
            QMessageBox.warning(self, "FFmpeg missing", "FFmpeg was not found. Place ffmpeg.exe and ffprobe.exe in the 'ffmpeg' folder next to the app.")

    def go(self, i):
        self.stack.setCurrentIndex(i)
        for k, b in enumerate(self.btns): b.setChecked(k == i)
        if i == 0: self.stack.widget(0).refresh()


def run():
    app = QApplication(sys.argv); app.setStyleSheet(QSS)
    w = MainWindow(); w.show(); sys.exit(app.exec())
