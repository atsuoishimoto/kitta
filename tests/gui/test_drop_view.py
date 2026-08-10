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


def test_only_drop_zone_is_click_target(view):
    from PySide6.QtCore import Qt

    assert view._drop_label.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert view.cursor().shape() == Qt.CursorShape.ArrowCursor


def test_drop_zone_click_opens_file_dialog(view, image_file, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")), raising=False
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(image_file), ""))
    )

    view._drop_label.clicked.emit()

    assert view.selected_path() == str(image_file)


def test_preview_area_image_rect_and_click(qtbot):
    from PySide6.QtCore import QPointF, QSize
    from PySide6.QtGui import QPixmap

    from kitta.gui.drop_view import PreviewArea

    area = PreviewArea()
    qtbot.addWidget(area)
    area.resize(400, 300)
    pixmap = QPixmap(100, 300)  # tall: fits height, leaves side margins
    pixmap.fill()
    area.set_pixmap(pixmap)

    rect = area.image_rect()
    assert rect.size() == QSize(100, 300)
    assert rect.center() == area.rect().center()

    clicks = []
    area.clicked.connect(lambda: clicks.append(1))

    class FakeMouse:
        def __init__(self, x, y):
            self._pos = QPointF(x, y)

        def position(self):
            return self._pos

    area.mousePressEvent(FakeMouse(10, 150))  # outside the image
    assert clicks == []
    area.mousePressEvent(FakeMouse(*_center(rect)))  # on the image
    assert clicks == [1]


def test_preview_area_hover_only_over_image(qtbot):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QPixmap

    from kitta.gui.drop_view import PreviewArea

    area = PreviewArea()
    qtbot.addWidget(area)
    area.resize(400, 300)
    pixmap = QPixmap(100, 300)
    pixmap.fill()
    area.set_pixmap(pixmap)

    class FakeMouse:
        def __init__(self, x, y):
            self._pos = QPointF(x, y)

        def position(self):
            return self._pos

    area.mouseMoveEvent(FakeMouse(*_center(area.image_rect())))
    assert area._hover
    assert area.cursor().shape() == Qt.CursorShape.PointingHandCursor

    area.mouseMoveEvent(FakeMouse(10, 150))
    assert not area._hover
    assert area.cursor().shape() == Qt.CursorShape.ArrowCursor


def _center(rect):
    return rect.center().x(), rect.center().y()


def test_text_url_is_recognized():
    from PySide6.QtCore import QMimeData

    from kitta.gui.drop_view import remote_image_url

    mime = QMimeData()
    mime.setText("https://example.com/a.jpg")
    assert remote_image_url(mime).toString() == "https://example.com/a.jpg"

    mime = QMimeData()
    mime.setText("just some text")
    assert remote_image_url(mime) is None


def test_paste_image_from_clipboard(view, tmp_path, monkeypatch, qapp):
    from PySide6.QtGui import QImage

    from kitta.core import paths

    monkeypatch.setattr(paths, "cache_dir", lambda: tmp_path)
    image = QImage(24, 16, QImage.Format_RGB32)
    image.fill(0xFFE0B040)
    qapp.clipboard().setImage(image)

    view.paste_from_clipboard()

    assert view.selected_path() is not None
    assert Image.open(view.selected_path()).size == (24, 16)


def test_paste_button_pastes(view, tmp_path, monkeypatch, qapp):
    from PySide6.QtGui import QImage

    from kitta.core import paths

    monkeypatch.setattr(paths, "cache_dir", lambda: tmp_path)
    image = QImage(10, 10, QImage.Format_RGB32)
    image.fill(0xFF3060A0)
    qapp.clipboard().setImage(image)

    view._paste_button.click()

    assert view.selected_path() is not None


def test_paste_without_image_shows_info(view, monkeypatch, qapp):
    infos = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: infos.append(args))
    qapp.clipboard().clear()

    view.paste_from_clipboard()

    assert infos
    assert view.selected_path() is None


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


class FakeDropEvent:
    def __init__(self, mime):
        self._mime = mime
        self.accepted = False

    def mimeData(self):
        return self._mime

    def acceptProposedAction(self):
        self.accepted = True


def make_image_mime():
    from PySide6.QtCore import QMimeData
    from PySide6.QtGui import QImage

    image = QImage(16, 12, QImage.Format_RGB32)
    image.fill(0xFF3060A0)
    mime = QMimeData()
    mime.setImageData(image)
    return mime


def make_file_mime(path):
    from PySide6.QtCore import QMimeData, QUrl

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    return mime


def test_accepts_drop(qtbot, image_file):
    from kitta.gui.drop_view import accepts_drop

    assert accepts_drop(FakeDropEvent(make_file_mime(image_file)))
    assert accepts_drop(FakeDropEvent(make_image_mime()))
    from PySide6.QtCore import QMimeData

    empty = QMimeData()
    empty.setText("hello")
    assert not accepts_drop(FakeDropEvent(empty))


