"""Comparison screen.

Phase 4 placeholder: one cell per preset showing status text and a plain
thumbnail of the result. Phase 5 replaces the cells with synchronized
zoom/pan image views, background switching, selection and saving.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

GRID_COLUMNS = 3


def pil_to_qimage(image) -> QImage:
    """Convert a PIL image to a detached QImage."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, image.width * 4, QImage.Format_RGBA8888)
    return qimage.copy()


class ResultCell(QFrame):
    def __init__(self, preset, parent=None):
        super().__init__(parent)
        self.preset = preset
        self.result = None
        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.title_label = QLabel(preset.display_name)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(160, 120)
        self.status_label = QLabel(self.tr("Waiting..."))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(self.title_label)
        layout.addWidget(self.image_label, stretch=1)
        layout.addWidget(self.status_label)

    def show_started(self) -> None:
        self.status_label.setText(self.tr("Processing..."))

    def show_download_progress(self, done: int, total: int) -> None:
        if total:
            percent = min(100, 100 * done // total)
            self.status_label.setText(self.tr("Downloading model... {0}%").format(percent))
        else:
            self.status_label.setText(self.tr("Downloading model..."))

    def show_result(self, result) -> None:
        self.result = result
        pixmap = QPixmap.fromImage(pil_to_qimage(result.image))
        self.image_label.setPixmap(
            pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.status_label.setText(self.tr("{0:.2f}s").format(result.elapsed))

    def show_error(self, message: str) -> None:
        self.status_label.setText(self.tr("Failed: {0}").format(message))


class CompareView(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.source_path: Path | None = None
        self.cells: list[ResultCell] = []

        self._back_button = QPushButton(self.tr("Try another image"))
        self._back_button.clicked.connect(self.back_requested)

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)

        layout = QVBoxLayout(self)
        layout.addWidget(self._back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self._grid_host, stretch=1)

    def begin(self, source_path: Path, image, presets) -> None:
        self.source_path = source_path
        for cell in self.cells:
            self._grid.removeWidget(cell)
            cell.deleteLater()
        self.cells = []
        for index, preset in enumerate(presets):
            cell = ResultCell(preset)
            self._grid.addWidget(cell, index // GRID_COLUMNS, index % GRID_COLUMNS)
            self.cells.append(cell)

    # --- worker signal slots ---------------------------------------------

    def on_model_started(self, index: int, preset) -> None:
        self.cells[index].show_started()

    def on_download_progress(self, index: int, preset, done: int, total: int) -> None:
        self.cells[index].show_download_progress(done, total)

    def on_result(self, index: int, preset, result) -> None:
        self.cells[index].show_result(result)

    def on_model_failed(self, index: int, preset, message: str) -> None:
        self.cells[index].show_error(message)
