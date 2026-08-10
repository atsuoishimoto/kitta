"""Initial screen: drop target + preset selection (product plan §10)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

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


class DropView(QWidget):
    """Drop an image (or click to pick one) and choose presets to compare."""

    image_dropped = Signal(str)  # path of the dropped/chosen image file

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self._drop_label = QLabel(self.tr("Drop an image here\nor click to choose a file"))
        self._drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._drop_label.setStyleSheet("font-size: 18pt; color: palette(mid);")

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
        layout.addStretch()
        layout.addWidget(self._drop_label)
        layout.addStretch()
        layout.addLayout(presets_row)

    def selected_presets(self) -> list[Preset]:
        return [
            PRESETS[name] for name, checkbox in self._checkboxes.items() if checkbox.isChecked()
        ]

    def set_selected_presets(self, names) -> None:
        for name, checkbox in self._checkboxes.items():
            checkbox.setChecked(name in names)

    # --- input events ----------------------------------------------------

    def mousePressEvent(self, event) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Choose an image"),
            "",
            self.tr("Images (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff)"),
        )
        if path:
            self.image_dropped.emit(path)

    def dragEnterEvent(self, event) -> None:
        if dropped_image_path(event) is not None:
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        path = dropped_image_path(event)
        if path is not None:
            event.acceptProposedAction()
            self.image_dropped.emit(path)
