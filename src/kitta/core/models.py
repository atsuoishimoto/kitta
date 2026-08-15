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


# Every local ONNX model of the bundled rembg (the GUI checkbox order).
# Excluded rembg sessions: sam (needs prompt input), *_custom (need a
# user-supplied model file) and withoutbg (cloud API, not offline).
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
        name="u2net",
        display_name="U²-Net",
        url=f"{_REMBG_RELEASE}/u2net.onnx",
        filename="u2net.onnx",
        size=175_997_641,
        checksum="md5:60024c5c889badc19c04ad937298a77b",
        license_name="Apache-2.0",
        license_url="https://github.com/xuebinqin/U-2-Net",
    ),
    ModelSpec(
        name="u2net_human_seg",
        display_name="U²-Net Human",
        url=f"{_REMBG_RELEASE}/u2net_human_seg.onnx",
        filename="u2net_human_seg.onnx",
        size=175_997_641,
        checksum="md5:c09ddc2e0104f800e3e1bb4652583d1f",
        license_name="Apache-2.0",
        license_url="https://github.com/xuebinqin/U-2-Net",
    ),
    ModelSpec(
        name="u2net_cloth_seg",
        display_name="U²-Net Cloth",
        url=f"{_REMBG_RELEASE}/u2net_cloth_seg.onnx",
        filename="u2net_cloth_seg.onnx",
        size=176_194_565,
        checksum="md5:2434d1f3cb744e0e49386c906e5a08bb",
        license_name="MIT",
        license_url="https://github.com/levindabhi/cloth-segmentation",
    ),
    ModelSpec(
        name="silueta",
        display_name="Silueta",
        url=f"{_REMBG_RELEASE}/silueta.onnx",
        filename="silueta.onnx",
        size=44_173_029,
        checksum="md5:55e59e0d8062d2f5d013f4725ee84782",
        license_name="Apache-2.0",
        license_url="https://github.com/xuebinqin/U-2-Net",
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
        name="birefnet-general-lite",
        display_name="BiRefNet Lite",
        url=f"{_REMBG_RELEASE}/BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx",
        filename="birefnet-general-lite.onnx",
        size=224_005_088,
        checksum="md5:4fab47adc4ff364be1713e97b7e66334",
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
        name="birefnet-dis",
        display_name="BiRefNet DIS",
        url=f"{_REMBG_RELEASE}/BiRefNet-DIS-epoch_590.onnx",
        filename="birefnet-dis.onnx",
        size=972_666_916,
        checksum="md5:2d4d44102b446f33a4ebb2e56c051f2b",
        license_name="MIT",
        license_url="https://github.com/ZhengPeng7/BiRefNet",
    ),
    ModelSpec(
        name="birefnet-hrsod",
        display_name="BiRefNet HRSOD",
        url=f"{_REMBG_RELEASE}/BiRefNet-HRSOD_DHU-epoch_115.onnx",
        filename="birefnet-hrsod.onnx",
        size=972_666_916,
        checksum="md5:c017ade5de8a50ff0fd74d790d268dda",
        license_name="MIT",
        license_url="https://github.com/ZhengPeng7/BiRefNet",
    ),
    ModelSpec(
        name="birefnet-cod",
        display_name="BiRefNet COD",
        url=f"{_REMBG_RELEASE}/BiRefNet-COD-epoch_125.onnx",
        filename="birefnet-cod.onnx",
        size=972_666_916,
        checksum="md5:f6d0d21ca89d287f17e7afe9f5fd3b45",
        license_name="MIT",
        license_url="https://github.com/ZhengPeng7/BiRefNet",
    ),
    ModelSpec(
        name="birefnet-massive",
        display_name="BiRefNet Massive",
        url=f"{_REMBG_RELEASE}/BiRefNet-massive-TR_DIS5K_TR_TEs-epoch_420.onnx",
        filename="birefnet-massive.onnx",
        size=972_666_916,
        checksum="md5:33e726a2136a3d59eb0fdf613e31e3e9",
        license_name="MIT",
        license_url="https://github.com/ZhengPeng7/BiRefNet",
    ),
    ModelSpec(
        name="bria-rmbg",
        display_name="BRIA RMBG 2.0",
        url=f"{_REMBG_RELEASE}/bria-rmbg-2.0.onnx",
        filename="bria-rmbg.onnx",
        size=1_024_331_469,
        checksum="sha256:5b486f08200f513f460da46dd701db5fbb47d79b4be4b708a19444bcd4e79958",
        license_name="BRIA RMBG-2.0 (non-commercial)",
        license_url="https://huggingface.co/briaai/RMBG-2.0",
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

# One direct preset per model (GUI model checkboxes, CLI --model).
MODEL_PRESETS: dict[str, Preset] = {
    spec.name: Preset(name=spec.name, display_name=spec.display_name, model=spec)
    for spec in _MODEL_LIST
}

# Models pre-selected on the GUI drop screen (the DEFAULT_PRESET_NAMES models).
DEFAULT_MODEL_NAMES = tuple(PRESETS[name].model.name for name in DEFAULT_PRESET_NAMES)


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
