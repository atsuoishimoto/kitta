"""GUI entry point (``kitta-gui``)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _configure_platform(environ=os.environ, wslg_dir=Path("/mnt/wslg")) -> None:
    """Prefer XWayland under WSLg.

    WSLg draws no window frame for Wayland dialog surfaces (while telling
    Qt that the compositor decorates, so Qt draws no title bar either);
    X11 windows are decorated normally.
    """
    if sys.platform == "linux" and "QT_QPA_PLATFORM" not in environ and wslg_dir.exists():
        environ["QT_QPA_PLATFORM"] = "xcb"


def main() -> int:
    _configure_platform()
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("Kitta")
    app.setOrganizationName("Kitta")

    from kitta.gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
