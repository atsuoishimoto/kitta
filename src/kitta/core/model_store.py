"""Model download and local cache management.

Downloads go to ``<filename>.part`` first and are renamed into place only
after the checksum verifies. An interrupted download leaves the ``.part``
file behind and is resumed with an HTTP Range request when the server
supports it (falling back to a full restart otherwise).
"""

from __future__ import annotations

import hashlib
import urllib.request
from collections.abc import Callable
from pathlib import Path

from kitta.core import paths
from kitta.core.models import ModelSpec

# progress_cb(bytes_done, bytes_total) — shared by the CLI progress bar and
# the GUI progress display.
ProgressCallback = Callable[[int, int], None]

_CHUNK_SIZE = 256 * 1024


class ModelStoreError(Exception):
    """Base error for model store failures."""


class DownloadError(ModelStoreError):
    """The model could not be downloaded (network failure, HTTP error...)."""


class ChecksumError(ModelStoreError):
    """The downloaded file did not match the expected checksum."""


def model_path(spec: ModelSpec, models_dir: Path | None = None) -> Path:
    directory = models_dir if models_dir is not None else paths.models_dir()
    return directory / spec.filename


def is_available(spec: ModelSpec, models_dir: Path | None = None) -> bool:
    return model_path(spec, models_dir).exists()


def ensure(
    spec: ModelSpec,
    progress_cb: ProgressCallback | None = None,
    models_dir: Path | None = None,
) -> Path:
    """Return the local path of the model, downloading it if necessary."""
    dest = model_path(spec, models_dir)
    if dest.exists():
        return dest
    return download(spec, progress_cb, models_dir)


def download(
    spec: ModelSpec,
    progress_cb: ProgressCallback | None = None,
    models_dir: Path | None = None,
) -> Path:
    dest = model_path(spec, models_dir)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")

    offset = part.stat().st_size if part.exists() else 0
    request = urllib.request.Request(spec.url)
    if offset:
        request.add_header("Range", f"bytes={offset}-")

    try:
        response = urllib.request.urlopen(request)
    except OSError as exc:
        raise DownloadError(f"failed to download {spec.name}: {exc}") from exc

    with response:
        if offset and response.status != 206:
            # Server ignored the Range request; start over.
            offset = 0
        total = _total_size(response, offset) or spec.size
        done = offset
        with open(part, "ab" if offset else "wb") as f:
            if progress_cb:
                progress_cb(done, total)
            while chunk := response.read(_CHUNK_SIZE):
                f.write(chunk)
                done += len(chunk)
                if progress_cb:
                    progress_cb(done, total)

    _verify_checksum(part, spec)
    part.replace(dest)
    return dest


def _total_size(response, offset: int) -> int:
    if response.status == 206:
        # Content-Range: bytes <start>-<end>/<total>
        content_range = response.headers.get("Content-Range", "")
        _, _, total = content_range.partition("/")
        if total.isdigit():
            return int(total)
        return 0
    content_length = response.headers.get("Content-Length")
    return int(content_length) + offset if content_length else 0


def _verify_checksum(path: Path, spec: ModelSpec) -> None:
    algorithm, _, expected = spec.checksum.partition(":")
    digest = hashlib.new(algorithm)
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK_SIZE):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual != expected:
        # A corrupt partial file cannot be resumed; force a clean retry.
        path.unlink(missing_ok=True)
        raise ChecksumError(f"checksum mismatch for {spec.name}: expected {expected}, got {actual}")
