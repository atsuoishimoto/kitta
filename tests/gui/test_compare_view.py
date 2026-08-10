import pytest
from PIL import Image
from PySide6.QtWidgets import QFileDialog

from kitta.core.models import PRESETS
from kitta.core.remove import RemovalResult
from kitta.gui.compare_view import CompareView, ViewMode, pil_to_qimage
from kitta.gui.image_view import Background

PRESET_LIST = [PRESETS["fast"], PRESETS["balanced"]]


def fake_result(preset) -> RemovalResult:
    rgba = Image.new("RGBA", (32, 32), (255, 0, 0, 128))
    return RemovalResult(
        image=rgba,
        mask=rgba.getchannel("A"),
        elapsed=1.23,
        model_name=preset.model.name,
        preset_name=preset.name,
    )


@pytest.fixture
def view(qtbot, tmp_path, sample_image):
    view = CompareView()
    qtbot.addWidget(view)
    view.begin(tmp_path / "photo.jpg", sample_image, PRESET_LIST)
    return view


def test_pil_to_qimage(sample_image):
    qimage = pil_to_qimage(sample_image)
    assert (qimage.width(), qimage.height()) == sample_image.size


def test_clickables_use_pointing_hand_cursor(view):
    from PySide6.QtCore import Qt

    hand = Qt.CursorShape.PointingHandCursor
    assert view._back_button.cursor().shape() == hand
    assert view._save_png_button.cursor().shape() == hand
    assert all(b.cursor().shape() == hand for b in view._mode_buttons.values())
    assert all(b.cursor().shape() == hand for b in view._background_buttons.values())
    for cell in view.cells:
        assert cell.cursor().shape() == hand
        # the image area keeps its pan (open hand) cursor
        assert cell.view.viewport().cursor().shape() == Qt.CursorShape.OpenHandCursor
    # the original cell is not clickable
    assert view.original_cell.cursor().shape() != hand


def test_begin_creates_cells_showing_original(view):
    assert len(view.cells) == 2
    assert view.view_mode() is ViewMode.RESULT
    for cell in view.cells:
        assert cell.displayed_mode() is ViewMode.ORIGINAL  # no result yet
    assert view.original_cell is not None
    assert "Original" in view.original_cell.title_label.text()
    assert view.original_cell.displayed_mode() is ViewMode.ORIGINAL
    assert view._grid.itemAtPosition(0, 0).widget() is view.original_cell


def test_no_original_mode_button(view):
    assert set(view._mode_buttons) == {ViewMode.MASK, ViewMode.RESULT}


def test_result_display_and_mode_switch(view):
    view.on_result(0, PRESET_LIST[0], fake_result(PRESET_LIST[0]))

    assert view.cells[0].displayed_mode() is ViewMode.RESULT
    assert view.cells[1].displayed_mode() is ViewMode.ORIGINAL
    assert "1.23" in view.cells[0].status_label.text()

    view.set_view_mode(ViewMode.MASK)
    assert view.cells[0].displayed_mode() is ViewMode.MASK
    assert view.cells[1].displayed_mode() is ViewMode.ORIGINAL
    # the original cell is unaffected by the view mode
    assert view.original_cell.displayed_mode() is ViewMode.ORIGINAL


def test_original_cell_is_not_selectable(view):
    view._on_cell_clicked(view.original_cell)
    assert view.selected_result() is None
    assert not view.original_cell.selected
    assert not view._save_png_button.isEnabled()


def test_original_cell_is_synchronized(view, qtbot):
    qtbot.wait(10)  # let the fit_all queued by begin() fire first
    view.original_cell.view.zoom(2.0)
    assert view.cells[0].view.transform() == view.original_cell.view.transform()


def test_late_result_respects_current_mode(view):
    view.set_view_mode(ViewMode.MASK)
    view.on_result(1, PRESET_LIST[1], fake_result(PRESET_LIST[1]))
    assert view.cells[1].displayed_mode() is ViewMode.MASK


