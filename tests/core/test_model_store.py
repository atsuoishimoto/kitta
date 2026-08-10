import hashlib
import io
import urllib.error
import urllib.request

import pytest

from kitta.core import model_store
from kitta.core.models import MODELS, ModelSpec

PAYLOAD = b"kitta test model payload " * 64


def make_spec(checksum: str | None = None) -> ModelSpec:
    return ModelSpec(
        name="test-model",
        display_name="Test Model",
        url="https://example.invalid/test-model.onnx",
        filename="test-model.onnx",
        size=len(PAYLOAD),
        checksum=checksum or "md5:" + hashlib.md5(PAYLOAD).hexdigest(),
        license_name="MIT",
        license_url="https://example.invalid/",
    )


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200, headers: dict | None = None):
        self._io = io.BytesIO(body)
        self.status = status
        self.headers = headers if headers is not None else {"Content-Length": str(len(body))}

    def read(self, size: int = -1) -> bytes:
        return self._io.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_download_success(monkeypatch, tmp_path):
    spec = make_spec()
    monkeypatch.setattr(urllib.request, "urlopen", lambda req: FakeResponse(PAYLOAD))
    progress = []

    dest = model_store.download(spec, lambda done, total: progress.append((done, total)), tmp_path)

    assert dest == tmp_path / spec.filename
    assert dest.read_bytes() == PAYLOAD
    assert not (tmp_path / (spec.filename + ".part")).exists()
    assert progress[0] == (0, len(PAYLOAD))
    assert progress[-1] == (len(PAYLOAD), len(PAYLOAD))


def test_download_checksum_mismatch(monkeypatch, tmp_path):
    spec = make_spec(checksum="md5:" + "0" * 32)
    monkeypatch.setattr(urllib.request, "urlopen", lambda req: FakeResponse(PAYLOAD))

    with pytest.raises(model_store.ChecksumError):
        model_store.download(spec, models_dir=tmp_path)

    assert not (tmp_path / spec.filename).exists()
    assert not (tmp_path / (spec.filename + ".part")).exists()


def test_download_resumes_with_range(monkeypatch, tmp_path):
    spec = make_spec()
    half = len(PAYLOAD) // 2
    part = tmp_path / (spec.filename + ".part")
    part.write_bytes(PAYLOAD[:half])

    def fake_urlopen(req):
        assert req.get_header("Range") == f"bytes={half}-"
        headers = {"Content-Range": f"bytes {half}-{len(PAYLOAD) - 1}/{len(PAYLOAD)}"}
        return FakeResponse(PAYLOAD[half:], status=206, headers=headers)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    progress = []

    dest = model_store.download(spec, lambda done, total: progress.append((done, total)), tmp_path)

    assert dest.read_bytes() == PAYLOAD
    assert progress[0] == (half, len(PAYLOAD))
    assert progress[-1] == (len(PAYLOAD), len(PAYLOAD))


def test_download_restarts_when_server_ignores_range(monkeypatch, tmp_path):
    spec = make_spec()
    part = tmp_path / (spec.filename + ".part")
    part.write_bytes(PAYLOAD[: len(PAYLOAD) // 2])
    monkeypatch.setattr(urllib.request, "urlopen", lambda req: FakeResponse(PAYLOAD, status=200))

    dest = model_store.download(spec, models_dir=tmp_path)

    assert dest.read_bytes() == PAYLOAD


def test_download_network_error(monkeypatch, tmp_path):
    spec = make_spec()

    def fake_urlopen(req):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(model_store.DownloadError):
        model_store.download(spec, models_dir=tmp_path)


def test_ensure_skips_download_when_available(monkeypatch, tmp_path):
    spec = make_spec()
    (tmp_path / spec.filename).write_bytes(PAYLOAD)

    def fail_urlopen(req):
        raise AssertionError("should not download")

    monkeypatch.setattr(urllib.request, "urlopen", fail_urlopen)

    assert model_store.is_available(spec, tmp_path)
    assert model_store.ensure(spec, models_dir=tmp_path) == tmp_path / spec.filename


def test_download_cancelled_keeps_part_file(monkeypatch, tmp_path):
    spec = make_spec()
    monkeypatch.setattr(urllib.request, "urlopen", lambda req: FakeResponse(PAYLOAD))

    with pytest.raises(model_store.DownloadCancelled):
        model_store.download(spec, models_dir=tmp_path, should_cancel=lambda: True)

    assert not (tmp_path / spec.filename).exists()
    assert (tmp_path / (spec.filename + ".part")).exists()  # kept for resuming


@pytest.mark.network
def test_download_real_u2netp(tmp_path):
    spec = MODELS["u2netp"]
    progress = []

    dest = model_store.ensure(spec, lambda done, total: progress.append((done, total)), tmp_path)

    assert dest.stat().st_size == spec.size
    assert progress[-1][0] == spec.size
