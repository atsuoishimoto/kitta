"""Kitta — compare AI background removal models side by side. Fully offline."""

__version__ = "0.1.0"


def notice_text() -> str:
    """Third-party license notices (NOTICE.md) bundled with the package."""
    from importlib import resources

    return (resources.files(__name__) / "NOTICE.md").read_text(encoding="utf-8")
