import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")


@pytest.fixture(autouse=True)
def isolated_qsettings(tmp_path):
    """Keep QSettings (ini format) inside the test's tmp dir."""
    from PySide6.QtCore import QSettings

    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings")
    )
