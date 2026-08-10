"""Entry point for the ``kitta`` command.

Usage:
    kitta IMAGE [-o OUT] [--model NAME | --preset NAME] [--mask]
    kitta compare IMAGE [--presets a,b | --models a,b] [--output-dir DIR]
    kitta batch INPUT_DIR (--preset NAME | --model NAME) --output DIR
                [--skip-existing]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

import kitta
from kitta.core import compare as compare_mod
from kitta.core import model_store, presets
from kitta.core.models import (
    DEFAULT_PRESET_NAMES,
    PRESETS,
    Preset,
    get_model,
    get_preset,
)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

DEFAULT_PRESET = "fast"


class CliError(Exception):
    """User-facing CLI failure; message is printed and exit code is 1."""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    commands = {"compare": run_compare, "batch": run_batch}
    command = commands.get(argv[0]) if argv else None
    try:
        if command is not None:
            return command(argv[1:])
        return run_single(argv)
    except CliError as exc:
        print(f"kitta: error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nkitta: interrupted", file=sys.stderr)
        return 130


# --- kitta IMAGE ---------------------------------------------------------


def run_single(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="kitta",
        description="Remove the background of an image. "
        "Subcommands: kitta compare, kitta batch (see 'kitta compare --help').",
    )
    parser.add_argument("--version", action="version", version=f"kitta {kitta.__version__}")
    parser.add_argument("image", type=Path, help="input image file")
    parser.add_argument("-o", "--output", type=Path, help="output PNG (default: NAME-cutout.png)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--model", help="rembg model name to use")
    group.add_argument(
        "--preset",
        help=f"preset name or preset TOML file (default: {DEFAULT_PRESET})",
    )
    parser.add_argument(
        "--mask", action="store_true", help="also save the alpha mask as NAME-mask.png"
    )
    args = parser.parse_args(argv)

    preset = _resolve_preset(args.model, args.preset)
    image = _load_image(args.image)
    output = args.output or args.image.with_name(args.image.stem + "-cutout.png")

    _ensure_model(preset)
    result = _remove(image, preset)
    _save_image(result.image, output)
    print(f"{output}  ({preset.model.name}, {result.elapsed:.2f}s)")

    if args.mask:
        mask_path = output.parent / (args.image.stem + "-mask.png")
        _save_image(result.mask, mask_path)
        print(f"{mask_path}")
    return 0


# --- kitta compare -------------------------------------------------------


def run_compare(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="kitta compare",
        description="Run multiple models over one image and save each result.",
    )
    parser.add_argument("image", type=Path, help="input image file")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--models", help="comma-separated rembg model names")
    group.add_argument(
        "--presets",
        help="comma-separated preset names (default: " + ",".join(DEFAULT_PRESET_NAMES) + ")",
    )
    parser.add_argument(
        "--output-dir", type=Path, help="output directory (default: next to the input image)"
    )
    args = parser.parse_args(argv)

    if args.models:
        preset_list = [_model_preset(name) for name in _split_names(args.models)]
    else:
        names = _split_names(args.presets) if args.presets else DEFAULT_PRESET_NAMES
        preset_list = [_named_preset(name) for name in names]

    image = _load_image(args.image)
    output_dir = args.output_dir or args.image.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(preset_list)
    outputs: dict[str, Path] = {}
    failures: list[str] = []

    def on_start(index: int, preset: Preset) -> None:
        print(f"[{index + 1}/{total}] {preset.name} ({preset.model.name}) ...", file=sys.stderr)

    def on_download_progress(index: int, preset: Preset, done: int, total_bytes: int) -> None:
        _print_progress(f"  downloading {preset.model.name}", done, total_bytes)

    def on_result(index: int, preset: Preset, result) -> None:
        output = output_dir / f"{args.image.stem}-{preset.name}.png"
        _save_image(result.image, output)
        outputs[preset.name] = output
        print(f"  {output}  ({result.elapsed:.2f}s)")

    def on_error(index: int, preset: Preset, exc: Exception) -> None:
        failures.append(preset.name)
        print(f"  {preset.name}: failed: {exc}", file=sys.stderr)

    results = compare_mod.compare(
        image,
        preset_list,
        compare_mod.CompareCallbacks(
            on_start=on_start,
            on_download_progress=on_download_progress,
            on_result=on_result,
            on_error=on_error,
        ),
    )

    print(f"\n{len([r for r in results if r])}/{total} succeeded")
    for preset, result in zip(preset_list, results, strict=True):
        if result:
            print(f"  {preset.name:<15} {result.elapsed:>7.2f}s  {outputs[preset.name]}")
        else:
            print(f"  {preset.name:<15}   failed")
    return 1 if failures else 0


# --- kitta batch ---------------------------------------------------------


def run_batch(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="kitta batch",
        description="Apply one preset to every image in a directory.",
    )
    parser.add_argument("input_dir", type=Path, help="directory containing input images")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preset", help="preset name or preset TOML file")
    group.add_argument("--model", help="rembg model name to use")
    parser.add_argument(
        "--output", type=Path, required=True, help="output directory (created if missing)"
    )
    parser.add_argument(
        "--skip-existing", action="store_true", help="skip images whose output already exists"
    )
    args = parser.parse_args(argv)

    preset = _resolve_preset(args.model, args.preset)
    if not args.input_dir.is_dir():
        raise CliError(f"not a directory: {args.input_dir}")

    images = sorted(
        p for p in args.input_dir.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        raise CliError(f"no image files found in {args.input_dir}")

    args.output.mkdir(parents=True, exist_ok=True)
    _ensure_model(preset)

    total = len(images)
    processed = 0
    skipped = 0
    failed: list[tuple[Path, str]] = []
    for index, path in enumerate(images, start=1):
        output = args.output / (path.stem + ".png")
        if args.skip_existing and output.exists():
            skipped += 1
            print(f"[{index}/{total}] {path.name}: skipped (exists)")
            continue
        try:
            result = _remove(_load_image(path), preset)
            _save_image(result.image, output)
        except Exception as exc:  # noqa: BLE001 - batch keeps going and reports at the end
            failed.append((path, str(exc)))
            print(f"[{index}/{total}] {path.name}: failed: {exc}", file=sys.stderr)
            continue
        processed += 1
        print(f"[{index}/{total}] {path.name} -> {output.name}  ({result.elapsed:.2f}s)")

    print(f"\nprocessed {processed}, skipped {skipped}, failed {len(failed)} (of {total})")
    for path, message in failed:
        print(f"  {path.name}: {message}", file=sys.stderr)
    return 1 if failed else 0


# --- helpers -------------------------------------------------------------


def _split_names(value: str) -> list[str]:
    names = [name.strip() for name in value.split(",") if name.strip()]
    if not names:
        raise CliError("empty model/preset list")
    return names


def _named_preset(name: str) -> Preset:
    try:
        return get_preset(name)
    except ValueError as exc:
        raise CliError(str(exc)) from None


def _model_preset(name: str) -> Preset:
    try:
        model = get_model(name)
    except ValueError as exc:
        raise CliError(str(exc)) from None
    return Preset(name=model.name, display_name=model.display_name, model=model)


def _resolve_preset(model_name: str | None, preset_name: str | None) -> Preset:
    if model_name:
        return _model_preset(model_name)
    if preset_name is None:
        preset_name = DEFAULT_PRESET
    if preset_name in PRESETS:
        return PRESETS[preset_name]
    path = Path(preset_name)
    if path.suffix == ".toml" or path.exists():
        try:
            return presets.load_preset(path)
        except presets.PresetError as exc:
            raise CliError(str(exc)) from None
    known = ", ".join(PRESETS)
    raise CliError(f"unknown preset {preset_name!r} (available: {known}, or a .toml file)")


def _load_image(path: Path) -> Image.Image:
    try:
        with Image.open(path) as img:
            return img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img.copy()
    except FileNotFoundError:
        raise CliError(f"file not found: {path}") from None
    except OSError as exc:
        raise CliError(f"cannot read image {path}: {exc}") from None


def _save_image(image: Image.Image, path: Path) -> None:
    try:
        image.save(path, format="PNG")
    except OSError as exc:
        raise CliError(f"cannot write {path}: {exc}") from None


def _ensure_model(preset: Preset) -> None:
    if model_store.is_available(preset.model):
        return
    label = f"downloading {preset.model.name}"
    try:
        model_store.ensure(preset.model, lambda done, total: _print_progress(label, done, total))
    except model_store.ModelStoreError as exc:
        raise CliError(str(exc)) from None


def _remove(image: Image.Image, preset: Preset):
    from kitta.core.remove import remove_background

    try:
        return remove_background(image, preset)
    except model_store.ModelStoreError as exc:
        raise CliError(str(exc)) from None


def _print_progress(label: str, done: int, total: int) -> None:
    if total:
        width = 20
        filled = min(width, width * done // total)
        bar = "=" * filled + " " * (width - filled)
        percent = min(100, 100 * done // total)
        line = f"\r{label}: [{bar}] {percent:3d}% {done / 1e6:.1f}/{total / 1e6:.1f} MB"
        end = "\n" if done >= total else ""
    else:
        line = f"\r{label}: {done / 1e6:.1f} MB"
        end = ""
    print(line, end=end, file=sys.stderr, flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
