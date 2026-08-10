import io

import pytest
from PIL import Image

from kitta.gui.images import load_qimage, pil_to_qimage, qimage_from_data


@pytest.fixture
def sample_image():
    return Image.new("RGBA", (6, 4), (10, 20, 30, 255))


def test_pil_to_qimage(sample_image):
    qimage = pil_to_qimage(sample_image)
    assert (qimage.width(), qimage.height()) == (6, 4)
    assert qimage.pixelColor(0, 0).getRgb() == (10, 20, 30, 255)


@pytest.mark.parametrize("suffix", [".png", ".avif"])
def test_load_qimage(tmp_path, sample_image, suffix):
    # .avif exercises the Pillow fallback: Qt cannot decode it
    path = tmp_path / f"photo{suffix}"
    sample_image.convert("RGB").save(path)
    qimage = load_qimage(path)
    assert (qimage.width(), qimage.height()) == (6, 4)


@pytest.mark.parametrize("format_name", ["PNG", "AVIF"])
def test_qimage_from_data(sample_image, format_name):
    buffer = io.BytesIO()
    sample_image.convert("RGB").save(buffer, format=format_name)
    qimage = qimage_from_data(buffer.getvalue())
    assert (qimage.width(), qimage.height()) == (6, 4)


def test_undecodable_input_yields_null_image(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("not an image")
    assert load_qimage(path).isNull()
    assert load_qimage(tmp_path / "missing.png").isNull()
    assert qimage_from_data(b"not an image").isNull()
