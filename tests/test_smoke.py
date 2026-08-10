import pytest

import kitta
from kitta.cli.main import main


def test_version():
    assert kitta.__version__


def test_cli_version_flag(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert kitta.__version__ in capsys.readouterr().out
