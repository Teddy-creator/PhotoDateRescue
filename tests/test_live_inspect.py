from pathlib import Path

import json
import subprocess

from photodaterescue.cli import main
from photodaterescue.live_inspect import inspect_live_pair
from photodaterescue.models import MetadataRecord


class FakeClient:
    def __init__(self, payloads):
        self.payloads = payloads
        self.extra_tags = None

    def read_metadata(self, paths, extra_tags=None):
        self.extra_tags = list(extra_tags or [])
        return {Path(path).resolve(): MetadataRecord(raw=self.payloads[Path(path).name]) for path in paths}


def test_live_inspect_reports_matching_content_identifier(tmp_path):
    image = tmp_path / "IMG_001.jpg"
    video = tmp_path / "IMG_001.mov"
    image.write_bytes(b"image")
    video.write_bytes(b"video")
    client = FakeClient(
        {
            "IMG_001.jpg": {
                "ContentIdentifier": "live-123",
                "MakerNoteApple": "present",
                "ImageWidth": 1200,
                "ImageHeight": 1600,
            },
            "IMG_001.mov": {
                "ContentIdentifier": "live-123",
                "ImageWidth": 1200,
                "ImageHeight": 1600,
                "Duration": 2.5,
            },
        }
    )

    result = inspect_live_pair(image, video, client)

    assert result["apple_live_status"] == "metadata_match"
    assert result["content_identifier_match"] is True
    assert result["image"]["content_identifier"] == "live-123"
    assert result["video"]["content_identifier"] == "live-123"
    assert result["image"]["apple_makernotes_present"] is True
    assert result["video"]["duration"] == 2.5
    assert "ContentIdentifier" in client.extra_tags


def test_live_inspect_reports_pair_package_when_identifiers_missing(tmp_path):
    image = tmp_path / "IMG_001.jpg"
    video = tmp_path / "IMG_001.mov"
    image.write_bytes(b"image")
    video.write_bytes(b"video")
    client = FakeClient(
        {
            "IMG_001.jpg": {"ImageWidth": 1200, "ImageHeight": 1600},
            "IMG_001.mov": {"Duration": 1.8},
        }
    )

    result = inspect_live_pair(image, video, client)

    assert result["apple_live_status"] == "no_live_metadata"
    assert result["content_identifier_match"] is False
    assert result["image"]["content_identifier"] is None
    assert result["video"]["content_identifier"] is None
    assert result["import_validation_status"] == "not_tested"


def test_live_inspect_reports_mismatched_identifiers(tmp_path):
    image = tmp_path / "IMG_001.jpg"
    video = tmp_path / "IMG_001.mov"
    image.write_bytes(b"image")
    video.write_bytes(b"video")
    client = FakeClient(
        {
            "IMG_001.jpg": {"ContentIdentifier": "image-id"},
            "IMG_001.mov": {"ContentIdentifier": "video-id"},
        }
    )

    result = inspect_live_pair(image, video, client)

    assert result["apple_live_status"] == "metadata_mismatch"
    assert result["content_identifier_match"] is False


def test_cli_live_inspect_prints_json(monkeypatch, tmp_path, capsys):
    image = tmp_path / "IMG_001.jpg"
    video = tmp_path / "IMG_001.mov"
    image.write_bytes(b"image")
    video.write_bytes(b"video")

    def fake_run(command, capture_output, check, text):
        payload = [
            {"SourceFile": str(image.resolve()), "ContentIdentifier": "live-123"},
            {"SourceFile": str(video.resolve()), "ContentIdentifier": "live-123"},
        ]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("photodaterescue.metadata.subprocess.run", fake_run)
    monkeypatch.setattr("photodaterescue.metadata.find_tool", lambda name: "exiftool")

    exit_code = main(["live-inspect", "--image", str(image), "--video", str(video)])
    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert exit_code == 0
    assert result["apple_live_status"] == "metadata_match"


def test_cli_live_inspect_reports_missing_file_without_traceback(tmp_path, capsys):
    exit_code = main(
        [
            "live-inspect",
            "--image",
            str(tmp_path / "missing.jpg"),
            "--video",
            str(tmp_path / "missing.mov"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "file does not exist" in captured.out
