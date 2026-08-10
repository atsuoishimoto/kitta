import pytest
from PIL import Image

from kitta.core.models import PRESETS
from kitta.core.remove import RemovalResult
from kitta.gui import workers as workers_mod
from kitta.gui.workers import CompareWorker

PRESET_LIST = [PRESETS["fast"], PRESETS["balanced"]]


def fake_result(preset) -> RemovalResult:
    rgba = Image.new("RGBA", (8, 8))
    return RemovalResult(
        image=rgba,
        mask=rgba.getchannel("A"),
        elapsed=0.01,
        model_name=preset.model.name,
        preset_name=preset.name,
    )


def fake_compare(image, presets, callbacks):
    results = []
    for index, preset in enumerate(presets):
        callbacks.on_start(index, preset)
        if preset.name == "balanced":
            callbacks.on_error(index, preset, RuntimeError("boom"))
            results.append(None)
            continue
        callbacks.on_download_progress(index, preset, 50, 100)
        result = fake_result(preset)
        results.append(result)
        callbacks.on_result(index, preset, result)
    return results


@pytest.fixture
def worker(monkeypatch, qtbot):
    monkeypatch.setattr(workers_mod, "compare", fake_compare)
    return CompareWorker(Image.new("RGB", (8, 8)), PRESET_LIST)


def test_worker_emits_lifecycle_signals(worker, qtbot):
    events = []
    worker.model_started.connect(lambda i, p: events.append(("start", i, p.name)))
    worker.download_progress.connect(lambda i, p, d, t: events.append(("dl", i, d, t)))
    worker.result_ready.connect(lambda i, p, r: events.append(("result", i, r.preset_name)))
    worker.model_failed.connect(lambda i, p, m: events.append(("failed", i, m)))

    with qtbot.waitSignal(worker.compare_finished, timeout=5000) as blocker:
        worker.start()
    qtbot.waitUntil(worker.isFinished, timeout=5000)

    results = blocker.args[0]
    assert results[0].preset_name == "fast"
    assert results[1] is None
    assert events == [
        ("start", 0, "fast"),
        ("dl", 0, 50, 100),
        ("result", 0, "fast"),
        ("start", 1, "balanced"),
        ("failed", 1, "boom"),
    ]


def test_worker_survives_total_failure(monkeypatch, qtbot):
    def broken_compare(image, presets, callbacks):
        raise RuntimeError("catastrophic")

    monkeypatch.setattr(workers_mod, "compare", broken_compare)
    worker = CompareWorker(Image.new("RGB", (8, 8)), PRESET_LIST)
    failures = []
    worker.model_failed.connect(lambda i, p, m: failures.append((i, m)))

    with qtbot.waitSignal(worker.compare_finished, timeout=5000) as blocker:
        worker.start()
    qtbot.waitUntil(worker.isFinished, timeout=5000)

    assert blocker.args[0] == [None, None]
    assert failures == [(0, "catastrophic"), (1, "catastrophic")]
