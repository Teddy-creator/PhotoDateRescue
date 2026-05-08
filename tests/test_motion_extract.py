import csv
import json
from pathlib import Path

from photodaterescue.cli import main
from photodaterescue.metadata import ExifToolClient
from photodaterescue.models import MetadataRecord
from photodaterescue.motion_extract import extract_motion_photos


class FakeExtractExifToolClient(ExifToolClient):
    def __init__(self, mapping):
        super().__init__(exiftool_path="exiftool")
        self.mapping = mapping
        self.extra_tags_seen = None

    def read_metadata(self, paths, extra_tags=None):
        self.extra_tags_seen = list(extra_tags or [])
        return {path.resolve(): self.mapping.get(path.resolve(), MetadataRecord(raw={})) for path in paths}


def test_motion_extract_dry_run_plans_embedded_candidate_without_writing(tmp_path):
    source_root = tmp_path / "source"
    source = _write_motion_photo(source_root / "DCIM/Camera/motion.jpg")
    candidates_csv = _write_candidates_csv(tmp_path / "candidates.csv", [_candidate_row(source, source_root)])
    client = FakeExtractExifToolClient({source.resolve(): MetadataRecord(raw={"DirectoryItemLength": str(len(VIDEO_BYTES))})})

    result = extract_motion_photos(
        candidates_csv=candidates_csv,
        source_root=source_root,
        output=tmp_path / "out",
        report_dir=tmp_path / "report",
        client=client,
        dry_run=True,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(result.extraction_path.open(encoding="utf-8")))

    assert result.planned_count == 1
    assert result.extracted_count == 0
    assert manifest["planned_count"] == 1
    assert rows[0]["status"] == "planned"
    assert not (tmp_path / "out").exists()


def test_motion_extract_splits_jpeg_and_embedded_mp4_using_directory_item_length(tmp_path):
    source_root = tmp_path / "source"
    source = _write_motion_photo(source_root / "DCIM/Camera/motion.jpg")
    candidates_csv = _write_candidates_csv(tmp_path / "candidates.csv", [_candidate_row(source, source_root)])
    client = FakeExtractExifToolClient({source.resolve(): MetadataRecord(raw={"DirectoryItemLength": str(len(VIDEO_BYTES))})})

    result = extract_motion_photos(candidates_csv, source_root, tmp_path / "out", tmp_path / "report", client)
    extraction_rows = list(csv.DictReader(result.extraction_path.open(encoding="utf-8")))
    pair_rows = list(csv.DictReader(result.pairs_path.open(encoding="utf-8")))
    still_output = Path(extraction_rows[0]["still_output"])
    video_output = Path(extraction_rows[0]["video_output"])

    assert result.planned_count == 1
    assert result.extracted_count == 1
    assert still_output.read_bytes() == STILL_BYTES
    assert video_output.read_bytes() == VIDEO_BYTES
    assert pair_rows[0]["category"] == "paired_candidate"
    assert pair_rows[0]["image_relative_path"].endswith("/motion.jpg")
    assert pair_rows[0]["video_relative_path"].endswith("/motion.mp4")


def test_motion_extract_reports_xiaomi_native_source_type(tmp_path):
    source_root = tmp_path / "source"
    source = _write_motion_photo(source_root / "DCIM/Camera/MVIMG_20250518_214522.jpg")
    candidates_csv = _write_candidates_csv(
        tmp_path / "candidates.csv",
        [
            _candidate_row(
                source,
                source_root,
                reason="Xiaomi native camera embedded dynamic photo marker found",
                motion_markers="MicroVideo=1;MicroVideoOffset={0};MicroVideoVersion=1".format(len(VIDEO_BYTES)),
            )
        ],
    )
    client = FakeExtractExifToolClient({source.resolve(): MetadataRecord(raw={"MicroVideoOffset": len(VIDEO_BYTES)})})

    result = extract_motion_photos(candidates_csv, source_root, tmp_path / "out", tmp_path / "report", client)
    extraction_rows = list(csv.DictReader(result.extraction_path.open(encoding="utf-8")))
    pair_rows = list(csv.DictReader(result.pairs_path.open(encoding="utf-8")))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert extraction_rows[0]["source_type"] == "xiaomi_native_camera"
    assert extraction_rows[0]["source_reason"] == "Xiaomi native camera embedded dynamic photo marker found"
    assert pair_rows[0]["source_type"] == "xiaomi_native_camera"
    assert pair_rows[0]["source_reason"] == "Xiaomi native camera embedded dynamic photo marker found"
    assert result.source_type_counts["xiaomi_native_camera"]["extracted"] == 1
    assert manifest["source_type_counts"]["xiaomi_native_camera"]["extracted"] == 1


