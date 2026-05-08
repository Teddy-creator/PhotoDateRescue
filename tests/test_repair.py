import json
import subprocess
from pathlib import Path

import pytest

from photodaterescue.models import MetadataRecord, ScanRecord, ScanStatus
from photodaterescue.repair import repair_directory
from tests.factories import create_image
from tests.test_scan import FakeExifToolClient


def test_repair_copies_repairable_files_and_preserves_relative_paths(sample_root):
    image = create_image(sample_root / "DCIM" / "tieba" / "example.jpg")
    client = FakeExifToolClient({image.resolve(): MetadataRecord()})
    writes = []
    client.write_timestamp = lambda path, timestamp: writes.append((path, timestamp))

    output_dir = sample_root.parent / "output"
    report_dir = sample_root.parent / "report"
    result = repair_directory(sample_root, output_dir, report_dir, client)

    assert (output_dir / "DCIM/tieba/example.jpg").exists()
    assert result.repaired == 1
    assert writes


def test_repair_skips_high_risk_files_and_writes_manifest(sample_root):
    create_image(sample_root / "example.jpg")
    client = FakeExifToolClient({})
    output_dir = sample_root.parent / "output"
    report_dir = sample_root.parent / "report"

    high_risk_record = ScanRecord(
        absolute_path=sample_root / "example.jpg",
        relative_path=Path("example.jpg"),
        extension=".jpg",
        width=32,
        height=32,
        has_exif_datetime=False,
        exif_datetime=None,
        file_mtime=None,
        file_ctime=None,
        chosen_time_source=None,
        chosen_datetime=None,
        status=ScanStatus.HIGH_RISK,
        reason="No trustworthy timestamp source found",
        is_supported=True,
        effective_extension=".jpg",
    )

    from photodaterescue import repair as repair_module

    original_analyze_directory = repair_module.analyze_directory
    repair_module.analyze_directory = lambda source, exif_client, **kwargs: [high_risk_record]
    try:
        result = repair_directory(sample_root, output_dir, report_dir, client)
    finally:
        repair_module.analyze_directory = original_analyze_directory

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["repaired"] == 0
    assert manifest["copied"] == 0
    assert manifest["failed"] == 0
    assert manifest["skipped"] == 1
    assert manifest["skipped_items"][0]["status"] == "high_risk"


def test_repair_writes_timestamp_to_copy_not_source(sample_root):
    image = create_image(sample_root / "copy.jpg")
    original_source_bytes = image.read_bytes()
    writes = []
    client = FakeExifToolClient({image.resolve(): MetadataRecord()})
    client.write_timestamp = lambda path, timestamp: writes.append((path, timestamp))

    output_dir = sample_root.parent / "output"
    report_dir = sample_root.parent / "report"
    repair_directory(sample_root, output_dir, report_dir, client)

    assert image.read_bytes() == original_source_bytes
    assert writes[0][0] == output_dir / "copy.jpg"


def test_repair_respects_exclude_patterns_and_records_them_in_manifest(sample_root):
    keep_image = create_image(sample_root / "Pictures" / "WeiXin" / "keep.jpg")
    create_image(sample_root / "Pictures" / ".thumbnails" / "skip.jpg")
    client = FakeExifToolClient({keep_image.resolve(): MetadataRecord()})
    client.write_timestamp = lambda path, timestamp: None

    output_dir = sample_root.parent / "output"
    report_dir = sample_root.parent / "report"
    result = repair_directory(
        sample_root,
        output_dir,
        report_dir,
        client,
        exclude_patterns=["Pictures/.thumbnails"],
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert (output_dir / "Pictures/WeiXin/keep.jpg").exists()
    assert not (output_dir / "Pictures/.thumbnails/skip.jpg").exists()
    assert manifest["exclude_patterns"] == ["Pictures/.thumbnails"]


@pytest.mark.parametrize(
    ("detected_extension", "expected_output_name"),
    [
        ("PNG", "weird.png"),
        ("WEBP", "weird.webp"),
        ("HEIC", "weird.heic"),
        ("HEIF", "weird.heif"),
    ],
)
def test_repair_renames_output_when_real_file_type_differs_from_suffix(
    sample_root,
    detected_extension,
    expected_output_name,
):
    image = create_image(sample_root / "DCIM" / "Alipay" / "weird.jpg")
    client = FakeExifToolClient(
        {
            image.resolve(): MetadataRecord(
                file_type=detected_extension,
                file_type_extension=detected_extension,
            )
        }
    )
    writes = []
    client.write_timestamp = lambda path, timestamp: writes.append((path, timestamp))

    output_dir = sample_root.parent / "output"
    report_dir = sample_root.parent / "report"
    repair_directory(sample_root, output_dir, report_dir, client)

    expected_output = output_dir / "DCIM" / "Alipay" / expected_output_name
    assert expected_output.exists()
    assert not (output_dir / "DCIM/Alipay/weird.jpg").exists()
    assert writes[0][0] == expected_output


def test_repair_records_write_failures_and_continues(sample_root):
    good = create_image(sample_root / "good.jpg")
    bad = create_image(sample_root / "bad.jpg")
    client = FakeExifToolClient(
        {
            good.resolve(): MetadataRecord(),
            bad.resolve(): MetadataRecord(),
        }
    )

    def fake_write_timestamp(path, timestamp):
        if path.name == "bad.jpg":
            raise subprocess.CalledProcessError(
                1,
                ["exiftool", str(path)],
                stderr="simulated write failure",
            )

    client.write_timestamp = fake_write_timestamp

    output_dir = sample_root.parent / "output"
    report_dir = sample_root.parent / "report"
    result = repair_directory(sample_root, output_dir, report_dir, client)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.repaired == 1
    assert result.failed == 1
    assert (output_dir / "good.jpg").exists()
    assert not (output_dir / "bad.jpg").exists()
    assert manifest["failed"] == 1
    assert manifest["failed_items"][0]["error"] == "simulated write failure"


def test_repair_copies_repairable_video_files(sample_root):
    clip = sample_root / "DCIM" / "Camera" / "clip.mp4"
    clip.parent.mkdir(parents=True, exist_ok=True)
    clip.write_bytes(b"fake-video")
    client = FakeExifToolClient(
        {
            clip.resolve(): MetadataRecord(
                file_type_extension="mp4",
            )
        }
    )
    writes = []
    client.write_timestamp = lambda path, timestamp: writes.append((path, timestamp))

    output_dir = sample_root.parent / "output"
    report_dir = sample_root.parent / "report"
    result = repair_directory(sample_root, output_dir, report_dir, client)

    assert result.repaired == 1
    assert (output_dir / "DCIM/Camera/clip.mp4").exists()
    assert writes[0][0] == output_dir / "DCIM/Camera/clip.mp4"
