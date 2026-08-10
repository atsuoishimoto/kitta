"""QGraphicsView-based image display with synchronized zoom/pan.

Synchronization: every user-driven change emits ``view_changed``; a
ViewSynchronizer copies the source view's transform and scroll positions
to the other views. ``apply_view`` sets a guard flag so the copies never
re-emit, which prevents feedback loops.
"""

from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPixmap, QTransform
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView


class Background(Enum):
    CHECKER = "checker"
    WHITE = "white"
    BLACK = "black"


MIN_SCALE = 0.05
MAX_SCALE = 50.0
ZOOM_STEP = 1.25

_checker_cache: QPixmap | None = None


def checker_pixmap() -> QPixmap:
    global _checker_cache
    if _checker_cache is None:
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(255, 255, 255))
        painter = QPainter(pixmap)
        gray = QColor(204, 204, 204)
        painter.fillRect(0, 0, 16, 16, gray)
        painter.fillRect(16, 16, 16, 16, gray)
        painter.end()
        _checker_cache = pixmap
    return _checker_cache


class ImageView(QGraphicsView):
    view_changed = Signal()  # zoom or pan to propagate to synced views
    user_interacted = Signal()  # explicit wheel zoom / drag pan by the user
    clicked = Signal()  # press + release without dragging

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._item = QGraphicsPixmapItem()
        self._item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._scene.addItem(self._item)
        self.setScene(self._scene)

        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        self._background = Background.CHECKER
        self._syncing = False
        self._press_pos = None

        self.horizontalScrollBar().valueChanged.connect(self._emit_view_changed)
        self.verticalScrollBar().valueChanged.connect(self._emit_view_changed)

    # --- content ----------------------------------------------------------

    def set_pixmap(self, pixmap: QPixmap) -> None:
        self._item.setPixmap(pixmap)
        self.setSceneRect(QRectF(pixmap.rect()))

    def pixmap(self) -> QPixmap:
        return self._item.pixmap()

    # --- background -------------------------------------------------------

    def background(self) -> Background:
        return self._background

    def set_background(self, background: Background) -> None:
        self._background = background
        self.viewport().update()

    def drawBackground(self, painter, rect) -> None:
        if self._background is Background.CHECKER:
            painter.fillRect(rect, QBrush(checker_pixmap()))
        elif self._background is Background.WHITE:
            painter.fillRect(rect, QColor(255, 255, 255))
        else:
            painter.fillRect(rect, QColor(0, 0, 0))

    # --- zoom / pan / sync ------------------------------------------------

    def zoom(self, factor: float) -> None:
        new_scale = self.transform().m11() * factor
        if not MIN_SCALE <= new_scale <= MAX_SCALE:
            return
        self.scale(factor, factor)
        self._emit_view_changed()

    def fit(self) -> None:
        if not self._item.pixmap().isNull():
            self.fitInView(self._item, Qt.AspectRatioMode.KeepAspectRatio)
            self._emit_view_changed()

    def apply_view(self, transform: QTransform, h_scroll: int, v_scroll: int) -> None:
        """Adopt another view's viewport without re-emitting view_changed."""
        self._syncing = True
        try:
            self.setTransform(transform)
            self.horizontalScrollBar().setValue(h_scroll)
            self.verticalScrollBar().setValue(v_scroll)
        finally:
            self._syncing = False

    def _emit_view_changed(self) -> None:
        if not self._syncing:
            self.view_changed.emit()

    # --- events -----------------------------------------------------------

    def wheelEvent(self, event) -> None:
        delta = event.angleDelta().y()
        if delta:
            self.user_interacted.emit()
            self.zoom(ZOOM_STEP if delta > 0 else 1 / ZOOM_STEP)

    def mousePressEvent(self, event) -> None:
        self._press_pos = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._press_pos is not None:  # dragging = panning
            self.user_interacted.emit()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if (
            self._press_pos is not None
            and (event.position() - self._press_pos).manhattanLength() < 4
        ):
            self.clicked.emit()
        self._press_pos = None
        super().mouseReleaseEvent(event)


class ViewSynchronizer:
    """Keeps a group of ImageViews at the same zoom and scroll position."""

    def __init__(self):
        self._views: list[ImageView] = []

    def add(self, view: ImageView) -> None:
        self._views.append(view)
        view.view_changed.connect(lambda view=view: self.sync_from(view))

    def sync_from(self, source: ImageView) -> None:
        transform = source.transform()
        h_scroll = source.horizontalScrollBar().value()
        v_scroll = source.verticalScrollBar().value()
        for view in self._views:
            if view is not source:
                view.apply_view(transform, h_scroll, v_scroll)

    def fit_all(self) -> None:
        if self._views:
            self._views[0].fit()
            self.sync_from(self._views[0])
