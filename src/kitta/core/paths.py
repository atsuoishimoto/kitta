"""Cache / config directory resolution.

Kitta keeps its model cache in an app-specific directory instead of
rembg's default ``~/.u2net``; rembg is pointed at it via the
``U2NET_HOME`` environment variable (see :func:`configure_rembg_model_dir`).

The ``KITTA_MODEL_DIR`` environment variable overrides the model cache
location (used by tests and CI).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "kitta"


def cache_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        return base / APP_NAME / "cache"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / APP_NAME
    base = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    return base / APP_NAME


def config_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return base / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / APP_NAME


def models_dir() -> Path:
    if override := os.environ.get("KITTA_MODEL_DIR"):
        return Path(override)
    return cache_dir() / "models"


def configure_rembg_model_dir() -> Path:
    """Create the model cache directory and point rembg at it.

    Must be called before any rembg session is created.
    """
    directory = models_dir()
    directory.mkdir(parents=True, exist_ok=True)
    os.environ["U2NET_HOME"] = str(directory)
    return directory
