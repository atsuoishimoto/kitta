"""Kitta — compare AI background removal models side by side. Fully offline."""

__version__ = "0.1.0"


def notice_text() -> str:
    """Third-party license notices (NOTICE.md) bundled with the package."""
    return _packaged_text("NOTICE.md")


def license_text() -> str:
    """Kitta's own license (LICENSE.txt) bundled with the package."""
    return _packaged_text("LICENSE.txt")


def _packaged_text(name: str) -> str:
    from importlib import resources

    return (resources.files(__name__) / name).read_text(encoding="utf-8")
