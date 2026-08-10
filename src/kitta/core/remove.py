"""Background removal execution (rembg wrapper, session management).

rembg imports are deferred into the functions: importing rembg pulls in
onnxruntime/scipy and takes noticeable time, which CLI startup and unit
tests should not pay unless inference actually runs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from PIL import Image

from kitta.core import model_store, paths
from kitta.core.models import Preset

_sessions: dict[str, object] = {}


@dataclass
class RemovalResult:
    image: Image.Image  # RGBA cutout
    mask: Image.Image  # alpha mask ("L")
    elapsed: float  # inference time in seconds
    model_name: str
    preset_name: str


def _get_session(model_name: str):
    """Return a cached rembg session, creating it on first use."""
    session = _sessions.get(model_name)
    if session is None:
        paths.configure_rembg_model_dir()
        from rembg import new_session

        session = new_session(model_name)
        _sessions[model_name] = session
    return session


def clear_sessions() -> None:
    _sessions.clear()


def remove_background(image: Image.Image, preset: Preset) -> RemovalResult:
    """Run background removal on ``image`` with ``preset``.

    The model must already be in the local cache for progress reporting;
    otherwise it is fetched here without progress (callers wanting progress
    use model_store.ensure / compare beforehand).
    """
    model_store.ensure(preset.model)
    session = _get_session(preset.model.name)
    from rembg import remove

    start = time.perf_counter()
    result = remove(
        image,
        session=session,
        alpha_matting=preset.alpha_matting.enabled,
        alpha_matting_foreground_threshold=preset.alpha_matting.foreground_threshold,
        alpha_matting_background_threshold=preset.alpha_matting.background_threshold,
        alpha_matting_erode_size=preset.alpha_matting.erode_size,
    )
    elapsed = time.perf_counter() - start

    rgba = result if result.mode == "RGBA" else result.convert("RGBA")
    mask = rgba.getchannel("A")
    return RemovalResult(
        image=rgba,
        mask=mask,
        elapsed=elapsed,
        model_name=preset.model.name,
        preset_name=preset.name,
    )
