"""Display-independent data models for the beginner GUI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    available: bool
    path: Optional[str] = None
    required: bool = False
    hint: str = ""


@dataclass(frozen=True)
class GuiScanSummary:
    total_files: int
    photo_files: int
    video_files: int
    repairable_files: int
    ok_files: int
    high_risk_files: int
    unsupported_files: int
    error_files: int
    report_dir: Path


@dataclass(frozen=True)
class GuiRepairSummary:
    copied: int
    repaired: int
    failed: int
    skipped: int
    output_dir: Path
