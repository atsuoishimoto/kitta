"""Orchestration of running multiple presets over a single image.

Presets run sequentially by design: parallel CPU inference is slower
overall and heavier on memory, and running one preset at a time lets the
GUI show the first result as early as possible.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PIL import Image

from kitta.core import model_store
from kitta.core.models import Preset
from kitta.core.remove import RemovalResult, remove_background


@dataclass
class CompareCallbacks:
    """Progress hooks; every field is optional.

    ``index`` is the position of the preset in the ``presets`` sequence.
    """

    on_start: Callable[[int, Preset], None] | None = None
    on_download_progress: Callable[[int, Preset, int, int], None] | None = None
    on_result: Callable[[int, Preset, RemovalResult], None] | None = None
    on_error: Callable[[int, Preset, Exception], None] | None = None


def compare(
    image: Image.Image,
    presets: Sequence[Preset],
    callbacks: CompareCallbacks | None = None,
) -> list[RemovalResult | None]:
    """Run every preset over ``image`` and return results in preset order.

    A preset that fails yields ``None`` in the result list; the failure is
    reported through ``on_error`` when provided, and re-raised otherwise.
    """
    callbacks = callbacks or CompareCallbacks()
    results: list[RemovalResult | None] = []
    for index, preset in enumerate(presets):
        if callbacks.on_start:
            callbacks.on_start(index, preset)
        try:
            if not model_store.is_available(preset.model):
                progress_cb = None
                if callbacks.on_download_progress:

                    def progress_cb(
                        done,
                        total,
                        index=index,
                        preset=preset,
                        cb=callbacks.on_download_progress,
                    ):
                        cb(index, preset, done, total)

                model_store.ensure(preset.model, progress_cb)
            result = remove_background(image, preset)
        except Exception as exc:
            if callbacks.on_error is None:
                raise
            results.append(None)
            callbacks.on_error(index, preset, exc)
            continue
        results.append(result)
        if callbacks.on_result:
            callbacks.on_result(index, preset, result)
    return results
