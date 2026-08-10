import pytest
from PIL import Image

from kitta.core.remove import RemovalResult
from kitta.gui import workers as workers_mod
from kitta.gui.main_window import MainWindow, load_image


def fake_compare(image, presets, callbacks):
    results = []
    for index, preset in enumerate(presets):
        callbacks.on_start(index, preset)
        rgba = Image.new("RGBA", (8, 8), (0, 255, 0, 200))
        result = RemovalResult(
            image=rgba,
            mask=rgba.getchannel("A"),
            elapsed=0.01,
            model_name=preset.model.name,
            preset_name=preset.name,
        )
        results.append(result)
        callbacks.on_result(index, preset, result)
    return results


@pytest.fixture
def image_file(tmp_path):
    path = tmp_path / "photo.png"
    Image.new("RGB", (32, 32), "white").save(path)
    return path


def test_load_image(image_file):
    image = load_image(image_file)
    assert image.mode == "RGB"
    assert image.size == (32, 32)


def test_start_runs_worker_and_switches_view(monkeypatch, qtbot, image_file):
    monkeypatch.setattr(workers_mod, "compare", fake_compare)
    window = MainWindow()
    qtbot.addWidget(window)
    assert window._stack.currentWidget() is window.drop_view

    window.drop_view.start_requested.emit(str(image_file))

    assert window._stack.currentWidget() is window.compare_view
    worker = window._worker
    assert worker is not None
    qtbot.waitUntil(lambda: window._worker is None, timeout=5000)

    presets = window.drop_view.selected_presets()
    assert len(window.compare_view.cells) == len(presets)
    qtbot.waitUntil(lambda: window.compare_view.cells[0].result is not None, timeout=5000)
    assert window.compare_view.cells[0].result.preset_name == presets[0].name


def test_no_presets_selected_shows_warning(monkeypatch, qtbot, image_file):
    warnings = []
    from PySide6.QtWidgets import QMessageBox

    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))
    window = MainWindow()
    qtbot.addWidget(window)
    window.drop_view.set_selected_presets(())

    window.drop_view.start_requested.emit(str(image_file))

    assert warnings
    assert window._worker is None
    assert window._stack.currentWidget() is window.drop_view


def test_back_returns_to_drop_view(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window._stack.setCurrentWidget(window.compare_view)

    window.compare_view.back_requested.emit()

    assert window._stack.currentWidget() is window.drop_view


def test_settings_roundtrip(qtbot):
    from kitta.gui.compare_view import ViewMode
    from kitta.gui.image_view import Background

    first = MainWindow()
    qtbot.addWidget(first)
    first.drop_view.set_selected_presets({"anime"})
    first.compare_view.set_background(Background.BLACK)
    first.compare_view.set_view_mode(ViewMode.MASK)
    first.close()

    second = MainWindow()
    qtbot.addWidget(second)
    assert [preset.name for preset in second.drop_view.selected_presets()] == ["anime"]
    assert second.compare_view.background() is Background.BLACK
    assert second.compare_view.view_mode() is ViewMode.MASK


def test_all_failed_shows_dialog(monkeypatch, qtbot):
    from PySide6.QtWidgets import QMessageBox

    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: errors.append(args))
    window = MainWindow()
    qtbot.addWidget(window)

    window._on_compare_finished([None, None])

    assert errors


def test_partial_failure_shows_no_dialog(monkeypatch, qtbot):
    from PySide6.QtWidgets import QMessageBox

    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: errors.append(args))
    window = MainWindow()
    qtbot.addWidget(window)

    window._on_compare_finished([object(), None])

    assert not errors


def test_help_menu_about_and_licenses(monkeypatch, qtbot):
    import kitta

    window = MainWindow()
    qtbot.addWidget(window)

    from PySide6.QtWidgets import QDialog, QMessageBox

    abouts = []
    monkeypatch.setattr(QMessageBox, "about", lambda *args: abouts.append(args))
    window._show_about()
    assert abouts
    assert kitta.__version__ in abouts[0][2]

    dialogs = []
    monkeypatch.setattr(QDialog, "exec", lambda self: dialogs.append(self))
    window._show_licenses()
    assert dialogs


def test_drop_on_compare_view_previews_instead_of_starting(qtbot, image_file):
    window = MainWindow()
    qtbot.addWidget(window)
    window._stack.setCurrentWidget(window.compare_view)

    window.compare_view.image_dropped.emit(str(image_file))

    assert window._stack.currentWidget() is window.drop_view
    assert window.drop_view.selected_path() == str(image_file)
    assert window._worker is None
