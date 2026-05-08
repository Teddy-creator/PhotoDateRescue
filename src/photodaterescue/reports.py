"""Report generation helpers."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

from .models import ScanRecord, ScanStatus


FILES_CSV_FIELDS = [
    "relative_path",
    "absolute_path",
    "extension",
    "media_kind",
    "width",
    "height",
    "file_type",
    "file_type_extension",
    "effective_extension",
    "has_exif_datetime",
    "exif_datetime",
    "file_mtime",
    "file_ctime",
    "chosen_time_source",
    "chosen_datetime",
    "status",
    "reason",
    "is_supported",
    "error",
]


def write_reports(records: List[ScanRecord], report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(records)
    (report_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    _write_csv(report_dir / "files.csv", records)
    high_risk_records = [record for record in records if record.status == ScanStatus.HIGH_RISK]
    _write_csv(report_dir / "high_risk.csv", high_risk_records)


def build_summary(records: List[ScanRecord]) -> Dict[str, object]:
    status_counts = Counter(record.status.value for record in records)
    media_kind_counts = Counter((record.media_kind or "unknown") for record in records)
    by_directory = defaultdict(Counter)
    for record in records:
        parent = record.relative_path.parent.as_posix() or "."
        by_directory[parent][record.status.value] += 1

    return {
        "total_files": len(records),
        "status_counts": dict(status_counts),
        "media_kind_counts": dict(media_kind_counts),
        "directories": {
            path: dict(counter)
            for path, counter in sorted(by_directory.items())
        },
    }


def _write_csv(path: Path, records: List[ScanRecord]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FILES_CSV_FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow(record.to_csv_row())
