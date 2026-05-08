import csv
import json
from pathlib import Path

import pytest

from photodaterescue.live_build import build_live_photos
from photodaterescue.cli import main


def test_live_build_dry_run_plans_eligible_pairs_without_copying(tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "DCIM/Camera/IMG_001.jpg", "image")
    video = _write_file(source_root / "DCIM/Camera/IMG_001.mp4", "video")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [
            _pair_row("pair-1", "paired_candidate", "medium", image, video, source_root),
        ],
    )
    backend_calls = []

    result = build_live_photos(
        pairs_csv=pairs_csv,
        source_root=source_root,
        output=tmp_path / "out",
        report_dir=tmp_path / "report",
        dry_run=True,
        backend_runner=lambda image_path, video_path, makelive_path: backend_calls.append((image_path, video_path)),
    )

    rows = list(csv.DictReader(result.rows_path.open(encoding="utf-8")))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.planned_count == 1
    assert result.built_count == 0
    assert backend_calls == []
    assert rows[0]["status"] == "planned"
    assert rows[0]["dry_run"] == "True"
    assert not (tmp_path / "out" / "pair-1").exists()
    assert manifest["planned_count"] == 1


def test_live_build_copies_to_pair_folder_and_invokes_backend(tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "DCIM/Camera/IMG_001.jpg", "image")
    video = _write_file(source_root / "DCIM/Camera/IMG_001.mp4", "video")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [
            _pair_row("pair-1", "paired_candidate", "high", image, video, source_root),
        ],
    )
    backend_calls = []

    result = build_live_photos(
        pairs_csv=pairs_csv,
        source_root=source_root,
        output=tmp_path / "out",
        report_dir=tmp_path / "report",
        makelive_path="/usr/local/bin/makelive",
        backend_runner=lambda image_path, video_path, makelive_path: backend_calls.append(
            (image_path, video_path, makelive_path)
        ),
    )

    output_image = tmp_path / "out" / "pair-1" / "IMG_001.jpg"
    output_video = tmp_path / "out" / "pair-1" / "IMG_001.mp4"
    rows = list(csv.DictReader(result.rows_path.open(encoding="utf-8")))

    assert result.built_count == 1
    assert result.planned_count == 1
    assert output_image.read_text(encoding="utf-8") == "image"
    assert output_video.read_text(encoding="utf-8") == "video"
    assert backend_calls == [(output_image, output_video, "/usr/local/bin/makelive")]
    assert rows[0]["status"] == "built"
    assert image.read_text(encoding="utf-8") == "image"
    assert video.read_text(encoding="utf-8") == "video"


def test_live_build_portable_pair_writes_pair_manifest_without_backend(tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "DCIM/Camera/IMG_001.jpg", "image")
    video = _write_file(source_root / "DCIM/Camera/IMG_001.mov", "video")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [
            _pair_row("pair-1", "paired_candidate", "high", image, video, source_root),
        ],
    )
    backend_calls = []

    result = build_live_photos(
        pairs_csv=pairs_csv,
        source_root=source_root,
        output=tmp_path / "out",
        report_dir=tmp_path / "report",
        backend="portable-pair",
        backend_runner=lambda image_path, video_path, makelive_path: backend_calls.append((image_path, video_path)),
    )

    output_image = tmp_path / "out" / "pair-1" / "IMG_001.jpg"
    output_video = tmp_path / "out" / "pair-1" / "IMG_001.mov"
    pair_manifest = tmp_path / "out" / "pair-1" / "pair.json"
    rows = list(csv.DictReader(result.rows_path.open(encoding="utf-8")))
    manifest = json.loads(pair_manifest.read_text(encoding="utf-8"))

    assert result.built_count == 1
    assert backend_calls == []
    assert output_image.read_text(encoding="utf-8") == "image"
    assert output_video.read_text(encoding="utf-8") == "video"
    assert rows[0]["status"] == "built_pair"
    assert rows[0]["backend"] == "portable-pair"
    assert manifest["pair_id"] == "pair-1"
    assert manifest["apple_live_status"] == "not_attempted"
    assert manifest["import_validation_status"] == "not_tested"
    assert manifest["note"] == "Portable pair package only; Apple Photos Live Photo recognition is not guaranteed."


def test_live_build_skips_uncertain_pairs_by_default(tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "a.jpg", "image")
    video = _write_file(source_root / "a.mp4", "video")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [_pair_row("pair-1", "uncertain_candidate", "low", image, video, source_root)],
    )

    result = build_live_photos(pairs_csv, source_root, tmp_path / "out", tmp_path / "report")
    rows = list(csv.DictReader(result.rows_path.open(encoding="utf-8")))

    assert result.skipped_count == 1
    assert rows[0]["status"] == "skipped"
    assert "Skipped category uncertain_candidate" in rows[0]["reason"]


def test_live_build_can_include_uncertain_pairs_when_explicit(tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "a.jpg", "image")
    video = _write_file(source_root / "a.mp4", "video")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [_pair_row("pair-1", "uncertain_candidate", "low", image, video, source_root)],
    )
    calls = []

    result = build_live_photos(
        pairs_csv,
        source_root,
        tmp_path / "out",
        tmp_path / "report",
        include_uncertain=True,
        backend_runner=lambda image_path, video_path, makelive_path: calls.append((image_path, video_path)),
    )

    assert result.built_count == 1
    assert calls