def test_extract_prefers_local_file(qtbot, image_file):
    from kitta.gui.drop_view import extract_dropped_image_path

    mime = make_file_mime(image_file)
    mime.setImageData(make_image_mime().imageData())
    assert extract_dropped_image_path(FakeDropEvent(mime)) == str(image_file)


def test_image_data_drop_is_materialized(qtbot, tmp_path, monkeypatch):
    from kitta.core import paths
    from kitta.gui.drop_view import extract_dropped_image_path

    monkeypatch.setattr(paths, "cache_dir", lambda: tmp_path)

    path = extract_dropped_image_path(FakeDropEvent(make_image_mime()))

    assert path is not None
    assert path.startswith(str(tmp_path / "dropped"))
    assert Image.open(path).size == (16, 12)

    # a second drop in the same second must not overwrite the first
    other = extract_dropped_image_path(FakeDropEvent(make_image_mime()))
    assert other != path


def test_drop_event_with_image_data_shows_preview(view, tmp_path, monkeypatch):
    from kitta.core import paths

    monkeypatch.setattr(paths, "cache_dir", lambda: tmp_path)
    event = FakeDropEvent(make_image_mime())

    view.dropEvent(event)

    assert event.accepted
    assert view.selected_path() is not None
    assert view._center_stack.currentIndex() == 1


def make_remote_mime(url="https://example.com/photos/Cat_poster_1.jpg?x=1"):
    from PySide6.QtCore import QMimeData, QUrl

    mime = QMimeData()
    mime.setUrls([QUrl(url)])
    return mime


def png_bytes():
    import io

    buffer = io.BytesIO()
    Image.new("RGB", (20, 10), "green").save(buffer, format="PNG")
    return buffer.getvalue()


class FakeResponse:
    def __init__(self, body):
        self._body = body

    def read(self, size=-1):
        return self._body[:size] if size >= 0 else self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_accepts_drop_with_remote_url(qtbot):
    from kitta.gui.drop_view import accepts_drop

    assert accepts_drop(FakeDropEvent(make_remote_mime()))


def test_remote_url_drop_downloads_image(qtbot, tmp_path, monkeypatch):
    import urllib.request

    from kitta.core import paths
    from kitta.gui.drop_view import extract_dropped_image_path

    monkeypatch.setattr(paths, "cache_dir", lambda: tmp_path)
    requests = []

    def fake_urlopen(request, timeout=None):
        requests.append(request.full_url)
        return FakeResponse(png_bytes())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    path = extract_dropped_image_path(FakeDropEvent(make_remote_mime()))

    assert requests == ["https://example.com/photos/Cat_poster_1.jpg?x=1"]
    assert path is not None
    assert path.endswith("Cat_poster_1.png")
    assert Image.open(path).size == (20, 10)


def test_remote_url_with_non_ascii_path(qtbot, tmp_path, monkeypatch):
    import urllib.request

    from kitta.core import paths
    from kitta.gui.drop_view import extract_dropped_image_path

    monkeypatch.setattr(paths, "cache_dir", lambda: tmp_path)
    requests = []

    def fake_urlopen(request, timeout=None):
        requests.append(request.full_url)
        return FakeResponse(png_bytes())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    path = extract_dropped_image_path(
        FakeDropEvent(make_remote_mime("https://example.com/画像/猫の写真.jpg"))
    )

    assert path is not None
    assert len(requests) == 1
    assert requests[0].isascii()  # percent-encoded for urllib
    assert "%E7%8C%AB" in requests[0]  # 猫


def test_remote_url_download_failure(qtbot, tmp_path, monkeypatch):
    import urllib.error
    import urllib.request

    from kitta.core import paths
    from kitta.gui.drop_view import extract_dropped_image_path

    monkeypatch.setattr(paths, "cache_dir", lambda: tmp_path)

    def fake_urlopen(request, timeout=None):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    assert extract_dropped_image_path(FakeDropEvent(make_remote_mime())) is None


def test_remote_url_non_image_content(qtbot, tmp_path, monkeypatch):
    import urllib.request

    from kitta.core import paths
    from kitta.gui.drop_view import extract_dropped_image_path

    monkeypatch.setattr(paths, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda request, timeout=None: FakeResponse(b"<html>nope</html>")
    )

    assert extract_dropped_image_path(FakeDropEvent(make_remote_mime())) is None


def test_drop_event_shows_error_when_download_fails(view, tmp_path, monkeypatch):
    import urllib.error
    import urllib.request

    from kitta.core import paths

    monkeypatch.setattr(paths, "cache_dir", lambda: tmp_path)

    def fake_urlopen(request, timeout=None):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: errors.append(args))
    event = FakeDropEvent(make_remote_mime())

    view.dropEvent(event)

    assert event.accepted
    assert errors
    assert view.selected_path() is None
