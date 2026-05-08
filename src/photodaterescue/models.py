"""Core data models for PhotoDateRescue."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class ScanStatus(str, Enum):
    OK = "ok"
    REPAIRABLE = "repairable"
    HIGH_RISK = "high_risk"
    UNSUPPORTED = "unsupported"
    ERROR = "error"

@dataclass
class DiscoveredFile:
    absolute_path: Path
    relative_path: Path
    extension: str
    has_supported_extension: bool
    path_media_kind: Optional[str] = None


@dataclass
class MetadataRecord:
    width: Optional[int] = None
    height: Optional[int] = None
    file_type: Optional[str] = None
    file_type_extension: Optional[str] = None
    date_time_original: Optional[datetime] = None
    create_date: Optional[datetime] = None
    creation_date: Optional[datetime] = None
    modify_date: Optional[datetime] = None
    media_create_date: Optional[datetime] = None
    track_create_date: Optional[datetime] = None
    make: Optional[str] = None
    model: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class ScanRecord:
    absolute_path: Path
    relative_path: Path
    extension: str
    width: Optional[int]
    height: Optional[int]
    has_exif_datetime: bool
    exif_datetime: Optional[datetime]
    file_mtime: Optional[datetime]
    file_ctime: Optional[datetime]
    chosen_time_source: Optional[str]
    chosen_datetime: Optional[datetime]
    status: ScanStatus
    reason: str
    is_supported: bool
    file_type: Optional[str] = None
    file_type_extension: Optional[str] = None
    effective_extension: Optional[str] = None
    media_kind: Optional[str] = None
    error: Optional[str] = None

    def to_csv_row(self) -> Dict[str, Any]:
        row = asdict(self)
        row["relative_path"] = self.relative_path.as_posix()
        row["absolute_path"] = str(self.absolute_path)
        row["status"] = self.status.value
        row["exif_datetime"] = isoformat_or_empty(self.exif_datetime)
        row["file_mtime"] = isoformat_or_empty(self.file_mtime)
        row["file_ctime"] = isoformat_or_empty(self.file_ctime)
        row["chosen_datetime"] = isoformat_or_empty(self.chosen_datetime)
        return row

    def to_manifest_item(self) -> Dict[str, Any]:
        return {
            "relative_path": self.relative_path.as_posix(),
            "status": self.status.value,
            "reason": self.reason,
            "file_type": self.file_type,
            "file_type_extension": self.file_type_extension,
            "effective_extension": self.effective_extension,
            "media_kind": self.media_kind,
            "chosen_time_source": self.chosen_time_source,
            "chosen_datetime": isoformat_or_empty(self.chosen_datetime),
        }


@dataclass
class RepairResult:
    copied: int
    repaired: int
    failed: int
    skipped: int
    manifest_path: Path


def isoformat_or_empty(value: Optional[datetime]) -> str:
    return value.isoformat() if value else ""
