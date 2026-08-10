"""Initial screen: drop target + preset selection (product plan §10).

Choosing an image (drop or file dialog) does not start processing
immediately: the image is previewed with a Start button, and the
comparison begins only when Start is pressed.
"""

from __future__ import annotations

import itertools
import re
import urllib.request
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QUrl, Signal
from PySide6.QtGui import QImage, QKeySequence, QPainter, QPalette, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
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

import kitta
from kitta.core import paths
from kitta.core.models import DEFAULT_PRESET_NAMES, PRESETS, Preset
from kitta.gui.images import load_qimage, qimage_from_data

# ".avif" is decoded through Pillow: Qt has no AVIF plugin (see gui.images)
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".bmp", ".tif", ".tiff"}

# secondary (gray) text color, dark enough to stay readable
SECONDARY_TEXT_COLOR = "#505050"

DOWNLOAD_TIMEOUT = 10  # seconds
MAX_DOWNLOAD_SIZE = 64 * 1024 * 1024  # bytes


def is_supported_image(path: str | Path) -> bool:
    return Path(path).suffix.lower() in IMAGE_SUFFIXES


def local_image_path(mime) -> str | None:
    """Return the first supported local file in the mime data, if any."""
    if not mime.hasUrls():
        return None
    for url in mime.urls():
        if url.isLocalFile() and is_supported_image(url.toLocalFile()):
            return url.toLocalFile()
    return None


def remote_image_url(mime) -> QUrl | None:
    """Return the first http(s) URL in the mime data, if any.

    Also recognizes a plain-text URL (e.g. a copied image address).
    """
    if mime.hasUrls():
        for url in mime.urls():
            if url.scheme() in ("http", "https"):
                return url
    text = (mime.text() or "").strip()
    if re.fullmatch(r"https?://\S+", text):
        url = QUrl(text)
        if url.isValid():
            return url
    return None


def mime_has_image(mime) -> bool:
    """The mime data carries a supported file, raw image data, or a web URL."""
    return (
        local_image_path(mime) is not None or mime.hasImage() or remote_image_url(mime) is not None
    )


def image_path_from_mime(mime) -> str | None:
    """Resolve drag/paste mime data to a local file path.

    A local file wins; raw image data or a web image URL (browser drags —
    on Windows browsers provide neither a local file nor readable image
    data, only the source URL) is materialized as a file in the cache so
    the rest of the path-based flow works unchanged.
    """
    path = local_image_path(mime)
    if path is not None:
        return path
    if mime.hasImage():
        image = QImage(mime.imageData())
        if not image.isNull():
            return _save_dropped_image(image)
    url = remote_image_url(mime)
    if url is not None:
        return _download_dropped_image(url)
    return None


def accepts_drop(event) -> bool:
    return mime_has_image(event.mimeData())


def extract_dropped_image_path(event) -> str | None:
    return image_path_from_mime(event.mimeData())


def _download_dropped_image(url: QUrl) -> str | None:
    """Fetch a dragged web image and materialize it in the cache."""
    # urllib needs the percent-encoded (ASCII) form; toString() would give
    # the decoded form and crash on non-ASCII path components.
    encoded_url = bytes(url.toEncoded()).decode("ascii")
    request = urllib.request.Request(
        encoded_url, headers={"User-Agent": f"Kitta/{kitta.__version__}"}
    )
    try:
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response:
            data = response.read(MAX_DOWNLOAD_SIZE + 1)
    except (OSError, ValueError):
        return None
    if len(data) > MAX_DOWNLOAD_SIZE:
        return None
    image = qimage_from_data(data)
    if image.isNull():
        return None
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", Path(url.fileName()).stem)[:60]
    return _save_dropped_image(image, stem or None)


def _save_dropped_image(image: QImage, stem: str | None = None) -> str | None:
    directory = paths.cache_dir() / "dropped"
    directory.mkdir(parents=True, exist_ok=True)
    if stem is None:
        stem = datetime.now().strftime("dropped-%Y%m%d-%H%M%S")
    for counter in itertools.count():
        suffix = "" if counter == 0 else f"-{counter}"
        path = directory / f"{stem}{suffix}.png"
        if not path.exists():
            break
    if not image.save(str(path), "PNG"):
        return None
    return str(path)


