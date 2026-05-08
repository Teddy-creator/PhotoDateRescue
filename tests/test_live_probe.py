import csv
import json
import subprocess
from pathlib import Path

from photodaterescue.cli import main
from photodaterescue.live_probe import probe_live_pairs
from photodaterescue.models import MetadataRecord


class FakeClient:
    def __init__(self, payloads):
        self.payloads = payloads

    def read_metadata(self, paths, extra_tags=None):
        return {Path(path).resolve(): MetadataRecord(raw=self.payloads[Path(path).name]) for path in paths}


def test_live_probe_writes_batch_reports(tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "a.jpg")
    video = _write_file(source_root / "a.mov")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [
            _pair_row("pair-1", "paired_candidate", "high", image, video, source_root),
        ],
    )
    client = FakeClient(
        {
            "a.jpg": {"ContentIdentifier": "live-123", "MakerNoteApple": "present"},
            "a.mov": {"ContentIdentifier": "live-123", "Duration": 2.0},
        }
    )

    result = probe_live_pairs(
        pairs_csv=pairs_csv,
        source_root=source_root,
        report_dir=tmp_path / "report",
        client=client,
    )

    rows = list(csv.DictReader(result.rows_path.open(encoding="utf-8")))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.total_count == 1
    assert result.metadata_match_count == 1
    assert result.error_count == 0
    assert rows[0]["pair_id"] == "pair-1"
    assert rows[0]["apple_live_status"] == "metadata_match"
    assert rows[0]["content_identifier_match"] == "True"
    assert manifest["status_counts"]["metadata_match"] == 1


def test_live_probe_marks_missing_makernotes_as_metadata_blocked(tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "a.jpg")
    video = _write_file(source_root / "a.mov")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [_pair_row("pair-1", "paired_candidate", "high", image, video, source_root)],
    )
    client = FakeClient(
        {
            "a.jpg": {},
            "a.mov": {"ContentIdentifier": "video-only"},
        }
    )

    result = probe_live_pairs(pairs_csv, source_root, tmp_path / "report", client)
    rows = list(csv.DictReader(result.rows_path.open(encoding="utf-8")))

    assert rows[0]["apple_live_status"] == "metadata_mismatch"
    assert rows[0]["windows_writer_status"] == "metadata_blocked"
    assert rows[0]["windows_writer_reason"] == "still image lacks Apple Maker Notes"


def test_live_probe_reports_bad_pair_path(tmp_path):
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [
            {
                "pair_id": "pair-1",
                "category": "paired_candidate",
                "confidence": "high",
                "reason": "bad",
                "image_relative_path": "../escape.jpg",
                "video_relative_path": "a.mov",
            }
        ],
    )
    client = FakeClient({})

    result = probe_live_pairs(pairs_csv, tmp_path / "source", tmp_path / "report", client)
    errors = list(csv.DictReader(result.errors_path.open(encoding="utf-8")))

    assert result.error_count == 1
    assert "escapes source root" in errors[0]["error"]


def test_cli_live_probe_writes_reports(monkeypatch, tmp_path, capsys):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "a.jpg")
    video = _write_file(source_root / "a.mov")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [_pair_row("pair-1", "paired_candidate", "high", image, video, source_root)],
    )

    def fake_run(command, capture_output, check, text):
        payload = [
            {"SourceFile": str(image.resolve()), "ContentIdentifier": "live-123", "MakerNoteApple": "present"},
            {"SourceFile": str(video.resolve()), "ContentIdentifier": "live-123"},
        ]
        return subprocess.CompletedProcess(command, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr("photodaterescue.metadata.subprocess.run", fake_run)
    monkeypatch.setattr("photodaterescue.metadata.find_tool", lambda name: "exiftool")

    exit_code = main(
        [
            "live-probe",
            "--pairs-csv",
            str(pairs_csv),
            "--source-root",
            str(source_root),
            "--report",
            str(tmp_path / "report"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Live probe complete" in captured.out
    assert (tmp_path / "report" / "live-probe.csv").exists()


def _write_file(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake")
    return path


def _pair_row(pair_id: str, category: str, confidence: str, image: Path, video: Path, source_root: Path) -> dict:
    return {
        "pair_id": pair_id,
        "category": category,
        "confidence": confidence,
        "reason": "test pair",
        "image_relative_path": image.relative_to(source_root).as_posix(),
        "video_relative_path": video.relative_to(source_root).as_posix(),
        "time_delta_seconds": "0",
        "shared_identifier": "",
    }


def _write_pairs_csv(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "pair_id",
        "category",
        "confidence",
        "reason",
        "image_relative_path",
        "video_relative_path",
        "time_delta_seconds",
        "shared_identifier",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path
