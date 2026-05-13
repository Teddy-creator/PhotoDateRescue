"""Executable launcher for the beginner GUI."""

from __future__ import annotations

import argparse
from typing import Optional, Sequence

from photodaterescue.gui_app import main


def build_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="photodaterescue-gui",
        description="启动 PhotoDateRescue 图形界面。",
    )


def cli(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    try:
        parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    main()
    return 0


if __name__ == "__main__":  # pragma: no cover - manual app launch
    raise SystemExit(cli())
