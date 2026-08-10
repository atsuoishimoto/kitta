"""Comparison screen (product plan §11-12).

A grid of result cells with synchronized zoom/pan image views,
Original/Mask/Result display switching, Checker/White/Black backgrounds,
result selection and PNG/mask saving.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from kitta.gui.drop_view import accepts_drop, extract_dropped_image_path
from kitta.gui.image_view import Background, ImageView, ViewSynchronizer

GRID_COLUMNS = 3


class ViewMode(Enum):
    ORIGINAL = "original"
    MASK = "mask"
    RESULT = "result"


def pil_to_qimage(image) -> QImage:
    """Convert a PIL image to a detached QImage."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, image.width * 4, QImage.Format_RGBA8888)
    return qimage.copy()


class ResultCell(QFrame):
    clicked = Signal(object)  # self

    def __init__(self, preset, original_pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.preset = preset
        self.result = None
        self.selected = False
        self._pixmaps: dict[ViewMode, QPixmap] = {ViewMode.ORIGINAL: original_pixmap}
        self._displayed: ViewMode = ViewMode.ORIGINAL

        self.setFrameShape(QFrame.Shape.StyledPanel)

        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.view = ImageView()
        self.view.set_pixmap(original_pixmap)
        self.view.clicked.connect(lambda: self.clicked.emit(self))

        self.status_label = QLabel(self.tr("Waiting..."))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(12)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.title_label)
        layout.addWidget(self.view, stretch=1)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)

        self.set_selected(False)

    # --- state changes (driven by worker signals) -------------------------

    def show_started(self) -> None:
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # busy indicator
        self.status_label.setText(self.tr("Processing..."))

    def show_download_progress(self, done: int, total: int) -> None:
        self.progress_bar.setVisible(True)
        if total:
            self.progress_bar.setRange(0, 1000)
            self.progress_bar.setValue(min(1000, done * 1000 // total))
        else:
            self.progress_bar.setRange(0, 0)
        self.status_label.setText(self.tr("Downloading model..."))

    def show_result(self, result, view_mode: ViewMode) -> None:
        self.result = result
        self._pixmaps[ViewMode.RESULT] = QPixmap.fromImage(pil_to_qimage(result.image))
        self._pixmaps[ViewMode.MASK] = QPixmap.fromImage(pil_to_qimage(result.mask))
        self.progress_bar.setVisible(False)
        self.status_label.setText(self.tr("{0:.2f} s").format(result.elapsed))
        self.set_view_mode(view_mode)

    def show_error(self, message: str) -> None:
        self.progress_bar.setVisible(False)
        self.status_label.setText(self.tr("Failed: {0}").format(message))
        self.status_label.setStyleSheet("color: red;")

    # --- display ----------------------------------------------------------

    def set_view_mode(self, mode: ViewMode) -> None:
        """Show ``mode`` if its pixmap exists; fall back to the original."""
        shown = mode if mode in self._pixmaps else ViewMode.ORIGINAL
        self._displayed = shown
        self.view.set_pixmap(self._pixmaps[shown])

    def displayed_mode(self) -> ViewMode:
        return self._displayed

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        # Same border width in both states so the content area never shifts.
        color = "palette(highlight)" if selected else "transparent"
        self.setStyleSheet(f"ResultCell {{ border: 2px solid {color}; }}")
        self._update_title()

    def _update_title(self) -> None:
        star = "★ " if self.selected else ""
        self.title_label.setText(f"{star}{self.preset.display_name} ({self.preset.model.name})")

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self)
        super().mousePressEvent(event)


class CompareView(QWidget):
    back_requested = Signal()
    image_dropped = Signal(str)  # a new image dropped directly on this screen

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.source_path: Path | None = None
        self.cells: list[ResultCell] = []
        self._synchronizer = ViewSynchronizer()
        self._selected_cell: ResultCell | None = None
        self._view_mode = ViewMode.RESULT

        # --- toolbar ------------------------------------------------------
        self._back_button = QPushButton(self.tr("New Image"))
        self._back_button.clicked.connect(self.back_requested)

        self._mode_group = QButtonGroup(self)
        mode_buttons = [
            (ViewMode.ORIGINAL, self.tr("Original")),
            (ViewMode.MASK, self.tr("Mask")),
            (ViewMode.RESULT, self.tr("Result")),
        ]
        self._mode_buttons: dict[ViewMode, QToolButton] = {}
        for mode, label in mode_buttons:
            button = QToolButton()
            button.setText(label)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, mode=mode: self.set_view_mode(mode))
            self._mode_group.addButton(button)
            self._mode_buttons[mode] = button
        self._mode_buttons[ViewMode.RESULT].setChecked(True)

        self._background_group = QButtonGroup(self)
        background_buttons = [
            (Background.CHECKER, self.tr("Checker")),
            (Background.WHITE, self.tr("White")),
            (Background.BLACK, self.tr("Black")),
        ]
        self._background_buttons: dict[Background, QToolButton] = {}
        for background, label in background_buttons:
            button = QToolButton()
            button.setText(label)
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, background=background: self.set_background(background)
            )
            self._background_group.addButton(button)
            self._background_buttons[background] = button
        self._background_buttons[Background.CHECKER].setChecked(True)

        self._save_png_button = QPushButton(self.tr("Save PNG"))
        self._save_png_button.setEnabled(False)
        self._save_png_button.clicked.connect(self.save_png)
        self._save_mask_button = QPushButton(self.tr("Save Mask"))
        self._save_mask_button.setEnabled(False)
        self._save_mask_button.clicked.connect(self.save_mask)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self._back_button)
        toolbar.addSpacing(16)
        for button in self._mode_buttons.values():
            toolbar.addWidget(button)
        toolbar.addSpacing(16)
        for button in self._background_buttons.values():
            toolbar.addWidget(button)
        toolbar.addStretch()
        toolbar.addWidget(self._save_png_button)
        toolbar.addWidget(self._save_mask_button)

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self._grid_host, stretch=1)

    # --- lifecycle --------------------------------------------------------

    def begin(self, source_path: Path, image, presets) -> None:
        """Reset the grid for a new comparison run."""
        self.source_path = Path(source_path)
        for cell in self.cells:
            self._grid.removeWidget(cell)
            cell.deleteLater()
        self.cells = []
        self._synchronizer = ViewSynchronizer()
        self._selected_cell = None
        self._update_save_buttons()

        original = QPixmap.fromImage(pil_to_qimage(image))
        for index, preset in enumerate(presets):
            cell = ResultCell(preset, original)
            cell.clicked.connect(self._on_cell_clicked)
            cell.view.set_background(self._current_background())
            cell.set_view_mode(self._view_mode)
            self._grid.addWidget(cell, index // GRID_COLUMNS, index % GRID_COLUMNS)
            self._synchronizer.add(cell.view)
            self.cells.append(cell)

        # Distribute space by stretch, not by size hints: a cell's size hint
        # changes when its style sheet changes (selection), which would
        # otherwise shrink that column.
        used_columns = min(len(self.cells), GRID_COLUMNS)
        used_rows = (len(self.cells) + GRID_COLUMNS - 1) // GRID_COLUMNS
        for column in range(max(self._grid.columnCount(), used_columns)):
            self._grid.setColumnStretch(column, 1 if column < used_columns else 0)
        for row in range(max(self._grid.rowCount(), used_rows)):
            self._grid.setRowStretch(row, 1 if row < used_rows else 0)

        QTimer.singleShot(0, self._synchronizer.fit_all)

    # --- worker signal slots ----------------------------------------------

    def on_model_started(self, index: int, preset) -> None:
        self.cells[index].show_started()

    def on_download_progress(self, index: int, preset, done: int, total: int) -> None:
        self.cells[index].show_download_progress(done, total)

    def on_result(self, index: int, preset, result) -> None:
        self.cells[index].show_result(result, self._view_mode)

    def on_model_failed(self, index: int, preset, message: str) -> None:
        self.cells[index].show_error(message)

    # --- display switching ------------------------------------------------

    def set_view_mode(self, mode: ViewMode) -> None:
        self._view_mode = mode
        self._mode_buttons[mode].setChecked(True)
        for cell in self.cells:
            cell.set_view_mode(mode)

    def view_mode(self) -> ViewMode:
        return self._view_mode

    def set_background(self, background: Background) -> None:
        self._background_buttons[background].setChecked(True)
        for cell in self.cells:
            cell.view.set_background(background)

    def _current_background(self) -> Background:
        for background, button in self._background_buttons.items():
            if button.isChecked():
                return background
        return Background.CHECKER

    # --- selection / saving -----------------------------------------------

    def _on_cell_clicked(self, cell: ResultCell) -> None:
        if cell.result is None:
            return
        for other in self.cells:
            other.set_selected(other is cell)
        self._selected_cell = cell
        self._update_save_buttons()

    def selected_result(self):
        return self._selected_cell.result if self._selected_cell else None

    def _update_save_buttons(self) -> None:
        enabled = self._selected_cell is not None
        self._save_png_button.setEnabled(enabled)
        self._save_mask_button.setEnabled(enabled)

    def save_png(self) -> None:
        self._save(ViewMode.RESULT, "-cutout.png", self.tr("Save PNG"))

    def save_mask(self) -> None:
        self._save(ViewMode.MASK, "-mask.png", self.tr("Save Mask"))

    def _save(self, kind: ViewMode, suffix: str, caption: str) -> None:
        result = self.selected_result()
        if result is None or self.source_path is None:
            return
        default = self.source_path.parent / (self.source_path.stem + suffix)
        path, _ = QFileDialog.getSaveFileName(
            self, caption, str(default), self.tr("PNG images (*.png)")
        )
        if not path:
            return
        image = result.image if kind is ViewMode.RESULT else result.mask
        try:
            image.save(path, format="PNG")
        except OSError as exc:
            QMessageBox.critical(
                self, self.tr("Kitta"), self.tr("Cannot save file:\n{0}").format(exc)
            )

    # --- drag & drop of a new image ---------------------------------------

    def dragEnterEvent(self, event) -> None:
        if accepts_drop(event):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        path = extract_dropped_image_path(event)
        if path is not None:
            event.acceptProposedAction()
            self.image_dropped.emit(path)
