"""Image decoding helpers shared by the GUI.

Qt and Pillow do not support the same formats: the PySide6 wheels ship no
AVIF plugin, while Pillow decodes AVIF out of the box. Everything that
turns a file (or downloaded bytes) into a QImage goes through here so the
Pillow fallback applies everywhere.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

from PIL import Image
from PySide6.QtGui import QImage


def pil_to_qimage(image) -> QImage:
    """Convert a PIL image to a detached QImage."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, image.width * 4, QImage.Format_RGBA8888)
    return qimage.copy()


def _pil_qimage(open_image: Callable[[], Image.Image]) -> QImage:
    """Decode with Pillow; a null QImage if Pillow cannot read it either."""
    try:
        with open_image() as image:
            return pil_to_qimage(image)
    except (OSError, ValueError):
        return QImage()


def load_qimage(path: str | Path) -> QImage:
    """Load an image file, falling back to Pillow for e.g. AVIF.

    Returns a null QImage when neither library can decode the file.
    """
    image = QImage(str(path))
    if not image.isNull():
        return image
    return _pil_qimage(lambda: Image.open(path))


def qimage_from_data(data: bytes) -> QImage:
    """Decode in-memory image bytes, falling back to Pillow for e.g. AVIF."""
    image = QImage.fromData(data)
    if not image.isNull():
        return image
    return _pil_qimage(lambda: Image.open(io.BytesIO(data)))
