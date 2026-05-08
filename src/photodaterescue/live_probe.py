"""Batch read-only probing for Live Photo metadata readiness."""

from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Sequence

from .live_build import LiveBuildPair, _read_pairs_csv, _resolve_source_path
from .live_inspect import inspect_live_pair
from .metadata import ExifToolClient


LIVE_PROBE_FIELDS = [
    "pair_id",
    "category",
    "confidence",
    "reason",
    "image_source",
    "video_source",
    "apple_live_status",
    "content_identifier_match",
    "image_content_identifier",
    "video_content_identifier",
    "image_makernotes_present",
    "video_duration",
    "windows_writer_status",
    "windows_writer_reason",
]
LIVE_PROBE_ERROR_FIELDS = [
    "pair_id",
    "category",
    "confidence",
    "image_source",
    "video_source",
    "error",
]


@dataclass
class LiveProbeResult:
    total_count: int
    metadata_match_count: int
    metadata_blocked_count: int
    error_count: int
    manifest_path: Path
    rows_path: Path
    errors_path: Path


def probe_live_pairs(
    pairs_csv: Path,
    source_root: Path,
    report_dir: Path,
    client: ExifToolClient,
) -> LiveProbeResult:
    pairs_csv = pairs_csv.expanduser().resolve()
    source_root = source_root.expanduser().resolve()
    report_dir = report_dir.expanduser().resolve()
    pairs = _read_pairs_csv(pairs_csv)

    rows = []
    errors = []
    status_counts: Counter[str] = Counter()
    writer_counts: Counter[str] = Counter()

    for pair in pairs:
        try:
            image_source = _resolve_source_path(source_root, pair.image_relative_path)
            video_source = _resolve_source_path(source_root, pair.video_relative_path)
            _ensure_file(image_source, "image")
            _ensure_file(video_source, "video")
            inspection = inspect_live_pair(image_source, video_source, client)
        except Exception as exc:
            errors.append(_error_row(pair, source_root / pair.image_relative_path, source_root / pair.video_relative_path, str(exc)))
            status_counts["error"] += 1
            continue

        writer_status, writer_reason = _windows_writer_readiness(inspection)
        rows.append(_row(pair, image_source, video_source, inspection, writer_status, writer_reason))
        status_counts[inspection["apple_live_status"]] += 1
        writer_counts[writer_status] += 1

    report_dir.mkdir(parents=True, exist_ok=True)
    rows_path = report_dir / "live-probe.csv"
    errors_path = report_dir / "errors.csv"
    manifest_path = report_dir / "live-probe-manifest.json"
    _write_csv(rows_path, LIVE_PROBE_FIELDS, rows)
    _write_csv(errors_path, LIVE_PROBE_ERROR_FIELDS, errors)
    manifest = {
        "pairs_csv": str(pairs_csv),
        "source_root": str(source_root),
        "total_count": len(rows) + len(errors),
        "error_count": len(errors),
        "status_counts": dict(status_counts),
        "windows_writer_counts": dict(writer_counts),
        "reports": {
            "rows": "live-probe.csv",
            "errors": "errors.csv",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return LiveProbeResult(
        total_count=len(rows) + len(errors),
        metadata_match_count=status_counts.get("metadata_match", 0),
        metadata_blocked_count=writer_counts.get("metadata_blocked", 0),
        error_count=len(errors),
        manifest_path=manifest_path,
        rows_path=rows_path,
        errors_path=errors_path,
    )


def _windows_writer_readiness(inspection: Dict[str, object]) -> tuple[str, str]:
    image = inspection["image"]
    video = inspection["video"]
    if inspection["apple_live_status"] == "metadata_match":
        return "already_live_metadata", "matching image/video identifiers already present"
    if not image.get("apple_makernotes_present"):
        return "metadata_blocked", "still image lacks Apple Maker Notes"
    if not video.get("content_identifier"):
        return "video_identifier_missing", "video lacks ContentIdentifier but image Maker Notes exist"
    return "metadata_mismatch", "image/video identifiers do not match"


def _row(
    pair: LiveBuildPair,
    image_source: Path,
    video_source: Path,
    inspection: Dict[str, object],
    writer_status: str,
    writer_reason: str,
) -> Dict[str, str]:
    image = inspection["image"]
    video = inspection["video"]
    return {
        "pair_id": pair.pair_id,
        "category": pair.category,
        "confidence": pair.confidence,
        "reason": pair.reason,
        "image_source": str(image_source),
        "video_source": str(video_source),
        "apple_live_status": str(inspection["apple_live_status"]),
        "content_identifier_match": str(inspection["content_identifier_match"]),
        "image_content_identifier": str(image.get("content_identifier") or ""),
        "video_content_identifier": str(video.get("content_identifier") or ""),
        "image_makernotes_present": str(image.get("apple_makernotes_present")),
        "video_duration": str(video.get("duration") or ""),
        "windows_writer_status": writer_status,
        "windows_writer_reason": writer_reason,
    }


def _error_row(pair: LiveBuildPair, image_source: Path, video_source: Path, error: str) -> Dict[str, str]:
    return {
        "pair_id": pair.pair_id,
        "category": pair.category,
        "confidence": pair.confidence,
        "image_source": str(image_source),
        "video_source": str(video_source),
        "error": error,
    }


def _ensure_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError("{0} file does not exist: {1}".format(label, path))
    if not path.is_file():
        raise ValueError("{0} path is not a file: {1}".format(label, path))


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
