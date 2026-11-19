import logging, traceback
from PySide6.QtCore import QThread, Signal

log = logging.getLogger("clipforge")


class Worker(QThread):
    progress = Signal(float, str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn, self._cancel = fn, False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            self.done.emit(self.fn(lambda f, m="": self.progress.emit(f, m), lambda: self._cancel))
        except InterruptedError:
            self.failed.emit("Cancelled.")
        except Exception as e:
            log.error("worker failed\n%s", traceback.format_exc())
            self.failed.emit(str(e))
