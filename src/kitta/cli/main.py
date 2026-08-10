"""Entry point for the ``kitta`` command.

Placeholder until Phase 3; only ``--version`` works.
"""

import argparse

import kitta


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kitta", description=kitta.__doc__)
    parser.add_argument("--version", action="version", version=f"kitta {kitta.__version__}")
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
