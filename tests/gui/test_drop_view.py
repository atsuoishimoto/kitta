from kitta.core.models import DEFAULT_PRESET_NAMES, PRESETS
from kitta.gui.drop_view import DropView, is_supported_image


def test_default_preset_selection(qtbot):
    view = DropView()
    qtbot.addWidget(view)
    selected = {preset.name for preset in view.selected_presets()}
    assert selected == set(DEFAULT_PRESET_NAMES)


def test_set_selected_presets(qtbot):
    view = DropView()
    qtbot.addWidget(view)
    view.set_selected_presets({"anime"})
    assert [preset.name for preset in view.selected_presets()] == ["anime"]


def test_all_presets_offered(qtbot):
    view = DropView()
    qtbot.addWidget(view)
    view.set_selected_presets(PRESETS.keys())
    assert [preset.name for preset in view.selected_presets()] == list(PRESETS)


def test_is_supported_image():
    assert is_supported_image("photo.JPG")
    assert is_supported_image("/tmp/x/photo.webp")
    assert not is_supported_image("notes.txt")
    assert not is_supported_image("archive.zip")
