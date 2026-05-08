import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from photodaterescue.metadata import ExifToolClient, parse_exif_datetime


def test_parse_exif_datetime_parses_supported_format():
    assert parse_exif_datetime("2025:07:06 14:01:00") == datetime(2025, 7, 6, 14, 1, 0)


def test_parse_exif_datetime_ignores_timezone_suffix():
    assert parse_exif_datetime("2025:07:06 14:01:00+08:00") == datetime(2025, 7, 6, 14, 1, 0)


def test_read_metadata_parses_json_payload(monkeypatch, tmp_path):
    target = tmp_path / "sample.jpg"
    target.write_bytes(b"fake")

    def fake_run(command, capture_output, check, text):
        payload = [
            {
                "SourceFile": str(target.resolve()),
                "DateTimeOriginal": "2025:07:06 14:01:00",
                "ImageWidth": 1200,
                "ImageHeight": 2670,
            }
        ]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("photodaterescue.metadata.subprocess.run", fake_run)
    client = ExifToolClient(exiftool_path="exiftool", chunk_size=10)
    result = client.read_metadata([target])

    assert result[target.resolve()].date_time_original == datetime(2025, 7, 6, 14, 1, 0)
    assert result[target.resolve()].width == 1200


def test_read_metadata_chunks_large_path_lists(monkeypatch, tmp_path):
    paths = []
    for idx in range(5):
        path = tmp_path / "{0}.jpg".format(idx)
        path.write_bytes(b"fake")
        paths.append(path)

    calls = []

    def fake_run(command, capture_output, check, text):
        calls.append(command)
        payload = [{"SourceFile": str(path.resolve())} for path in paths if str(path) in command]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("photodaterescue.metadata.subprocess.run", fake_run)
    client = ExifToolClient(exiftool_path="exiftool", chunk_size=2)
    client.read_metadata(paths)

    assert len(calls) == 3


def test_read_metadata_accepts_extra_tags(monkeypatch, tmp_path):
    target = tmp_path / "motion.jpg"
    target.write_bytes(b"fake")
    calls = []

    def fake_run(command, capture_output, check, text):
        calls.append(command)
        payload = [{"SourceFile": str(target.resolve()), "MotionPhoto": 1}]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("photodaterescue.metadata.subprocess.run", fake_run)
    client = ExifToolClient(exiftool_path="exiftool", chunk_size=10)
    result = client.read_metadata([target], extra_tags=["MotionPhoto"])

    assert "-MotionPhoto" in calls[0]
    assert result[target.resolve()].raw["MotionPhoto"] == 1


def test_write_timestamp_targets_copy_only(monkeypatch, tmp_path):
    target = tmp_path / "copy.jpg"
    target.write_bytes(b"fake")
    calls = []

    def fake_run(command, capture_output, check, text):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("photodaterescue.metadata.subprocess.run", fake_run)
    client = ExifToolClient(exiftool_path="exiftool")
    client.write_timestamp(target, datetime(2025, 7, 6, 14, 1, 0))

    assert "-DateTimeOriginal=2025:07:06 14:01:00" in calls[0]
    assert str(target) in calls[0]


def test_build_write_timestamp_command_uses_video_tags_for_videos(tmp_path):
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"fake")
    client = ExifToolClient(exiftool_path="exiftool")

    command = client.build_write_timestamp_command(target, datetime(2025, 7, 6, 14, 1, 0))

    assert "-CreateDate=2025:07:06 06:01:00" in command
    assert "-MediaCreateDate=2025:07:06 06:01:00" in command
    assert "-TrackCreateDate=2025:07:06 06:01:00" in command
    assert "-ModifyDate=2025:07:06 14:01:00" in command
    assert "-DateTimeOriginal=2025:07:06 14:01:00" not in command


def test_read_metadata_uses_partial_stdout_even_when_exiftool_returns_nonzero(monkeypatch, tmp_path):
    good = tmp_path / "good.jpg"
    bad = tmp_path / "bad.jpg"
    good.write_bytes(b"good")
    bad.write_bytes(b"bad")

    def fake_run(command, capture_output, check, text):
        payload = [
            {
                "SourceFile": str(good.resolve()),
                "DateTimeOriginal": "2025:07:06 14:01:00",
            },
            {
                "SourceFile": str(bad.resolve()),
            },
        ]
        return subprocess.CompletedProcess(
            command,
            1,
            stdout=json.dumps(payload),
            stderr="Error: File format error - {0}".format(bad),
        )

    monkeypatch.setattr("photodaterescue.metadata.subprocess.run", fake_run)
    client = ExifToolClient(exiftool_path="exiftool", chunk_size=10)
    result = client.read_metadata([good, bad])

    assert result[good.resolve()].date_time_original == datetime(2025, 7, 6, 14, 1, 0)
    assert result[bad.resolve()].date_time_original is None


def test_read_metadata_keeps_real_file_type_information(monkeypatch, tmp_path):
    target = tmp_path / "sample.bin"
    target.write_bytes(b"fake")

    def fake_run(command, capture_output, check, text):
        payload = [
            {
                "SourceFile": str(target.resolve()),
                "FileType": "HEIF",
                "FileTypeExtension": "heif",
            }
        ]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("photodaterescue.metadata.subprocess.run", fake_run)
    client = ExifToolClient(exiftool_path="exiftool", chunk_size=10)
    result = client.read_metadata([target])

    assert result[target.resolve()].file_type == "HEIF"
    assert result[target.resolve()].file_type_extension == "heif"


def test_read_metadata_parses_video_time_fields(monkeypatch, tmp_path):
    target = tmp_path / "clip.mp4"
    target.write_bytes(b"fake")

    def fake_run(command, capture_output, check, text):
        payload = [
            {
                "SourceFile": str(target.resolve()),
                "FileType": "MP4",
                "FileTypeExtension": "mp4",
                "CreateDate": "2025:07:06 14:01:00",
                "MediaCreateDate": "2025:07:06 14:01:01",
                "TrackCreateDate": "2025:07:06 14:01:02",
                "CreationDate": "2025:07:06 14:01:03+08:00",
            }
        ]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("photodaterescue.metadata.subprocess.run", fake_run)
    client = ExifToolClient(exiftool_path="exiftool", chunk_size=10)
    result = client.read_metadata([target])[target.resolve()]

    assert result.file_type_extension == "mp4"
    assert result.create_date == datetime(2025, 7, 6, 14, 1, 0)
    assert result.media_create_date == datetime(2025, 7, 6, 14, 1, 1)
    assert result.track_create_date == datetime(2025, 7, 6, 14, 1, 2)
    assert result.creation_date == datetime(2025, 7, 6, 14, 1, 3)
