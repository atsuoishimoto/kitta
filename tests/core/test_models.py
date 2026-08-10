import hashlib

import pytest

from kitta.core.models import (
    DEFAULT_PRESET_NAMES,
    MODELS,
    PRESETS,
    get_model,
    get_preset,
)


def test_catalog_keys_match_spec_names():
    assert all(key == spec.name for key, spec in MODELS.items())
    assert all(key == preset.name for key, preset in PRESETS.items())


def test_checksums_are_wellformed():
    for spec in MODELS.values():
        algorithm, sep, hexdigest = spec.checksum.partition(":")
        assert sep, spec.name
        assert algorithm in hashlib.algorithms_available, spec.name
        assert len(hexdigest) == hashlib.new(algorithm).digest_size * 2, spec.name


def test_model_urls_and_sizes():
    for spec in MODELS.values():
        assert spec.url.startswith("https://"), spec.name
        assert spec.size > 0, spec.name
        assert spec.filename.endswith(".onnx"), spec.name


def test_presets_reference_cataloged_models():
    for preset in PRESETS.values():
        assert preset.model is MODELS[preset.model.name]


def test_default_presets_exist():
    assert set(DEFAULT_PRESET_NAMES) <= set(PRESETS)


def test_get_model_and_preset():
    assert get_model("u2netp") is MODELS["u2netp"]
    assert get_preset("fast") is PRESETS["fast"]
    with pytest.raises(ValueError, match="unknown model"):
        get_model("nope")
    with pytest.raises(ValueError, match="unknown preset"):
        get_preset("nope")
