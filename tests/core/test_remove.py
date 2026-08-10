import pytest

from kitta.core.models import PRESETS


@pytest.mark.inference
def test_remove_background_u2netp(sample_image):
    from kitta.core.remove import remove_background

    result = remove_background(sample_image, PRESETS["fast"])

    assert result.image.mode == "RGBA"
    assert result.image.size == sample_image.size
    assert result.mask.mode == "L"
    assert result.mask.size == sample_image.size
    assert result.elapsed > 0
    assert result.model_name == "u2netp"
    assert result.preset_name == "fast"


@pytest.mark.inference
def test_sessions_are_cached(sample_image):
    from kitta.core import remove

    remove.remove_background(sample_image, PRESETS["fast"])
    session = remove._sessions["u2netp"]
    remove.remove_background(sample_image, PRESETS["fast"])
    assert remove._sessions["u2netp"] is session
