import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def sample_image() -> Image.Image:
    """A small synthetic photo-ish image: red square on white background."""
    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([16, 16, 47, 47], fill="red")
    return image
