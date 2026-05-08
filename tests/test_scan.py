from datetime import datetime
from pathlib import Path

from photodaterescue.metadata import ExifToolClient
from photodaterescue.models import MetadataRecord, ScanStatus
from photodaterescue.scan import analyze_directory
from tests.factories import create_image


class FakeExifToolClient(ExifToolClient):
    def __init__(self, mapping):
        super().__init__(exiftool_path="exiftool")
        self.mapping = mapping

    def read_metadata(self, paths):
        return {path.resolve(): self.mapping.get(path.resolve(), MetadataRecord(raw={})) for path in paths}


def test_scan_marks_file_high_risk_when_no_usable_time_exists(sample_root, monkeypatch):
    image = create_image(sample_root / "orphan.jpg")
    stat = image.stat()
    monkeypatch.setattr("photodaterescue.scan.datetime", FrozenDateTimeModule(stat.st_mtime, stat.st_ctime))
    client = FakeExifToolClient({image.resolve(): MetadataRecord()})

    records = analyze_directory(sample_root, client)

    assert records[0].status == ScanStatus.REPAIRABLE


def test_scan_marks_exif_files_as_ok(sample_root):
    image = create_image(sample_root / "camera.jpg")
    client = FakeExifToolClient(
        {
            image.resolve(): MetadataRecord(
                date_time_original=datetime(2025, 7, 6, 14, 1, 0),
                width=32,
                height=32,
            )
        }
    )

    records = analyze_directory(sample_root, client)

    assert records[0].status == ScanStatus.OK
    assert records[0].chosen_time_source == "exif"


def test_scan_marks_video_files_as_ok_when_embedded_video_time_exists(sample_root):
    clip = sample_root / "clip.mp4"
    clip.write_bytes(b"fake-video")
    client = FakeExifToolClient(
        {
            clip.resolve(): MetadataRecord(
                file_type_extension="mp4",
                create_date=datetime(2025, 7, 6, 14, 1, 0),
            )
        }
    )

    records = analyze_directory(sample_root, client)

    assert records[0].status == ScanStatus.OK
    assert records[0].media_kind == "video"
    assert records[0].chosen_time_source == "create_date"


class FrozenDateTimeModule:
    def __init__(self, mtime, ctime):
        self._mtime = datetime.fromtimestamp(mtime)
        self._ctime = datetime.fromtimestamp(ctime)

    def fromtimestamp(self, timestamp):
        if timestamp == self._mtime.timestamp():
            return self._mtime
        return self._ctime
