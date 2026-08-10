"""Background execution of core.compare.

Inference never runs on the GUI thread: MainWindow starts a
CompareWorker (a QThread) and consumes its signals. The core layer stays
synchronous; all threading lives here.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from kitta.core.compare import CompareCallbacks, compare


class CompareWorker(QThread):
    """Runs ``core.compare`` over one image in a background thread.

    Signal arguments use ``object`` for Preset / RemovalResult instances.
    """

    model_started = Signal(int, object)  # index, Preset
    download_progress = Signal(int, object, int, int)  # index, Preset, done, total
    result_ready = Signal(int, object, object)  # index, Preset, RemovalResult
    model_failed = Signal(int, object, str)  # index, Preset, error message
    compare_finished = Signal(list)  # list[RemovalResult | None]

    def __init__(self, image, presets, parent=None):
        super().__init__(parent)
        self._image = image
        self._presets = list(presets)

    def run(self) -> None:
        callbacks = CompareCallbacks(
            on_start=lambda i, p: self.model_started.emit(i, p),
            on_download_progress=lambda i, p, d, t: self.download_progress.emit(i, p, d, t),
            on_result=lambda i, p, r: self.result_ready.emit(i, p, r),
            on_error=lambda i, p, e: self.model_failed.emit(i, p, str(e)),
        )
        try:
            results = compare(self._image, self._presets, callbacks)
        except Exception as exc:  # noqa: BLE001 - surface unexpected errors to the UI
            for index, preset in enumerate(self._presets):
                self.model_failed.emit(index, preset, str(exc))
            results = [None] * len(self._presets)
        self.compare_finished.emit(results)
