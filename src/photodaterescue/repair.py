"""Copy-only repair workflow."""

from __future__ import annotations

import json
import subprocess
import shutil
from pathlib import Path
from typing import Iterable, List

from .formats import normalize_extension
from .models import RepairResult, ScanRecord, ScanStatus
from .reports import write_reports
from .scan import analyze_directory


def repair_directory(
    source: Path,
    output: Path,
    report_dir: Path,
    client,
    copy_all: bool = False,
    include_patterns: Iterable[str] | None = None,
    exclude_patterns: Iterable[str] | None = None,
) -> RepairResult:
    records = analyze_directory(
        source,
        client,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )
    output.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    repaired = 0
    failed = 0
    skipped = 0
    repaired_items = []
    copied_ok_items = []
    failed_items = []
    skipped_items = []

    for record in records:
        if record.status == ScanStatus.REPAIRABLE:
            target_relative_path = build_output_relative_path(record)
            target = output / target_relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record.absolute_path, target)
            try:
                client.write_timestamp(target, record.chosen_datetime)
            except subprocess.CalledProcessError as exc:
                failed += 1
                target.unlink(missing_ok=True)
                item = record.to_manifest_item()
                item["output_path"] = str(target)
                item["error"] = (exc.stderr or exc.stdout or str(exc)).strip()
                failed_items.append(item)
                continue
            copied += 1
            repaired += 1
            item = record.to_manifest_item()
            item["output_path"] = str(target)
            repaired_items.append(item)
        elif copy_all and record.status == ScanStatus.OK:
            target = output / record.relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(record.absolute_path, target)
            copied += 1
            item = record.to_manifest_item()
            item["output_path"] = str(target)
            copied_ok_items.append(item)
        else:
            skipped += 1
            skipped_items.append(record.to_manifest_item())

    write_reports(records, report_dir)
    manifest = {
        "source": str(source.resolve()),
        "output": str(output.resolve()),
        "copy_all": copy_all,
        "include_patterns": list(include_patterns or []),
        "exclude_patterns": list(exclude_patterns or []),
        "copied": copied,
        "repaired": repaired,
        "failed": failed,
        "skipped": skipped,
        "repaired_items": repaired_items,
        "copied_ok_items": copied_ok_items,
        "failed_items": failed_items,
        "skipped_items": skipped_items,
    }
    manifest_path = output / "_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return RepairResult(
        copied=copied,
        repaired=repaired,
        failed=failed,
        skipped=skipped,
        manifest_path=manifest_path,
    )


def build_output_relative_path(record: ScanRecord) -> Path:
    detected_suffix = normalize_detected_suffix(record.effective_extension or record.file_type_extension)
    current_suffix = record.relative_path.suffix.lower()

    if not detected_suffix:
        return record.relative_path

    if current_suffix in {".jpg", ".jpeg"} and detected_suffix == ".jpg":
        return record.relative_path

    if current_suffix == detected_suffix:
        return record.relative_path

    return record.relative_path.with_suffix(detected_suffix)


def normalize_detected_suffix(file_type_extension: str | None) -> str | None:
    return normalize_extension(file_type_extension)
