"""Main window: switches between the drop screen and the compare screen."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QDialog,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
)

import kitta
from kitta.gui.compare_view import CompareView, ViewMode
from kitta.gui.drop_view import DropView
from kitta.gui.image_view import Background
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

        self.drop_view.start_requested.connect(self.start_compare)
        self.compare_view.image_dropped.connect(self._on_new_image_dropped)
        self.compare_view.back_requested.connect(self.show_drop_view)
        self.compare_view.cancel_requested.connect(self._cancel_compare)

        self._build_menus()

        self._settings = QSettings(
            QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Kitta", "Kitta"
        )
        self._restore_settings()

    def _build_menus(self) -> None:
        help_menu = self.menuBar().addMenu(self.tr("&Help"))
        self.about_action = help_menu.addAction(self.tr("&About Kitta"))
        self.about_action.triggered.connect(self._show_about)
        self.license_action = help_menu.addAction(self.tr("&Kitta License"))
        self.license_action.triggered.connect(self._show_license)
        self.licenses_action = help_menu.addAction(self.tr("Third-Party &Licenses"))
        self.licenses_action.triggered.connect(self._show_licenses)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            self.tr("About Kitta"),
            self.tr(
                "<h3>Kitta {0}</h3>"
                "<p>Compare AI background removal models side by side. "
                "Fully offline.</p>"
                "<p>Licensed under the GNU General Public License v3.0 or later.<br>"
                'See <a href="https://github.com/atsuoishimoto/kitta">'
                "github.com/atsuoishimoto/kitta</a>.</p>"
            ).format(kitta.__version__),
        )

    def _show_license(self) -> None:
        text = QTextBrowser()
        # the GPL text is pre-wrapped and indented: keep it as authored
        text.setLineWrapMode(QTextBrowser.LineWrapMode.NoWrap)
        text.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        text.setPlainText(kitta.license_text())
        self._show_text_dialog(self.tr("License"), text)

    def _show_licenses(self) -> None:
        text = QTextBrowser()
        text.setOpenExternalLinks(True)
        text.setMarkdown(kitta.notice_text())
        self._show_text_dialog(self.tr("Third-Party Licenses"), text)

    def _show_text_dialog(self, title: str, text: QTextBrowser) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(700, 500)
        layout = QVBoxLayout(dialog)
        layout.addWidget(text)
        dialog.exec()

    def show_drop_view(self) -> None:
        self._stack.setCurrentWidget(self.drop_view)

    def _on_new_image_dropped(self, path: str) -> None:
        """A new image dropped on the compare screen: preview it first."""
        self.show_drop_view()
        self.drop_view.set_image(path)

    def start_compare(self, path: str) -> None:
        if self._worker is not None and self._worker.isRunning():
            self.statusBar().showMessage(self.tr("A comparison is already running"), 3000)
            return
        presets = self.drop_view.selected_presets()
        if not presets:
            QMessageBox.warning(self, self.tr("Kitta"), self.tr("Select at least one model first."))
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
        worker.model_cancelled.connect(self.compare_view.on_model_cancelled)
        worker.compare_finished.connect(self._on_compare_finished)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

        self._stack.setCurrentWidget(self.compare_view)

    def _cancel_compare(self) -> None:
        if self._worker is not None:
            self._worker.cancel()

    def _on_compare_finished(self, results) -> None:
        self._worker = None
        self.compare_view.set_running(False)
        if results and all(result is None for result in results):
            QMessageBox.critical(
                self,
                self.tr("Kitta"),
                self.tr(
                    "No model produced a result. "
                    "Check the error messages in each cell "
                    "(a network connection is required to download models)."
                ),
            )

    # --- settings ---------------------------------------------------------

    def _restore_settings(self) -> None:
        geometry = self._settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        presets = self._settings.value("presets/selected")
        if presets is not None:
            names = [name for name in str(presets).split(",") if name]
            self.drop_view.set_selected_presets(names)
        background = self._settings.value("view/background")
        if background is not None:
            try:
                self.compare_view.set_background(Background(background))
            except ValueError:
                pass
        mode = self._settings.value("view/mode")
        if mode is not None:
            try:
                self.compare_view.set_view_mode(ViewMode(mode))
            except ValueError:
                pass

    def _save_settings(self) -> None:
        self._settings.setValue("window/geometry", self.saveGeometry())
        names = [preset.name for preset in self.drop_view.selected_presets()]
        self._settings.setValue("presets/selected", ",".join(names))
        self._settings.setValue("view/background", self.compare_view.background().value)
        self._settings.setValue("view/mode", self.compare_view.view_mode().value)

    def closeEvent(self, event) -> None:
        self._save_settings()
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(10000)
        super().closeEvent(event)
