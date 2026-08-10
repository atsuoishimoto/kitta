import threading

import pytest
from PIL import Image

from kitta.core import compare as compare_mod
from kitta.core.compare import CompareCallbacks, compare
from kitta.core.models import PRESETS
from kitta.core.remove import RemovalResult

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


@pytest.fixture
def no_download(monkeypatch):
    monkeypatch.setattr(compare_mod.model_store, "is_available", lambda spec: True)


def test_compare_runs_presets_in_order(monkeypatch, no_download, sample_image):
    monkeypatch.setattr(compare_mod, "remove_background", lambda image, preset: fake_result(preset))
    events = []
    callbacks = CompareCallbacks(
        on_start=lambda i, p: events.append(("start", i, p.name)),
        on_result=lambda i, p, r: events.append(("result", i, p.name)),
    )

    results = compare(sample_image, PRESET_LIST, callbacks)

    assert [r.preset_name for r in results] == ["fast", "balanced"]
    assert events == [
        ("start", 0, "fast"),
        ("result", 0, "fast"),
        ("start", 1, "balanced"),
        ("result", 1, "balanced"),
    ]


def test_compare_downloads_missing_model(monkeypatch, sample_image):
    monkeypatch.setattr(compare_mod.model_store, "is_available", lambda spec: False)
    downloads = []

    def fake_ensure(spec, progress_cb=None, should_cancel=None):
        progress_cb(50, 100)
        downloads.append(spec.name)

    monkeypatch.setattr(compare_mod.model_store, "ensure", fake_ensure)
    monkeypatch.setattr(compare_mod, "remove_background", lambda image, preset: fake_result(preset))
    progress_events = []
    callbacks = CompareCallbacks(
        on_download_progress=lambda i, p, done, total: progress_events.append(
            (i, p.name, done, total)
        ),
    )

    compare(sample_image, [PRESETS["fast"]], callbacks)

    assert downloads == ["u2netp"]
    assert progress_events == [(0, "fast", 50, 100)]


def test_compare_reports_errors_and_continues(monkeypatch, no_download, sample_image):
    def flaky_remove(image, preset):
        if preset.name == "fast":
            raise RuntimeError("boom")
        return fake_result(preset)

    monkeypatch.setattr(compare_mod, "remove_background", flaky_remove)
    errors = []
    callbacks = CompareCallbacks(on_error=lambda i, p, exc: errors.append((i, p.name, str(exc))))

    results = compare(sample_image, PRESET_LIST, callbacks)

    assert results[0] is None
    assert results[1].preset_name == "balanced"
    assert errors == [(0, "fast", "boom")]


def test_cached_presets_run_before_downloads(monkeypatch, sample_image):
    fast, balanced = PRESETS["fast"], PRESETS["balanced"]
    # balanced is cached; fast needs a (slow) download
    monkeypatch.setattr(compare_mod.model_store, "is_available", lambda spec: spec.name != "u2netp")
    release_download = threading.Event()

    def fake_ensure(spec, progress_cb=None, should_cancel=None):
        assert release_download.wait(5)

    monkeypatch.setattr(compare_mod.model_store, "ensure", fake_ensure)
    monkeypatch.setattr(compare_mod, "remove_background", lambda image, preset: fake_result(preset))
    events = []

    def on_result(index, preset, result):
        events.append(("result", index, preset.name))
        if preset.name == "balanced":
            # let the download finish only after the cached preset ran
            release_download.set()

    results = compare(sample_image, [fast, balanced], CompareCallbacks(on_result=on_result))

    assert events == [("result", 1, "balanced"), ("result", 0, "fast")]
    assert results[0].preset_name == "fast"
    assert results[1].preset_name == "balanced"


def test_download_failure_is_reported_and_others_continue(monkeypatch, sample_image):
    monkeypatch.setattr(compare_mod.model_store, "is_available", lambda spec: False)

    def fake_ensure(spec, progress_cb=None, should_cancel=None):
        if spec.name == "u2netp":
            raise RuntimeError("network down")

    monkeypatch.setattr(compare_mod.model_store, "ensure", fake_ensure)
    monkeypatch.setattr(compare_mod, "remove_background", lambda image, preset: fake_result(preset))
    errors = []
    callbacks = CompareCallbacks(on_error=lambda i, p, exc: errors.append((i, p.name, str(exc))))

    results = compare(sample_image, PRESET_LIST, callbacks)

    assert results[0] is None
    assert results[1].preset_name == "balanced"
    assert errors == [(0, "fast", "network down")]


def test_cancel_between_presets(monkeypatch, no_download, sample_image):
    cancelled_flag = {"value": False}

    def fake_remove(image, preset):
        cancelled_flag["value"] = True  # cancel right after the first inference
        return fake_result(preset)

    monkeypatch.setattr(compare_mod, "remove_background", fake_remove)
    cancelled = []
    callbacks = CompareCallbacks(
        on_cancelled=lambda i, p: cancelled.append((i, p.name)),
        should_cancel=lambda: cancelled_flag["value"],
    )

    results = compare(sample_image, PRESET_LIST, callbacks)

    assert results[0].preset_name == "fast"
    assert results[1] is None
    assert cancelled == [(1, "balanced")]


def test_cancel_during_download(monkeypatch, sample_image):
    from kitta.core import model_store

    monkeypatch.setattr(compare_mod.model_store, "is_available", lambda spec: False)

    def fake_ensure(spec, progress_cb=None, should_cancel=None):
        raise model_store.DownloadCancelled("cancelled")

    monkeypatch.setattr(compare_mod.model_store, "ensure", fake_ensure)
    monkeypatch.setattr(compare_mod, "remove_background", lambda image, preset: fake_result(preset))
    cancelled = []
    callbacks = CompareCallbacks(on_cancelled=lambda i, p: cancelled.append((i, p.name)))

    results = compare(sample_image, PRESET_LIST, callbacks)

    assert results == [None, None]
    assert sorted(cancelled) == [(0, "fast"), (1, "balanced")]


def test_compare_raises_without_error_callback(monkeypatch, no_download, sample_image):
    def broken_remove(image, preset):
        raise RuntimeError("boom")

    monkeypatch.setattr(compare_mod, "remove_background", broken_remove)

    with pytest.raises(RuntimeError, match="boom"):
        compare(sample_image, PRESET_LIST)


@pytest.mark.inference
def test_compare_end_to_end_u2netp(sample_image):
    results = compare(sample_image, [PRESETS["fast"]])

    assert len(results) == 1
    assert results[0].image.mode == "RGBA"
    assert results[0].model_name == "u2netp"
