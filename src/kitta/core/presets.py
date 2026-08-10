"""Reading, writing and validating preset TOML files (product plan §15).

Built-in presets (models.PRESETS) and user preset files both resolve to
the same ``Preset`` type, so the rest of the code never needs to care
where a preset came from.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import tomli_w

from kitta.core.models import AlphaMatting, Preset, get_model

SUPPORTED_OUTPUT_FORMATS = ("png",)


class PresetError(Exception):
    """A preset file is malformed or references unknown values."""


def dumps_preset(preset: Preset) -> str:
    document = {
        "model": preset.model.name,
        "alpha_matting": {
            "enabled": preset.alpha_matting.enabled,
            "foreground_threshold": preset.alpha_matting.foreground_threshold,
            "background_threshold": preset.alpha_matting.background_threshold,
            "erode_size": preset.alpha_matting.erode_size,
        },
        "output": {
            "format": preset.output_format,
        },
    }
    return tomli_w.dumps(document)


def save_preset(preset: Preset, path: Path | str) -> None:
    Path(path).write_text(dumps_preset(preset), encoding="utf-8")


def loads_preset(text: str, name: str) -> Preset:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise PresetError(f"invalid TOML in preset {name!r}: {exc}") from exc

    model_name = data.get("model")
    if not isinstance(model_name, str):
        raise PresetError(f"preset {name!r}: 'model' must be a string")
    try:
        model = get_model(model_name)
    except ValueError as exc:
        raise PresetError(f"preset {name!r}: {exc}") from exc

    defaults = AlphaMatting()
    matting_data = _get_table(data, "alpha_matting", name)
    alpha_matting = AlphaMatting(
        enabled=_get_bool(matting_data, "enabled", defaults.enabled, name),
        foreground_threshold=_get_int(
            matting_data, "foreground_threshold", defaults.foreground_threshold, name, 0, 255
        ),
        background_threshold=_get_int(
            matting_data, "background_threshold", defaults.background_threshold, name, 0, 255
        ),
        erode_size=_get_int(matting_data, "erode_size", defaults.erode_size, name, 0, 1000),
    )

    output_data = _get_table(data, "output", name)
    output_format = output_data.get("format", "png")
    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise PresetError(
            f"preset {name!r}: unsupported output format {output_format!r} "
            f"(supported: {', '.join(SUPPORTED_OUTPUT_FORMATS)})"
        )

    return Preset(
        name=name,
        display_name=name,
        model=model,
        alpha_matting=alpha_matting,
        output_format=output_format,
    )


def load_preset(path: Path | str) -> Preset:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PresetError(f"cannot read preset file {path}: {exc}") from exc
    return loads_preset(text, name=path.stem)


def _get_table(data: dict, key: str, name: str) -> dict:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise PresetError(f"preset {name!r}: [{key}] must be a table")
    return value


def _get_bool(table: dict, key: str, default: bool, name: str) -> bool:
    value = table.get(key, default)
    if not isinstance(value, bool):
        raise PresetError(f"preset {name!r}: {key!r} must be a boolean")
    return value


def _get_int(table: dict, key: str, default: int, name: str, lo: int, hi: int) -> int:
    value = table.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise PresetError(f"preset {name!r}: {key!r} must be an integer")
    if not lo <= value <= hi:
        raise PresetError(f"preset {name!r}: {key!r} must be between {lo} and {hi}")
    return value
