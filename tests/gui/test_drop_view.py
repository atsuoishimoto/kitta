import pytest
from PIL import Image
from PySide6.QtWidgets import QMessageBox

from kitta.core.models import DEFAULT_PRESET_NAMES, PRESETS
from kitta.gui.drop_view import DropView, is_supported_image


@pytest.fixture
def view(qtbot):
    view = DropView()
    qtbot.addWidget(view)
    return view


@pytest.fixture
def image_file(tmp_path):
    path = tmp_path / "photo.png"
    Image.new("RGB", (32, 24), "white").save(path)
    return path


def test_default_preset_selection(view):
    selected = {preset.name for preset in view.selected_presets()}
    assert selected == set(DEFAULT_PRESET_NAMES)


def test_set_selected_presets(view):
    view.set_selected_presets({"anime"})
    assert [preset.name for preset in view.selected_presets()] == ["anime"]


def test_all_presets_offered(view):
    view.set_selected_presets(PRESETS.keys())
    assert [preset.name for preset in view.selected_presets()] == list(PRESETS)


def test_initially_no_image_selected(view):
    assert view.selected_path() is None
    assert view._center_stack.currentIndex() == 0  # drop label page


def test_set_image_shows_preview_and_start(view, image_file):
    assert view.set_image(str(image_file))

    assert view.selected_path() == str(image_file)
    assert view._center_stack.currentIndex() == 1  # preview page
    assert "photo.png" in view._filename_label.text()
    assert "32×24" in view._filename_label.text()


def test_set_image_unreadable_keeps_state(view, tmp_path, monkeypatch):
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: errors.append(args))
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not an image")

    assert not view.set_image(str(broken))

    assert errors
    assert view.selected_path() is None
    assert view._center_stack.currentIndex() == 0


def test_start_emits_only_with_image(view, image_file, qtbot):
    received = []
    view.start_requested.connect(received.append)

    view._start_button.click()
    assert received == []

    view.set_image(str(image_file))
    view._start_button.click()
    assert received == [str(image_file)]


def test_is_supported_image():
    assert is_supported_image("photo.JPG")
    assert is_supported_image("/tmp/x/photo.webp")
    assert not is_supported_image("notes.txt")
    assert not is_supported_image("archive.zip")
