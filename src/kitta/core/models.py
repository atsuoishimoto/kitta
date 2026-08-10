"""Model catalog and preset definitions.

This module is data only: the preset -> model mapping is provisional
(product plan §8) and will be swapped after model validation, so it must
stay free of logic that depends on specific models.

Checksums use the pooch-style ``"<algorithm>:<hexdigest>"`` format. The
current values are the MD5 hashes rembg itself verifies against, so files
downloaded by Kitta are accepted by rembg's own cache check as well.
"""

from __future__ import annotations

from dataclasses import dataclass, field

_REMBG_RELEASE = "https://github.com/danielgatis/rembg/releases/download/v0.0.0"


@dataclass(frozen=True)
class ModelSpec:
    """A single ONNX model as consumed by rembg."""

    name: str  # rembg model name (usable with rembg.new_session)
    display_name: str
    url: str
    filename: str  # filename rembg expects inside the model cache
    size: int  # download size in bytes (for progress display)
    checksum: str  # "<algorithm>:<hexdigest>"
    license_name: str
    license_url: str


@dataclass(frozen=True)
class AlphaMatting:
    """Alpha matting parameters (product plan §14/§15)."""

    enabled: bool = False
    foreground_threshold: int = 240
    background_threshold: int = 10
    erode_size: int = 10


@dataclass(frozen=True)
class Preset:
    """A named, user-facing configuration resolving to a model + parameters."""

    name: str  # identifier used by CLI/TOML (e.g. "quality")
    display_name: str  # user-facing label (e.g. "High Quality")
    model: ModelSpec
    alpha_matting: AlphaMatting = field(default_factory=AlphaMatting)
    output_format: str = "png"


_MODEL_LIST = [
    ModelSpec(
        name="u2netp",
        display_name="U²-Net (small)",
        url=f"{_REMBG_RELEASE}/u2netp.onnx",
        filename="u2netp.onnx",
        size=4_574_861,
        checksum="md5:8e83ca70e441ab06c318d82300c84806",
        license_name="Apache-2.0",
        license_url="https://github.com/xuebinqin/U-2-Net",
    ),
    ModelSpec(
        name="birefnet-general",
        display_name="BiRefNet General",
        url=f"{_REMBG_RELEASE}/BiRefNet-general-epoch_244.onnx",
        filename="birefnet-general.onnx",
        size=972_666_916,
        checksum="md5:7a35a0141cbbc80de11d9c9a28f52697",
        license_name="MIT",
        license_url="https://github.com/ZhengPeng7/BiRefNet",
    ),
    ModelSpec(
        name="birefnet-portrait",
        display_name="BiRefNet Portrait",
        url=f"{_REMBG_RELEASE}/BiRefNet-portrait-epoch_150.onnx",
        filename="birefnet-portrait.onnx",
        size=972_666_916,
        checksum="md5:c3a64a6abf20250d090cd055f12a3b67",
        license_name="MIT",
        license_url="https://github.com/ZhengPeng7/BiRefNet",
    ),
    ModelSpec(
        name="isnet-anime",
        display_name="ISNet Anime",
        url=f"{_REMBG_RELEASE}/isnet-anime.onnx",
        filename="isnet-anime.onnx",
        size=176_069_933,
        checksum="md5:6f184e756bb3bd901c8849220a83e38e",
        license_name="Apache-2.0",
        license_url="https://github.com/SkyTNT/anime-segmentation",
    ),
    ModelSpec(
        name="isnet-general-use",
        display_name="ISNet General",
        url=f"{_REMBG_RELEASE}/isnet-general-use.onnx",
        filename="isnet-general-use.onnx",
        size=178_648_008,
        checksum="md5:fc16ebd8b0c10d971d3513d564d01e29",
        license_name="Apache-2.0",
        license_url="https://github.com/xuebinqin/DIS",
    ),
]

MODELS: dict[str, ModelSpec] = {spec.name: spec for spec in _MODEL_LIST}

# Ordered fastest/lightest -> highest quality, then the specialized ones;
# this order is also the GUI checkbox order.
_PRESET_LIST = [
    Preset(name="fast", display_name="Fast", model=MODELS["u2netp"]),
    Preset(name="balanced", display_name="Balanced", model=MODELS["isnet-general-use"]),
    Preset(name="quality", display_name="High Quality", model=MODELS["birefnet-general"]),
    Preset(name="portrait", display_name="Portrait", model=MODELS["birefnet-portrait"]),
    Preset(name="anime", display_name="Anime", model=MODELS["isnet-anime"]),
]

PRESETS: dict[str, Preset] = {preset.name: preset for preset in _PRESET_LIST}

# Presets pre-selected on the GUI drop screen (product plan §10).
DEFAULT_PRESET_NAMES = ("fast", "balanced", "quality")


def get_model(name: str) -> ModelSpec:
    try:
        return MODELS[name]
    except KeyError:
        known = ", ".join(MODELS)
        raise ValueError(f"unknown model {name!r} (available: {known})") from None


def get_preset(name: str) -> Preset:
    try:
        return PRESETS[name]
    except KeyError:
        known = ", ".join(PRESETS)
        raise ValueError(f"unknown preset {name!r} (available: {known})") from None
