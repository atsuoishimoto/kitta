import pytest

from kitta.core.models import PRESETS, AlphaMatting, Preset, get_model
from kitta.core.presets import (
    PresetError,
    dumps_preset,
    load_preset,
    loads_preset,
    save_preset,
)


def make_preset(**kwargs) -> Preset:
    defaults = dict(
        name="my-preset",
        display_name="my-preset",
        model=get_model("birefnet-general"),
        alpha_matting=AlphaMatting(
            enabled=True, foreground_threshold=230, background_threshold=20, erode_size=15
        ),
        output_format="png",
    )
    defaults.update(kwargs)
    return Preset(**defaults)


def test_round_trip():
    preset = make_preset()
    text = dumps_preset(preset)
    loaded = loads_preset(text, name="my-preset")
    assert loaded == preset


def test_round_trip_via_file(tmp_path):
    preset = make_preset()
    path = tmp_path / "my-preset.toml"
    save_preset(preset, path)
    assert load_preset(path) == preset


def test_builtin_presets_round_trip():
    for preset in PRESETS.values():
        loaded = loads_preset(dumps_preset(preset), name=preset.name)
        assert loaded.model is preset.model
        assert loaded.alpha_matting == preset.alpha_matting
        assert loaded.output_format == preset.output_format


def test_minimal_toml_uses_defaults():
    preset = loads_preset('model = "u2netp"', name="minimal")
    assert preset.model.name == "u2netp"
    assert preset.alpha_matting == AlphaMatting()
    assert preset.output_format == "png"


def test_invalid_toml():
    with pytest.raises(PresetError, match="invalid TOML"):
        loads_preset("model = ", name="broken")


def test_unknown_model():
    with pytest.raises(PresetError, match="unknown model"):
        loads_preset('model = "nope"', name="p")


def test_missing_model():
    with pytest.raises(PresetError, match="'model' must be a string"):
        loads_preset("", name="p")


@pytest.mark.parametrize(
    "snippet,match",
    [
        ('model = "u2netp"\n[alpha_matting]\nenabled = 1', "must be a boolean"),
        ('model = "u2netp"\n[alpha_matting]\nforeground_threshold = "hi"', "must be an integer"),
        ('model = "u2netp"\n[alpha_matting]\nbackground_threshold = 999', "must be between"),
        ('model = "u2netp"\n[output]\nformat = "jpeg"', "unsupported output format"),
        ('model = "u2netp"\nalpha_matting = 3', r"\[alpha_matting\] must be a table"),
    ],
)
def test_validation_errors(snippet, match):
    with pytest.raises(PresetError, match=match):
        loads_preset(snippet, name="p")


def test_load_preset_missing_file(tmp_path):
    with pytest.raises(PresetError, match="cannot read preset file"):
        load_preset(tmp_path / "nope.toml")