class DropZoneLabel(QLabel):
    """The "Drop an image here" box: clickable, dashed border on hover."""

    clicked = Signal()

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"DropZoneLabel {{ font-size: 18pt; color: {SECONDARY_TEXT_COLOR};"
            f" border: 2px dashed transparent; border-radius: 8px; }}"
            f" DropZoneLabel:hover {{ border-color: palette(mid); }}"
        )

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()


class PreviewArea(QWidget):
    """Scaled preview of the selected image.

    Only the displayed image rectangle is clickable; hovering it shows a
    dashed border and the pointing-hand cursor.
    """

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(200, 150)
        self._pixmap: QPixmap | None = None
        self._hover = False

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = pixmap
        self.update()

    def image_rect(self) -> QRect:
        """Rectangle the scaled image occupies inside this widget."""
        if self._pixmap is None or self._pixmap.isNull():
            return QRect()
        size = self._pixmap.size()
        size.scale(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        rect = QRect(QPoint(0, 0), size)
        rect.moveCenter(self.rect().center())
        return rect

    def paintEvent(self, event) -> None:
        if self._pixmap is None or self._pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.image_rect()
        painter.drawPixmap(rect, self._pixmap)
        if self._hover:
            pen = QPen(self.palette().color(QPalette.ColorRole.Mid))
            pen.setStyle(Qt.PenStyle.DashLine)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(rect.adjusted(-3, -3, 2, 2))
        painter.end()

    def _set_hover(self, hover: bool) -> None:
        if hover != self._hover:
            self._hover = hover
            self.setCursor(
                Qt.CursorShape.PointingHandCursor if hover else Qt.CursorShape.ArrowCursor
            )
            self.update()

    def mouseMoveEvent(self, event) -> None:
        self._set_hover(self.image_rect().contains(event.position().toPoint()))

    def leaveEvent(self, event) -> None:
        self._set_hover(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if self.image_rect().contains(event.position().toPoint()):
            self.clicked.emit()


class DropView(QWidget):
    """Pick an image and presets, then press Start to run the comparison."""

    start_requested = Signal(str)  # path of the image to process

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._selected_path: str | None = None

        self._title_label = QLabel("Kitta")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet("font-size: 28pt; font-weight: bold;")
        self._tagline_label = QLabel(
            self.tr("Compare AI background removal models side by side. Fully offline.")
        )
        self._tagline_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tagline_label.setStyleSheet(f"font-size: 10pt; color: {SECONDARY_TEXT_COLOR};")

        # page shown while no image is selected
        self._drop_label = DropZoneLabel(self.tr("Drop an image here\nor click to choose a file"))
        self._drop_label.clicked.connect(self._open_file_dialog)
        self._paste_button = self._make_paste_button()
        drop_page = QWidget()
        drop_layout = QVBoxLayout(drop_page)
        drop_layout.setContentsMargins(48, 24, 48, 24)
        drop_layout.addWidget(self._drop_label)
        drop_layout.addSpacing(12)
        drop_layout.addWidget(self._paste_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self._paste_shortcut = QShortcut(QKeySequence(QKeySequence.StandardKey.Paste), self)
        self._paste_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self._paste_shortcut.activated.connect(self._on_paste_shortcut)

        # page shown once an image is selected
        self._preview_area = PreviewArea()
        self._preview_area.clicked.connect(self._open_file_dialog)
        self._filename_label = QLabel()
        self._filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._filename_label.setStyleSheet(f"color: {SECONDARY_TEXT_COLOR};")
        self._start_button = QPushButton(self.tr("Start"))
        self._start_button.setMinimumWidth(160)
        self._start_button.setDefault(True)
        self._start_button.clicked.connect(self._on_start_clicked)

        self._preview_paste_button = self._make_paste_button()
        preview_page = QWidget()
        preview_layout = QVBoxLayout(preview_page)
        preview_layout.addWidget(self._preview_area, stretch=1)
        preview_layout.addWidget(self._filename_label)
        preview_layout.addWidget(self._preview_paste_button, alignment=Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self._start_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self._center_stack = QStackedWidget()
        self._center_stack.addWidget(drop_page)
        self._center_stack.addWidget(preview_page)

        self._models_label = QLabel(self.tr("Select AI models to compare"))
        self._models_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._models_label.setStyleSheet(f"color: {SECONDARY_TEXT_COLOR};")

        self._checkboxes: dict[str, QCheckBox] = {}
        presets_row = QHBoxLayout()
        presets_row.addStretch()
        for preset in PRESETS.values():
            checkbox = QCheckBox(preset.display_name)
            font = checkbox.font()
            font.setPointSize(12)
            checkbox.setFont(font)
            checkbox.setChecked(preset.name in DEFAULT_PRESET_NAMES)
            self._checkboxes[preset.name] = checkbox
            presets_row.addWidget(checkbox)
        presets_row.addStretch()

        layout = QVBoxLayout(self)
        layout.addSpacing(24)
        layout.addWidget(self._title_label)
        layout.addWidget(self._tagline_label)
        layout.addWidget(self._center_stack, stretch=1)
        layout.addWidget(self._models_label)
        layout.addLayout(presets_row)
        # one line (at the checkbox font size) of breathing room at the bottom
        checkbox = next(iter(self._checkboxes.values()))
        layout.addSpacing(checkbox.fontMetrics().lineSpacing())

        QApplication.clipboard().dataChanged.connect(self._update_paste_button)
        self._update_paste_button()

    # --- selection state --------------------------------------------------

    def selected_path(self) -> str | None:
        return self._selected_path

    def set_image(self, path: str) -> bool:
        """Preview ``path`` and show the Start button. False if unreadable."""
        pixmap = QPixmap.fromImage(load_qimage(path))
        if pixmap.isNull():
            QMessageBox.critical(
                self, self.tr("Kitta"), self.tr("Cannot open image:\n{0}").format(path)
            )
            return False
        self._selected_path = path
        self._preview_area.set_pixmap(pixmap)
        self._filename_label.setText(f"{Path(path).name} ({pixmap.width()}×{pixmap.height()})")
        self._center_stack.setCurrentIndex(1)
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

    def paste_from_clipboard(self) -> None:
        mime = QApplication.clipboard().mimeData()
        path = image_path_from_mime(mime) if mime is not None else None
        if path is None:
            QMessageBox.information(self, self.tr("Kitta"), self.tr("No image in the clipboard."))
            return
        self.set_image(path)

    def _make_paste_button(self) -> QPushButton:
        paste_key = QKeySequence(QKeySequence.StandardKey.Paste).toString(
            QKeySequence.SequenceFormat.NativeText
        )
        button = QPushButton(self.tr("Paste Image ({0})").format(paste_key))
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(self.paste_from_clipboard)
        return button

    def _update_paste_button(self) -> None:
        mime = QApplication.clipboard().mimeData()
        enabled = mime is not None and mime_has_image(mime)
        self._paste_button.setEnabled(enabled)
        self._preview_paste_button.setEnabled(enabled)

    def _on_paste_shortcut(self) -> None:
        # window-scoped shortcut: act only while the drop screen is shown
        if self.isVisible() and self._paste_button.isEnabled():
            self.paste_from_clipboard()

    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Choose an image"),
            "",
            self.tr("Images ({0})").format(
                " ".join(f"*{suffix}" for suffix in sorted(IMAGE_SUFFIXES))
            ),
        )
        if path:
            self.set_image(path)

    # --- input events -----------------------------------------------------

    def dragEnterEvent(self, event) -> None:
        if accepts_drop(event):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if not accepts_drop(event):
            return
        event.acceptProposedAction()
        path = extract_dropped_image_path(event)
        if path is None:
            QMessageBox.critical(
                self, self.tr("Kitta"), self.tr("Could not retrieve the dropped image.")
            )
            return
        self.set_image(path)
