"""Shared analysis pipeline used by scan and repair commands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from .decision import build_scan_record
from .discovery import discover_files
from .metadata import ExifToolClient
from .models import MetadataRecord, ScanRecord


def analyze_directory(
    root: Path,
    client: ExifToolClient,
    include_patterns: Iterable[str] | None = None,
    exclude_patterns: Iterable[str] | None = None,
) -> List[ScanRecord]:
    discovered_files = discover_files(
        root,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )
    supported_paths = [item.absolute_path.resolve() for item in discovered_files]

    metadata_by_path = {}
    metadata_error: Optional[str] = None
    if supported_paths:
        try:
            metadata_by_path = client.read_metadata(supported_paths)
        except Exception as exc:  # pragma: no cover - behavior validated by higher-level tests
            metadata_error = str(exc)

    records = []
    for discovered in discovered_files:
        stat = discovered.absolute_path.stat()
        file_mtime = datetime.fromtimestamp(stat.st_mtime)
        file_ctime = datetime.fromtimestamp(stat.st_ctime)
        metadata = metadata_by_path.get(discovered.absolute_path.resolve(), MetadataRecord(raw={}))
        record = build_scan_record(
            discovered=discovered,
            metadata=metadata,
            file_mtime=file_mtime,
            file_ctime=file_ctime,
            error=metadata_error if discovered.has_supported_extension and metadata_error else None,
        )
        records.append(record)
    return records
