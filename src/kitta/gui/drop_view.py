"""Initial screen: drop target + preset selection (product plan §10).

Choosing an image (drop or file dialog) does not start processing
immediately: the image is previewed with a Start button, and the
comparison begins only when Start is pressed.
"""

from __future__ import annotations

import itertools
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from kitta.core import paths
from kitta.core.models import DEFAULT_PRESET_NAMES, PRESETS, Preset

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def is_supported_image(path: str | Path) -> bool:
    return Path(path).suffix.lower() in IMAGE_SUFFIXES


def dropped_image_path(event) -> str | None:
    """Return the first supported local file in a drag/drop event."""
    mime = event.mimeData()
    if not mime.hasUrls():
        return None
    for url in mime.urls():
        if url.isLocalFile() and is_supported_image(url.toLocalFile()):
            return url.toLocalFile()
    return None


def accepts_drop(event) -> bool:
    """A drop is usable if it carries a supported file or raw image data."""
    return dropped_image_path(event) is not None or event.mimeData().hasImage()


def extract_dropped_image_path(event) -> str | None:
    """Resolve a drop to a local file path.

    A local file wins; otherwise raw image data (e.g. an image dragged
    out of a browser) is materialized as a PNG in the cache so the rest
    of the path-based flow works unchanged.
    """
    path = dropped_image_path(event)
    if path is not None:
        return path
    mime = event.mimeData()
    if mime.hasImage():
        image = QImage(mime.imageData())
        if not image.isNull():
            return _save_dropped_image(image)
    return None


def _save_dropped_image(image: QImage) -> str | None:
    directory = paths.cache_dir() / "dropped"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for counter in itertools.count():
        suffix = "" if counter == 0 else f"-{counter}"
        path = directory / f"dropped-{stamp}{suffix}.png"
        if not path.exists():
            break
    if not image.save(str(path), "PNG"):
        return None
    return str(path)


class DropView(QWidget):
    """Pick an image and presets, then press Start to run the comparison."""

    start_requested = Signal(str)  # path of the image to process

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._selected_path: str | None = None
        self._preview_pixmap: QPixmap | None = None

        self._title_label = QLabel("Kitta")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet("font-size: 28pt; font-weight: bold;")
        self._tagline_label = QLabel(
            self.tr("Compare AI background removal models side by side. Fully offline.")
        )
        self._tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tagline_label.setStyleSheet("font-size: 10pt; color: palette(mid);")

        # page shown while no image is selected
        self._drop_label = QLabel(self.tr("Drop an image here\nor click to choose a file"))
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_label.setStyleSheet("font-size: 18pt; color: palette(mid);")

        # page shown once an image is selected
        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setMinimumSize(200, 150)
        self._filename_label = QLabel()
        self._filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._filename_label.setStyleSheet("color: palette(mid);")
        self._start_button = QPushButton(self.tr("Start"))
        self._start_button.setMinimumWidth(160)
        self._start_button.setDefault(True)
        self._start_button.clicked.connect(self._on_start_clicked)

        preview_page = QWidget()
        preview_layout = QVBoxLayout(preview_page)
        preview_layout.addWidget(self._preview_label, stretch=1)
        preview_layout.addWidget(self._filename_label)
        preview_layout.addWidget(self._start_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self._center_stack = QStackedWidget()
        self._center_stack.addWidget(self._drop_label)
        self._center_stack.addWidget(preview_page)

        self._checkboxes: dict[str, QCheckBox] = {}
        presets_row = QHBoxLayout()
        presets_row.addStretch()
        for preset in PRESETS.values():
            checkbox = QCheckBox(preset.display_name)
            checkbox.setChecked(preset.name in DEFAULT_PRESET_NAMES)
            self._checkboxes[preset.name] = checkbox
            presets_row.addWidget(checkbox)
        presets_row.addStretch()

        layout = QVBoxLayout(self)
        layout.addSpacing(24)
        layout.addWidget(self._title_label)
        layout.addWidget(self._tagline_label)
        layout.addWidget(self._center_stack, stretch=1)
        layout.addLayout(presets_row)

    # --- selection state --------------------------------------------------

    def selected_path(self) -> str | None:
        return self._selected_path

    def set_image(self, path: str) -> bool:
        """Preview ``path`` and show the Start button. False if unreadable."""
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.critical(
                self, self.tr("Kitta"), self.tr("Cannot open image:\n{0}").format(path)
            )
            return False
        self._selected_path = path
        self._preview_pixmap = pixmap
        self._filename_label.setText(f"{Path(path).name} ({pixmap.width()}×{pixmap.height()})")
        self._center_stack.setCurrentIndex(1)
        self._update_preview()
        return True

    def selected_presets(self) -> list[Preset]:
        return [
            PRESETS[name] for name, checkbox in self._checkboxes.items() if checkbox.isChecked()
        ]

    def set_selected_presets(self, names) -> None:
        for name, checkbox in self._checkboxes.items():
            checkbox.setChecked(name in names)

    def _on_start_clicked(self) -> None:
        if self._selected_path is not None:
            self.start_requested.emit(self._selected_path)

    def _update_preview(self) -> None:
        if self._preview_pixmap is None:
            return
        self._preview_label.setPixmap(
            self._preview_pixmap.scaled(
                self._preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    # --- input events -----------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_preview()

    def mousePressEvent(self, event) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Choose an image"),
            "",
            self.tr("Images (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)"),
        )
        if path:
            self.set_image(path)

    def dragEnterEvent(self, event) -> None:
        if accepts_drop(event):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        path = extract_dropped_image_path(event)
        if path is not None:
            event.acceptProposedAction()
            self.set_image(path)
