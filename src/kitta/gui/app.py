"""GUI entry point (``kitta-gui``)."""

from __future__ import annotations

import sys


def main() -> int:
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
