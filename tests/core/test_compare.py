import pytest
from PIL import Image

from kitta.core import compare as compare_mod
from kitta.core.compare import CompareCallbacks, compare
from kitta.core.models import PRESETS
from kitta.core.remove import RemovalResult

PRESET_LIST = [PRESETS["fast"], PRESETS["fine-detail"]]


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

    assert [r.preset_name for r in results] == ["fast", "fine-detail"]
    assert events == [
        ("start", 0, "fast"),
        ("result", 0, "fast"),
        ("start", 1, "fine-detail"),
        ("result", 1, "fine-detail"),
    ]


def test_compare_downloads_missing_model(monkeypatch, sample_image):
    monkeypatch.setattr(compare_mod.model_store, "is_available", lambda spec: False)
    downloads = []

    def fake_ensure(spec, progress_cb=None):
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
    assert results[1].preset_name == "fine-detail"
    assert errors == [(0, "fast", "boom")]


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
