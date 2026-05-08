"""Metadata read/write helpers backed by exiftool."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence
from zoneinfo import ZoneInfo

from .formats import MEDIA_KIND_VIDEO, media_kind_from_extension
from .models import MetadataRecord
from .tools import find_tool


TIME_FORMAT = "%Y:%m:%d %H:%M:%S"
LOCAL_TIME_ZONE = ZoneInfo("Asia/Shanghai")
READ_TAGS = [
    "FileType",
    "FileTypeExtension",
    "DateTimeOriginal",
    "CreateDate",
    "CreationDate",
    "ModifyDate",
    "MediaCreateDate",
    "TrackCreateDate",
    "ImageWidth",
    "ImageHeight",
    "Make",
    "Model",
]


def parse_exif_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    cleaned = value.strip()
    if len(cleaned) >= 19:
        cleaned = cleaned[:19]
    try:
        return datetime.strptime(cleaned, TIME_FORMAT)
    except ValueError:
        return None


class ExifToolMissingError(RuntimeError):
    """Raised when exiftool is unavailable."""


@dataclass
class ExifToolClient:
    exiftool_path: Optional[str] = None
    chunk_size: int = 100

    def __post_init__(self) -> None:
        if self.exiftool_path is None:
            self.exiftool_path = find_tool("exiftool")

    def is_available(self) -> bool:
        return bool(self.exiftool_path)

    def _ensure_available(self) -> str:
        if not self.exiftool_path:
            raise ExifToolMissingError("exiftool is not available on PATH")
        return self.exiftool_path

    def read_metadata(
        self,
        paths: Sequence[Path],
        extra_tags: Iterable[str] | None = None,
    ) -> Dict[Path, MetadataRecord]:
        exiftool = self._ensure_available()
        if not paths:
            return {}

        read_tags = _dedupe_tags([*READ_TAGS, *(extra_tags or [])])
        result: Dict[Path, MetadataRecord] = {}
        for start in range(0, len(paths), self.chunk_size):
            chunk = paths[start : start + self.chunk_size]
            command = [exiftool, "-j", "-n"]
            command.extend("-{0}".format(tag) for tag in read_tags)
            command.extend(str(path) for path in chunk)
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
            )
            payload = json.loads(completed.stdout or "[]")
            for raw in payload:
                source_file = raw.get("SourceFile")
                if not source_file:
                    continue
                path = Path(source_file).resolve()
                result[path] = self._record_from_payload(raw)

        for path in paths:
            result.setdefault(path.resolve(), MetadataRecord(raw={}))
        return result

    def write_timestamp(self, path: Path, timestamp: datetime) -> None:
        command = self.build_write_timestamp_command(path, timestamp)
        subprocess.run(command, capture_output=True, check=True, text=True)

    def build_write_timestamp_command(self, path: Path, timestamp: datetime) -> List[str]:
        exiftool = self._ensure_available()
        timestamp_value = timestamp.strftime(TIME_FORMAT)
        media_kind = media_kind_from_extension(path.suffix)
        if media_kind == MEDIA_KIND_VIDEO:
            quicktime_value = _format_quicktime_utc(timestamp)
            return [
                exiftool,
                "-overwrite_original",
                "-CreateDate={0}".format(quicktime_value),
                "-MediaCreateDate={0}".format(quicktime_value),
                "-TrackCreateDate={0}".format(quicktime_value),
                "-ModifyDate={0}".format(timestamp_value),
                str(path),
            ]

        return [
            exiftool,
            "-overwrite_original",
            "-DateTimeOriginal={0}".format(timestamp_value),
            "-CreateDate={0}".format(timestamp_value),
            "-ModifyDate={0}".format(timestamp_value),
            str(path),
        ]

    def _record_from_payload(self, raw: Dict[str, Any]) -> MetadataRecord:
        width = _to_int(raw.get("ImageWidth"))
        height = _to_int(raw.get("ImageHeight"))
        return MetadataRecord(
            width=width,
            height=height,
            file_type=raw.get("FileType"),
            file_type_extension=raw.get("FileTypeExtension"),
            date_time_original=parse_exif_datetime(raw.get("DateTimeOriginal")),
            create_date=parse_exif_datetime(raw.get("CreateDate")),
            creation_date=parse_exif_datetime(raw.get("CreationDate")),
            modify_date=parse_exif_datetime(raw.get("ModifyDate")),
            media_create_date=parse_exif_datetime(raw.get("MediaCreateDate")),
            track_create_date=parse_exif_datetime(raw.get("TrackCreateDate")),
            make=raw.get("Make"),
            model=raw.get("Model"),
            raw=raw,
        )


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_quicktime_utc(value: datetime) -> str:
    aware = value if value.tzinfo else value.replace(tzinfo=LOCAL_TIME_ZONE)
    return aware.astimezone(timezone.utc).strftime(TIME_FORMAT)


def _dedupe_tags(tags: Iterable[str]) -> List[str]:
    result = []
    seen = set()
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        result.append(tag)
    return result
