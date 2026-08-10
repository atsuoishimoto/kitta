"""Main window: switches between the drop screen and the compare screen."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtWidgets import QMainWindow, QMessageBox, QStackedWidget

from kitta.gui.compare_view import CompareView
from kitta.gui.drop_view import DropView
from kitta.gui.workers import CompareWorker


def load_image(path: str | Path) -> Image.Image:
    """Load an image file into memory, normalized to RGB/RGBA."""
    with Image.open(path) as img:
        return img.copy() if img.mode in ("RGB", "RGBA") else img.convert("RGB")


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kitta")
        self.resize(1100, 750)

        self.drop_view = DropView()
        self.compare_view = CompareView()
        self._stack = QStackedWidget()
        self._stack.addWidget(self.drop_view)
        self._stack.addWidget(self.compare_view)
        self.setCentralWidget(self._stack)

        self._worker: CompareWorker | None = None

        self.drop_view.image_dropped.connect(self.start_compare)
        self.compare_view.image_dropped.connect(self.start_compare)
        self.compare_view.back_requested.connect(self.show_drop_view)

    def show_drop_view(self) -> None:
        self._stack.setCurrentWidget(self.drop_view)

    def start_compare(self, path: str) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.statusBar().showMessage(self.tr("A comparison is already running"), 3000)
            return
        presets = self.drop_view.selected_presets()
        if not presets:
            QMessageBox.warning(
                self, self.tr("Kitta"), self.tr("Select at least one preset first.")
            )
            return
        try:
            image = load_image(path)
        except OSError as exc:
            QMessageBox.critical(
                self, self.tr("Kitta"), self.tr("Cannot open image:\n{0}").format(exc)
            )
            return

        self.compare_view.begin(Path(path), image, presets)

        worker = CompareWorker(image, presets, self)
        worker.model_started.connect(self.compare_view.on_model_started)
        worker.download_progress.connect(self.compare_view.on_download_progress)
        worker.result_ready.connect(self.compare_view.on_result)
        worker.model_failed.connect(self.compare_view.on_model_failed)
        worker.compare_finished.connect(self._on_compare_finished)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

        self._stack.setCurrentWidget(self.compare_view)

    def _on_compare_finished(self, results) -> None:
        self._worker = None
