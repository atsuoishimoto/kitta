from pathlib import Path

import kitta
from kitta.core.models import MODELS, PRESETS


def test_root_notice_matches_packaged_copy():
    root = Path(__file__).resolve().parents[1] / "NOTICE.md"
    assert root.read_text(encoding="utf-8") == kitta.notice_text()


def test_root_license_matches_packaged_copy():
    # LICENSE, not the LICENSE.txt symlink: Windows checkouts materialise the
    # symlink as a text file holding its target's name.
    root = Path(__file__).resolve().parents[1] / "LICENSE"
    assert root.read_text(encoding="utf-8") == kitta.license_text()


def test_notice_covers_catalog():
    text = kitta.notice_text()
    for spec in MODELS.values():
        assert spec.license_name in text, spec.name
    for preset in PRESETS.values():
        assert preset.display_name in text, preset.name
