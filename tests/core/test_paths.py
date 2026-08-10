import os
import sys
from pathlib import Path

from kitta.core import paths


def test_models_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("KITTA_MODEL_DIR", str(tmp_path / "override"))
    assert paths.models_dir() == tmp_path / "override"


def test_linux_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("KITTA_MODEL_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg-cache"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    assert paths.models_dir() == tmp_path / "xdg-cache" / "kitta" / "models"
    assert paths.config_dir() == tmp_path / "xdg-config" / "kitta"


def test_windows_dirs(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("KITTA_MODEL_DIR", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    assert paths.models_dir() == tmp_path / "Local" / "kitta" / "cache" / "models"
    assert paths.config_dir() == tmp_path / "Roaming" / "kitta"


def test_darwin_dirs(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delenv("KITTA_MODEL_DIR", raising=False)
    home = Path.home()
    assert paths.models_dir() == home / "Library" / "Caches" / "kitta" / "models"
    assert paths.config_dir() == home / "Library" / "Application Support" / "kitta"


def test_configure_rembg_model_dir(monkeypatch, tmp_path):
    model_dir = tmp_path / "models"
    monkeypatch.setenv("KITTA_MODEL_DIR", str(model_dir))
    result = paths.configure_rembg_model_dir()
    assert result == model_dir
    assert model_dir.is_dir()
    assert os.environ["U2NET_HOME"] == str(model_dir)