def test_live_build_reports_missing_source_files(tmp_path):
    source_root = tmp_path / "source"
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [
            {
                "pair_id": "pair-1",
                "category": "paired_candidate",
                "confidence": "high",
                "reason": "same stem",
                "image_relative_path": "missing.jpg",
                "video_relative_path": "missing.mp4",
                "time_delta_seconds": "0",
                "shared_identifier": "",
            }
        ],
    )

    result = build_live_photos(pairs_csv, source_root, tmp_path / "out", tmp_path / "report")
    errors = list(csv.DictReader(result.errors_path.open(encoding="utf-8")))

    assert result.error_count == 1
    assert "Missing source file" in errors[0]["error"]


def test_live_build_rejects_relative_paths_that_escape_source_root(tmp_path):
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [
            {
                "pair_id": "pair-1",
                "category": "paired_candidate",
                "confidence": "high",
                "reason": "bad path",
                "image_relative_path": "../outside.jpg",
                "video_relative_path": "inside.mp4",
                "time_delta_seconds": "0",
                "shared_identifier": "",
            }
        ],
    )

    result = build_live_photos(pairs_csv, tmp_path / "source", tmp_path / "out", tmp_path / "report")
    errors = list(csv.DictReader(result.errors_path.open(encoding="utf-8")))

    assert result.error_count == 1
    assert "escapes source root" in errors[0]["error"]


def test_live_build_rejects_pair_ids_that_escape_output_root(tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "a.jpg", "image")
    video = _write_file(source_root / "a.mp4", "video")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [_pair_row("../bad", "paired_candidate", "high", image, video, source_root)],
    )

    result = build_live_photos(pairs_csv, source_root, tmp_path / "out", tmp_path / "report")
    errors = list(csv.DictReader(result.errors_path.open(encoding="utf-8")))

    assert result.error_count == 1
    assert "Invalid pair_id" in errors[0]["error"]


def test_live_build_refuses_to_overwrite_existing_pair_output(tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "a.jpg", "image")
    video = _write_file(source_root / "a.mp4", "video")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [_pair_row("pair-1", "paired_candidate", "high", image, video, source_root)],
    )
    (tmp_path / "out" / "pair-1").mkdir(parents=True)

    result = build_live_photos(pairs_csv, source_root, tmp_path / "out", tmp_path / "report")
    errors = list(csv.DictReader(result.errors_path.open(encoding="utf-8")))

    assert result.error_count == 1
    assert errors[0]["error"] == "Output pair directory already exists"


def test_live_build_records_backend_failures(tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "a.jpg", "image")
    video = _write_file(source_root / "a.mp4", "video")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [_pair_row("pair-1", "paired_candidate", "high", image, video, source_root)],
    )

    def failing_backend(image_path, video_path, makelive_path):
        raise RuntimeError("backend exploded")

    result = build_live_photos(
        pairs_csv,
        source_root,
        tmp_path / "out",
        tmp_path / "report",
        backend_runner=failing_backend,
    )
    errors = list(csv.DictReader(result.errors_path.open(encoding="utf-8")))

    assert result.error_count == 1
    assert errors[0]["error"] == "backend exploded"
    assert (tmp_path / "out" / "pair-1" / "a.jpg").exists()


def test_live_build_invokes_makelive_with_explicit_manual_pair(monkeypatch, tmp_path):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "Camera_XHS_1743314261438.jpg", "image")
    video = _write_file(source_root / "xhs_live_photo_1743314261947.mp4", "video")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [_pair_row("pair-1", "paired_candidate", "medium", image, video, source_root)],
    )
    commands = []

    class Completed:
        returncode = 0
        stderr = ""
        stdout = ""

    def fake_run(command, capture_output, check, text):
        commands.append(command)
        return Completed()

    monkeypatch.setattr("photodaterescue.live_build.subprocess.run", fake_run)

    result = build_live_photos(
        pairs_csv=pairs_csv,
        source_root=source_root,
        output=tmp_path / "out",
        report_dir=tmp_path / "report",
        makelive_path="/usr/local/bin/makelive",
    )

    assert result.built_count == 1
    assert commands == [
        [
            "/usr/local/bin/makelive",
            "--manual",
            str(tmp_path / "out" / "pair-1" / "Camera_XHS_1743314261438.jpg"),
            str(tmp_path / "out" / "pair-1" / "xhs_live_photo_1743314261947.mp4"),
        ]
    ]


def test_live_build_rejects_unknown_backend(tmp_path):
    with pytest.raises(ValueError, match="Unsupported live-build backend"):
        build_live_photos(tmp_path / "pairs.csv", tmp_path / "source", tmp_path / "out", tmp_path / "report", backend="x")


def test_cli_live_build_dry_run_does_not_require_exiftool(monkeypatch, tmp_path, capsys):
    source_root = tmp_path / "source"
    image = _write_file(source_root / "a.jpg", "image")
    video = _write_file(source_root / "a.mp4", "video")
    pairs_csv = _write_pairs_csv(
        tmp_path / "pairs.csv",
        [_pair_row("pair-1", "paired_candidate", "high", image, video, source_root)],
    )
    monkeypatch.setattr("photodaterescue.metadata.find_tool", lambda name: None)

    exit_code = main(
        [
            "live-build",
            "--pairs-csv",
            str(pairs_csv),
            "--source-root",
            str(source_root),
            "--output",
            str(tmp_path / "out"),
            "--report",
            str(tmp_path / "report"),
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Live build complete" in captured.out


def test_cli_live_build_reports_missing_pairs_csv_without_traceback(tmp_path, capsys):
    exit_code = main(
        [
            "live-build",
            "--pairs-csv",
            str(tmp_path / "missing.csv"),
            "--source-root",
            str(tmp_path / "source"),
            "--output",
            str(tmp_path / "out"),
            "--report",
            str(tmp_path / "report"),
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "Pairs CSV does not exist" in captured.out


def _write_file(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
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
