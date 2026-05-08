from datetime import datetime
from pathlib import Path

from photodaterescue.decision import build_scan_record, choose_best_timestamp
from photodaterescue.formats import MEDIA_KIND_VIDEO
from photodaterescue.models import DiscoveredFile, MetadataRecord, ScanStatus


def make_discovered(name="sample.jpg", supported=True):
    path = Path("/tmp") / name
    return DiscoveredFile(
        absolute_path=path,
        relative_path=Path(name),
        extension=path.suffix.lower(),
        has_supported_extension=supported,
    )


def test_choose_timestamp_prefers_exif():
    embedded = datetime(2024, 1, 2, 3, 4, 5)
    source, value = choose_best_timestamp(embedded, datetime(2025, 1, 1, 0, 0, 0), None)
    assert source == "exif"
    assert value == embedded


def test_choose_timestamp_falls_back_to_mtime_then_ctime():
    mtime = datetime(2025, 1, 1, 0, 0, 0)
    ctime = datetime(2024, 1, 1, 0, 0, 0)
    source, value = choose_best_timestamp(None, mtime, ctime)
    assert source == "file_mtime"
    assert value == mtime


def test_build_scan_record_marks_file_high_risk_when_no_usable_time_exists():
    record = build_scan_record(
        discovered=make_discovered(),
        metadata=MetadataRecord(),
        file_mtime=None,
        file_ctime=None,
    )
    assert record.status == ScanStatus.HIGH_RISK


def test_build_scan_record_marks_existing_exif_as_ok():
    record = build_scan_record(
        discovered=make_discovered(),
        metadata=MetadataRecord(date_time_original=datetime(2025, 7, 6, 14, 1, 0)),
        file_mtime=datetime(2026, 1, 1, 0, 0, 0),
        file_ctime=datetime(2026, 1, 1, 0, 0, 0),
    )
    assert record.status == ScanStatus.OK
    assert record.chosen_time_source == "exif"


def test_build_scan_record_marks_supported_suffix_with_unsupported_real_type_as_unsupported():
    record = build_scan_record(
        discovered=make_discovered("fake.jpg", supported=True),
        metadata=MetadataRecord(file_type_extension="txt"),
        file_mtime=datetime(2026, 1, 1, 0, 0, 0),
        file_ctime=datetime(2026, 1, 1, 0, 0, 0),
    )

    assert record.status == ScanStatus.UNSUPPORTED
    assert record.reason == "Unsupported real file container"


def test_build_scan_record_accepts_unknown_suffix_when_real_type_is_supported():
    record = build_scan_record(
        discovered=make_discovered("rescued.bin", supported=False),
        metadata=MetadataRecord(file_type_extension="heif"),
        file_mtime=datetime(2026, 1, 1, 0, 0, 0),
        file_ctime=datetime(2026, 1, 1, 0, 0, 0),
    )

    assert record.status == ScanStatus.REPAIRABLE
    assert record.effective_extension == ".heif"
    assert record.media_kind == "image"


def test_build_scan_record_marks_video_with_embedded_time_as_ok():
    record = build_scan_record(
        discovered=make_discovered("clip.mp4", supported=True),
        metadata=MetadataRecord(
            file_type_extension="mp4",
            create_date=datetime(2025, 7, 6, 14, 1, 0),
        ),
        file_mtime=datetime(2026, 1, 1, 0, 0, 0),
        file_ctime=datetime(2026, 1, 1, 0, 0, 0),
    )

    assert record.status == ScanStatus.OK
    assert record.media_kind == MEDIA_KIND_VIDEO
    assert record.chosen_time_source == "create_date"


def test_build_scan_record_marks_video_repairable_from_file_time():
    record = build_scan_record(
        discovered=make_discovered("clip.mov", supported=True),
        metadata=MetadataRecord(file_type_extension="mov"),
        file_mtime=datetime(2026, 1, 1, 0, 0, 0),
        file_ctime=datetime(2025, 12, 31, 23, 59, 59),
    )

    assert record.status == ScanStatus.REPAIRABLE
    assert record.media_kind == MEDIA_KIND_VIDEO
    assert record.chosen_time_source == "file_mtime"
