"""Defaults used by the guided terminal wizard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_EXCLUDES = (
    "Pictures/.thumbnails",
    "Pictures/.gs",
    "Pictures/.gs_fs0",
    "Pictures/.gs_fs3",
    "Pictures/.gs_fs6",
    "DCIM/.globalTrash",
    "DCIM/_.globalTrash",
    "DCIM/.tmfs",
    "DCIM/.tmsdual",
)


@dataclass(frozen=True)
class WizardOutputLayout:
    base: Path
    scan_report: Path
    repaired_media: Path
    live_work: Path
    live_output: Path


def build_output_layout(base: Path) -> WizardOutputLayout:
    base = base.expanduser()
    return WizardOutputLayout(
        base=base,
        scan_report=base / "scan-report",
        repaired_media=base / "repaired-media",
        live_work=base / "live-work",
        live_output=base / "live-output",
    )


def suggest_run_dir(base: Path, suffix: str) -> Path:
    base = base.expanduser()
    if not base.exists():
        return base
    return base.with_name("{0}-{1}".format(base.name, suffix))