def test_motion_extract_reports_generic_embedded_source_type(tmp_path):
    source_root = tmp_path / "source"
    source = _write_motion_photo(source_root / "DCIM/Camera/DOUYIN_LP_1768846657746.jpg")
    candidates_csv = _write_candidates_csv(
        tmp_path / "candidates.csv",
        [
            _candidate_row(
                source,
                source_root,
                reason="motion-related metadata marker found",
                motion_markers="MicroVideo=1;MicroVideoOffset={0};MicroVideoVersion=1".format(len(VIDEO_BYTES)),
            )
        ],
    )
    client = FakeExtractExifToolClient({source.resolve(): MetadataRecord(raw={"MicroVideoOffset": len(VIDEO_BYTES)})})

    result = extract_motion_photos(candidates_csv, source_root, tmp_path / "out", tmp_path / "report", client)
    rows = list(csv.DictReader(result.extraction_path.open(encoding="utf-8")))

    assert rows[0]["source_type"] == "generic_embedded_motion"
    assert rows[0]["source_reason"] == "motion-related metadata marker found"


def test_motion_extract_counts_errors_by_source_type(tmp_path):
    source_root = tmp_path / "source"
    source = source_root / "DCIM/Camera/MVIMG_20250518_214522.jpg"
    source.parent.mkdir(parents=True)
    source.write_bytes(STILL_BYTES + b"not-video")
    candidates_csv = _write_candidates_csv(
        tmp_path / "candidates.csv",
        [
            _candidate_row(
                source,
                source_root,
                reason="Xiaomi native camera embedded dynamic photo marker found",
                motion_markers="MicroVideo=1;MicroVideoOffset=9;MicroVideoVersion=1",
            )
        ],
    )
    client = FakeExtractExifToolClient({source.resolve(): MetadataRecord(raw={"MicroVideoOffset": 9})})

    result = extract_motion_photos(candidates_csv, source_root, tmp_path / "out", tmp_path / "report", client)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    errors = list(csv.DictReader(result.errors_path.open(encoding="utf-8")))

    assert result.error_count == 1
    assert result.source_type_counts["xiaomi_native_camera"]["errors"] == 1
    assert manifest["source_type_counts"]["xiaomi_native_camera"]["errors"] == 1
    assert errors[0]["source_type"] == "xiaomi_native_camera"


def test_motion_extract_falls_back_to_micro_video_offset(tmp_path):
    source_root = tmp_path / "source"
    source = _write_motion_photo(source_root / "motion.jpg")
    candidates_csv = _write_candidates_csv(tmp_path / "candidates.csv", [_candidate_row(source, source_root)])
    client = FakeExtractExifToolClient({source.resolve(): MetadataRecord(raw={"MicroVideoOffset": len(VIDEO_BYTES)})})

    result = extract_motion_photos(candidates_csv, source_root, tmp_path / "out", tmp_path / "report", client)
    rows = list(csv.DictReader(result.extraction_path.open(encoding="utf-8")))

    assert result.extracted_count == 1
    assert rows[0]["offset_source"] == "micro_video_offset"