def test_background_switch_applies_to_all_cells(view):
    view.set_background(Background.BLACK)
    assert all(cell.view.background() is Background.BLACK for cell in view.cells)
    assert view.original_cell.view.background() is Background.BLACK


def test_new_cells_inherit_background(qtbot, tmp_path, sample_image):
    view = CompareView()
    qtbot.addWidget(view)
    view.set_background(Background.WHITE)
    view.begin(tmp_path / "photo.jpg", sample_image, PRESET_LIST)
    assert all(cell.view.background() is Background.WHITE for cell in view.cells)


def test_selection_requires_result(view):
    view._on_cell_clicked(view.cells[0])
    assert view.selected_result() is None
    assert not view._save_png_button.isEnabled()


def test_selection_is_exclusive(view):
    for index, preset in enumerate(PRESET_LIST):
        view.on_result(index, preset, fake_result(preset))

    view._on_cell_clicked(view.cells[0])
    assert view.cells[0].selected
    assert "★" in view.cells[0].title_label.text()
    assert view._save_png_button.isEnabled()
    assert view._save_mask_button.isEnabled()

    view._on_cell_clicked(view.cells[1])
    assert not view.cells[0].selected
    assert view.cells[1].selected
    assert view.selected_result().preset_name == "balanced"


def test_save_png_and_mask(monkeypatch, view, tmp_path):
    view.on_result(0, PRESET_LIST[0], fake_result(PRESET_LIST[0]))
    view._on_cell_clicked(view.cells[0])

    suggested = []

    def fake_dialog(parent, caption, default, filter):
        suggested.append(default)
        name = "cutout.png" if "cutout" in default else "mask.png"
        return str(tmp_path / name), filter

    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(fake_dialog))

    view.save_png()
    saved = Image.open(tmp_path / "cutout.png")
    assert saved.mode == "RGBA"
    assert suggested[0].endswith("photo-cutout.png")

    view.save_mask()
    mask = Image.open(tmp_path / "mask.png")
    assert mask.mode == "L"
    assert suggested[1].endswith("photo-mask.png")


def test_error_state(view):
    view.on_model_failed(0, PRESET_LIST[0], "download failed")
    assert "download failed" in view.cells[0].status_label.text()
    assert not view.cells[0].progress_bar.isVisibleTo(view)


def test_download_progress(view):
    view.on_download_progress(0, PRESET_LIST[0], 500, 1000)
    cell = view.cells[0]
    assert cell.progress_bar.isVisibleTo(view)
    assert cell.progress_bar.value() == 500
    assert "Downloading" in cell.status_label.text()


def test_selection_keeps_cell_widths_equal(qtbot, tmp_path):
    """Regression: selecting a cell (style sheet change) must not shrink it."""
    view = CompareView()
    qtbot.addWidget(view)
    view.resize(1100, 700)
    view.show()
    image = Image.new("RGB", (1080, 1440), "blue")
    presets = [PRESETS["fast"], PRESETS["quality"], PRESETS["balanced"]]
    view.begin(tmp_path / "photo.jpg", image, presets)
    for index, preset in enumerate(presets):
        big = Image.new("RGBA", (1080, 1440), (200, 150, 100, 255))
        view.on_result(
            index,
            preset,
            RemovalResult(
                image=big,
                mask=big.getchannel("A"),
                elapsed=0.5,
                model_name=preset.model.name,
                preset_name=preset.name,
            ),
        )
    qtbot.wait(10)
    before = [cell.width() for cell in view.cells]

    view._on_cell_clicked(view.cells[0])
    qtbot.wait(10)

    after = [cell.width() for cell in view.cells]
    assert max(after) - min(after) <= 2
    assert all(abs(a - b) <= 2 for a, b in zip(after, before, strict=True))


def test_zoom_is_synchronized_across_cells(view, qtbot):
    qtbot.wait(10)  # let the fit_all queued by begin() fire first
    before = view.cells[0].view.transform().m11()

    view.cells[0].view.zoom(2.0)

    assert view.cells[0].view.transform().m11() == pytest.approx(before * 2)
    assert view.cells[1].view.transform() == view.cells[0].view.transform()
