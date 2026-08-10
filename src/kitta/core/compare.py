"""Orchestration of running multiple presets over a single image.

Inference runs sequentially by design: parallel CPU inference is slower
overall and heavier on memory, and running one preset at a time lets the
GUI show the first result as early as possible.

Model downloads, however, happen on a background thread: cached models
never wait for a download, and network time overlaps inference time.
"""

from __future__ import annotations

import queue
import threading
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
    ``on_start`` fires when inference for a preset begins;
    ``on_download_progress`` may fire before that (from the download
    thread) while the preset's model is being fetched.
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

    Presets whose model is already cached run first (in preset order);
    the remaining models are downloaded concurrently and run in download
    completion order. A preset that fails yields ``None`` in the result
    list; the failure is reported through ``on_error`` when provided, and
    re-raised otherwise.
    """
    callbacks = callbacks or CompareCallbacks()
    presets = list(presets)
    results: list[RemovalResult | None] = [None] * len(presets)

    available: list[tuple[int, Preset]] = []
    missing: list[tuple[int, Preset]] = []
    for index, preset in enumerate(presets):
        group = available if model_store.is_available(preset.model) else missing
        group.append((index, preset))

    # (index, preset, error) for each finished download
    downloaded: queue.SimpleQueue = queue.SimpleQueue()

    def download_all() -> None:
        for index, preset in missing:
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

            try:
                model_store.ensure(preset.model, progress_cb)
            except Exception as exc:  # noqa: BLE001 - marshaled back to the main loop
                downloaded.put((index, preset, exc))
                continue
            downloaded.put((index, preset, None))

    def run_inference(index: int, preset: Preset) -> None:
        if callbacks.on_start:
            callbacks.on_start(index, preset)
        try:
            result = remove_background(image, preset)
        except Exception as exc:
            if callbacks.on_error is None:
                raise
            callbacks.on_error(index, preset, exc)
            return
        results[index] = result
        if callbacks.on_result:
            callbacks.on_result(index, preset, result)

    downloader = None
    if missing:
        downloader = threading.Thread(target=download_all, name="kitta-model-download", daemon=True)
        downloader.start()

    for index, preset in available:
        run_inference(index, preset)

    for _ in missing:
        index, preset, error = downloaded.get()
        if error is not None:
            if callbacks.on_error is None:
                raise error
            callbacks.on_error(index, preset, error)
            continue
        run_inference(index, preset)

    if downloader is not None:
        downloader.join()
    return results
