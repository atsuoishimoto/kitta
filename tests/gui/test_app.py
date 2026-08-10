import sys

import pytest

from kitta.gui.app import _configure_platform


@pytest.fixture(autouse=True)
def linux_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")


def test_wslg_defaults_to_xcb(tmp_path):
    environ = {}
    _configure_platform(environ, wslg_dir=tmp_path)
    assert environ["QT_QPA_PLATFORM"] == "xcb"


def test_explicit_setting_is_respected(tmp_path):
    environ = {"QT_QPA_PLATFORM": "wayland"}
    _configure_platform(environ, wslg_dir=tmp_path)
    assert environ["QT_QPA_PLATFORM"] == "wayland"


def test_non_wslg_untouched(tmp_path):
    environ = {}
    _configure_platform(environ, wslg_dir=tmp_path / "missing")
    assert "QT_QPA_PLATFORM" not in environ


def test_non_linux_untouched(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    environ = {}
    _configure_platform(environ, wslg_dir=tmp_path)
    assert "QT_QPA_PLATFORM" not in environ