def test_motion_extract_rejects_invalid_mp4_signature(tmp_path):
    source_root = tmp_path / "source"
    source = source_root / "motion.jpg"
    source.parent.mkdir(parents=True)
    source.write_bytes(STILL_BYTES + b"not-an-mp4-trailer")
    candidates_csv = _write_candidates_csv(tmp_path / "candidates.csv", [_candidate_row(source, source_root)])
    client = FakeExtractExifToolClient({source.resolve(): MetadataRecord(raw={"DirectoryItemLength": "18"})})

    result = extract_motion_photos(candidates_csv, source_root, tmp_path / "out", tmp_path / "report", client)
    errors = list(csv.DictReader(result.errors_path.open(encoding="utf-8")))

    assert result.error_count == 1
    assert "ftyp" in errors[0]["error"]


def test_motion_extract_skips_non_embedded_candidates(tmp_path):
    source_root = tmp_path / "source"
    source = _write_motion_photo(source_root / "motion.jpg")
    candidates_csv = _write_candidates_csv(
        tmp_path / "candidates.csv",
        [_candidate_row(source, source_root, category="paired_candidate")],
    )
    client = FakeExtractExifToolClient({})

    result = extract_motion_photos(candidates_csv, source_root, tmp_path / "out", tmp_path / "report", client)

    assert result.skipped_count == 1
    assert result.extracted_count == 0


def test_motion_extract_rejects_paths_that_escape_source_root(tmp_path):
    source_root = tmp_path / "source"
    candidates_csv = _write_candidates_csv(
        tmp_path / "candidates.csv",
        [
            {
                "relative_path": "../outside.jpg",
                "absolute_path": "",
                "category": "embedded_motion_candidate",
                "confidence": "high",
                "media_kind": "image",
                "motion_markers": "MotionPhoto=1",
            }
        ],
    )
    client = FakeExtractExifToolClient({})

    result = extract_motion_photos(candidates_csv, source_root, tmp_path / "out", tmp_path / "report", client)
    errors = list(csv.DictReader(result.errors_path.open(encoding="utf-8")))
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.error_count == 1
    assert manifest["error_count"] == 1
    assert "escapes source root" in errors[0]["error"]


def test_motion_extract_rejects_non_jpeg_candidates(tmp_path):
    source_root = tmp_path / "source"
    source = source_root / "motion.heic"
    source.parent.mkdir(parents=True)
    source.write_bytes(STILL_BYTES + VIDEO_BYTES)
    candidates_csv = _write_candidates_csv(tmp_path / "candidates.csv", [_candidate_row(source, source_root)])
    client = FakeExtractExifToolClient({source.resolve(): MetadataRecord(raw={"DirectoryItemLength": str(len(VIDEO_BYTES))})})

    result = extract_motion_photos(candidates_csv, source_root, tmp_path / "out", tmp_path / "report", client)
    errors = list(csv.DictReader(result.errors_path.open(encoding="utf-8")))

    assert result.error_count == 1
    assert "Only JPEG/JPG" in errors[0]["error"]


def test_cli_motion_extract_reports_missing_candidates_csv_without_traceback(tmp_path, capsys):
    exit_code = main(
        [
            "motion-extract",
            "--candidates-csv",
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
    assert "Motion candidates CSV does not exist" in captured.out


STILL_BYTES = b"\xff\xd8fake-jpeg-still\xff\xd9"
VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42fake-video"


def _write_motion_photo(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(STILL_BYTES + VIDEO_BYTES)
    return path


def _candidate_row(
    source: Path,
    source_root: Path,
    category: str = "embedded_motion_candidate",
    reason: str = "motion marker",
    motion_markers: str = "MotionPhoto=1",
) -> dict:
    return {
        "relative_path": source.relative_to(source_root).as_posix(),
        "absolute_path": str(source),
        "category": category,
        "confidence": "high",
        "reason": reason,
        "media_kind": "image",
        "paired_relative_path": "",
        "pair_id": "",
        "time_delta_seconds": "",
        "motion_markers": motion_markers,
        "chosen_time": "",
    }


def _write_candidates_csv(path: Path, rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "relative_path",
        "absolute_path",
        "category",
        "confidence",
        "reason",
        "media_kind",
        "paired_relative_path",
        "pair_id",
        "time_delta_seconds",
        "motion_markers",
        "chosen_time",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path
