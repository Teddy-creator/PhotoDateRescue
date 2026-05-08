"""Report-only reconciliation between candidate and baseline image trees."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from PIL import Image

from .media_decode import load_rgb_image

SKIPPED_ARTIFACT_SUFFIXES = {".csv", ".json", ".log", ".md", ".txt"}
SKIPPED_ARTIFACT_NAMES = {"_manifest.json"}


@dataclass
class ReconcileResult:
    candidate_total: int
    baseline_total: int
    matched_count: int
    unmatched_count: int
    candidate_error_count: int
    baseline_error_count: int
    summary_path: Path


def reconcile_directories(candidate: Path, baseline: Path, report_dir: Path) -> ReconcileResult:
    candidate_files = _discover_visible_files(candidate)
    baseline_files = _discover_visible_files(baseline)
    report_dir.mkdir(parents=True, exist_ok=True)

    baseline_index: Dict[Tuple[int, int, str], List[Path]] = defaultdict(list)
    baseline_errors = []
    for path in baseline_files:
        try:
            baseline_index[_build_visual_signature(path)].append(path)
        except Exception as exc:  # pragma: no cover - exercised through tests with monkeypatching
            baseline_errors.append({"side": "baseline", "path": str(path), "error": str(exc)})

    matched_rows = []
    unmatched_rows = []
    candidate_errors = []

    for path in candidate_files:
        try:
            width, height, dhash = _build_visual_signature(path)
        except Exception as exc:
            candidate_errors.append({"side": "candidate", "path": str(path), "error": str(exc)})
            continue

        matches = baseline_index.get((width, height, dhash))
        if matches:
            matched_rows.append(
                {
                    "candidate_path": str(path),
                    "baseline_path": str(matches[0]),
                    "width": width,
                    "height": height,
                    "dhash": dhash,
                }
            )
        else:
            unmatched_rows.append(
                {
                    "candidate_path": str(path),
                    "width": width,
                    "height": height,
                    "dhash": dhash,
                }
            )

    summary = {
        "candidate_total": len(candidate_files),
        "baseline_total": len(baseline_files),
        "matched_count": len(matched_rows),
        "unmatched_count": len(unmatched_rows),
        "candidate_error_count": len(candidate_errors),
        "baseline_error_count": len(baseline_errors),
    }
    summary_path = report_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(report_dir / "matched.csv", matched_rows)
    _write_csv(report_dir / "unmatched.csv", unmatched_rows)
    _write_csv(report_dir / "errors.csv", candidate_errors + baseline_errors)

    return ReconcileResult(
        candidate_total=len(candidate_files),
        baseline_total=len(baseline_files),
        matched_count=len(matched_rows),
        unmatched_count=len(unmatched_rows),
        candidate_error_count=len(candidate_errors),
        baseline_error_count=len(baseline_errors),
        summary_path=summary_path,
    )


def _discover_visible_files(root: Path) -> List[Path]:
    root = root.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError("Input directory does not exist: {0}".format(root))
    if not root.is_dir():
        raise NotADirectoryError("Input path is not a directory: {0}".format(root))
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not any(part.startswith(".") for part in path.relative_to(root).parts)
        and not _should_skip_file(path)
    )


def _should_skip_file(path: Path) -> bool:
    if path.name in SKIPPED_ARTIFACT_NAMES:
        return True
    return path.suffix.lower() in SKIPPED_ARTIFACT_SUFFIXES


def _build_visual_signature(path: Path) -> Tuple[int, int, str]:
    image = load_rgb_image(path)
    try:
        width, height = image.size
        return width, height, _dhash(image)
    finally:
        try:
            image.close()
        except Exception:
            pass


def _dhash(image: Image.Image, size: int = 8) -> str:
    grayscale = image.resize((size + 1, size), Image.Resampling.LANCZOS).convert("L")
    pixels = list(grayscale.getdata())
    width = size + 1
    value = 0
    for row in range(size):
        offset = row * width
        for col in range(size):
            value = (value << 1) | (1 if pixels[offset + col] > pixels[offset + col + 1] else 0)
    return "{0:016x}".format(value)


def _write_csv(path: Path, rows: Iterable[dict]) -> None:
    rows = list(rows)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(rows)
