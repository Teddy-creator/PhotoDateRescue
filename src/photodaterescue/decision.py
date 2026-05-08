"""Timestamp selection and scan classification."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from .formats import MEDIA_KIND_VIDEO, resolve_media_kind, resolve_supported_extension
from .models import DiscoveredFile, MetadataRecord, ScanRecord, ScanStatus


def choose_embedded_timestamp(
    metadata: MetadataRecord,
    media_kind: Optional[str],
) -> Tuple[Optional[str], Optional[datetime]]:
    if media_kind == MEDIA_KIND_VIDEO:
        candidates = [
            ("create_date", metadata.create_date),
            ("creation_date", metadata.creation_date),
            ("media_create_date", metadata.media_create_date),
            ("track_create_date", metadata.track_create_date),
        ]
    else:
        candidates = [
            ("exif", metadata.date_time_original),
            ("create_date", metadata.create_date),
        ]

    for source, value in candidates:
        if value:
            return source, value
    return None, None


def choose_best_timestamp(
    embedded_datetime: Optional[datetime],
    file_mtime: Optional[datetime],
    file_ctime: Optional[datetime],
    embedded_source: Optional[str] = "exif",
) -> Tuple[Optional[str], Optional[datetime]]:
    if embedded_datetime:
        return embedded_source, embedded_datetime
    if file_mtime:
        return "file_mtime", file_mtime
    if file_ctime:
        return "file_ctime", file_ctime
    return None, None


def build_scan_record(
    discovered: DiscoveredFile,
    metadata: MetadataRecord,
    file_mtime: Optional[datetime],
    file_ctime: Optional[datetime],
    error: Optional[str] = None,
) -> ScanRecord:
    media_kind = resolve_media_kind(
        path_extension=discovered.extension,
        metadata_extension=metadata.file_type_extension,
    )
    embedded_source, embedded_datetime = choose_embedded_timestamp(metadata, media_kind)
    chosen_source, chosen_datetime = choose_best_timestamp(
        embedded_datetime=embedded_datetime,
        file_mtime=file_mtime,
        file_ctime=file_ctime,
        embedded_source=embedded_source,
    )
    effective_extension = resolve_supported_extension(
        path_extension=discovered.extension,
        metadata_extension=metadata.file_type_extension,
    )
    is_supported = effective_extension is not None and media_kind is not None

    if not is_supported:
        reason = (
            "Unsupported real file container"
            if metadata.file_type_extension
            else "Unsupported file extension"
        )
        return ScanRecord(
            absolute_path=discovered.absolute_path,
            relative_path=discovered.relative_path,
            extension=discovered.extension,
            width=metadata.width,
            height=metadata.height,
            file_type=metadata.file_type,
            file_type_extension=metadata.file_type_extension,
            effective_extension=effective_extension,
            media_kind=media_kind,
            has_exif_datetime=False,
            exif_datetime=None,
            file_mtime=file_mtime,
            file_ctime=file_ctime,
            chosen_time_source=None,
            chosen_datetime=None,
            status=ScanStatus.UNSUPPORTED,
            reason=reason,
            is_supported=False,
        )

    if error is not None:
        return ScanRecord(
            absolute_path=discovered.absolute_path,
            relative_path=discovered.relative_path,
            extension=discovered.extension,
            width=metadata.width,
            height=metadata.height,
            file_type=metadata.file_type,
            file_type_extension=metadata.file_type_extension,
            effective_extension=effective_extension,
            media_kind=media_kind,
            has_exif_datetime=bool(embedded_datetime),
            exif_datetime=embedded_datetime,
            file_mtime=file_mtime,
            file_ctime=file_ctime,
            chosen_time_source=None,
            chosen_datetime=None,
            status=ScanStatus.ERROR,
            reason="Metadata analysis failed",
            is_supported=True,
            error=error,
        )

    if embedded_datetime:
        return ScanRecord(
            absolute_path=discovered.absolute_path,
            relative_path=discovered.relative_path,
            extension=discovered.extension,
            width=metadata.width,
            height=metadata.height,
            file_type=metadata.file_type,
            file_type_extension=metadata.file_type_extension,
            effective_extension=effective_extension,
            media_kind=media_kind,
            has_exif_datetime=True,
            exif_datetime=embedded_datetime,
            file_mtime=file_mtime,
            file_ctime=file_ctime,
            chosen_time_source=embedded_source,
            chosen_datetime=embedded_datetime,
            status=ScanStatus.OK,
            reason="Embedded timestamp already available",
            is_supported=True,
        )

    if chosen_datetime and chosen_source:
        return ScanRecord(
            absolute_path=discovered.absolute_path,
            relative_path=discovered.relative_path,
            extension=discovered.extension,
            width=metadata.width,
            height=metadata.height,
            file_type=metadata.file_type,
            file_type_extension=metadata.file_type_extension,
            effective_extension=effective_extension,
            media_kind=media_kind,
            has_exif_datetime=False,
            exif_datetime=None,
            file_mtime=file_mtime,
            file_ctime=file_ctime,
            chosen_time_source=chosen_source,
            chosen_datetime=chosen_datetime,
            status=ScanStatus.REPAIRABLE,
            reason="Missing embedded timestamp, fallback available",
            is_supported=True,
        )

    return ScanRecord(
        absolute_path=discovered.absolute_path,
        relative_path=discovered.relative_path,
        extension=discovered.extension,
        width=metadata.width,
        height=metadata.height,
        file_type=metadata.file_type,
        file_type_extension=metadata.file_type_extension,
        effective_extension=effective_extension,
        media_kind=media_kind,
        has_exif_datetime=False,
        exif_datetime=None,
        file_mtime=file_mtime,
        file_ctime=file_ctime,
        chosen_time_source=None,
        chosen_datetime=None,
        status=ScanStatus.HIGH_RISK,
        reason="No trustworthy timestamp source found",
        is_supported=True,
    )
