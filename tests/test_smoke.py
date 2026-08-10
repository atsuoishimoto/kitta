import kitta
from kitta.cli.main import main


def test_version():
    assert kitta.__version__


def test_cli_runs():
    assert main([]) == 0
