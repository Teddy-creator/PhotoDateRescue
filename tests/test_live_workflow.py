import csv
import json
from datetime import datetime
from pathlib import Path

from photodaterescue.live_workflow import run_live_workflow
from photodaterescue.metadata import ExifToolClient
from photodaterescue.models import MetadataRecord
from tests.factories import create_image


class FakeWorkflowExifToolClient(ExifToolClient):
    def __init__(self, mapping):
        super().__init__(exiftool_path="exiftool")
        self.mapping = mapping

    def read_metadata(self, paths, extra_tags=None):
        return {path.resolve(): self.mapping.get(path.resolve(), MetadataRecord(raw={})) for path in paths}


def test_rescue_live_dry_run_writes_reports_without_media_outputs(tmp_path):
    source_root = tmp_path / "source"
    direct_image = create_image(source_root / "DCIM/Camera/IMG_001.jpg")
    direct_video = _write_file(source_root / "DCIM/Camera/IMG_001.mp4", b"direct-video")
    embedded = _write_motion_photo(source_root / "DCIM/Camera/motion.jpg")
    client = FakeWorkflowExifToolClient(
        {
            direct_image.resolve(): MetadataRecord(date_time_original=datetime(2025, 5, 1, 12, 0, 0), raw={}),
            direct_video.resolve(): MetadataRecord(
                file_type_extension="mp4",
                create_date=datetime(2025, 5, 1, 12, 0, 1),
                raw={},
            ),
            embedded.resolve(): MetadataRecord(
                date_time_original=datetime(2025, 5, 1, 12, 1, 0),
                raw={"MotionPhoto": 1, "DirectoryItemLength": str(len(VIDEO_BYTES))},
            ),
        }
    )

    result = run_live_workflow(
        input_root=source_root,
        work_dir=tmp_path / "work",
        output=tmp_path / "out",
        client=client,
        dry_run=True,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    direct_rows = list(csv.DictReader(result.direct_build.rows_path.open(encoding="utf-8")))
    extracted_rows = list(csv.DictReader(result.extracted_build.rows_path.open(encoding="utf-8")))

    assert result.audit.pair_count == 1
    assert result.extract.planned_count == 1
    assert result.planned_count == 2
    assert result.built_count == 0
    assert manifest["counts"]["total_live_planned"] == 2
    assert manifest["extract_source_type_counts"]["generic_embedded_motion"]["planned"] == 1
    assert direct_rows[0]["status"] == "planned"
    assert extracted_rows[0]["status"] == "planned"
    assert not (tmp_path / "work" / "extracted-motion").exists()
    assert not (tmp_path / "out").exists()


def test_rescue_live_builds_direct_and_extracted_outputs(tmp_path):
    source_root = tmp_path / "source"
    direct_image = create_image(source_root / "DCIM/Camera/IMG_001.jpg")
    direct_video = _write_file(source_root / "DCIM/Camera/IMG_001.mp4", b"direct-video")
    embedded = _write_motion_photo(source_root / "DCIM/Camera/motion.jpg")
    client = FakeWorkflowExifToolClient(
        {
            direct_image.resolve(): MetadataRecord(date_time_original=datetime(2025, 5, 1, 12, 0, 0), raw={}),
            direct_video.resolve(): MetadataRecord(
                file_type_extension="mp4",
                create_date=datetime(2025, 5, 1, 12, 0, 1),
                raw={},
            ),
            embedded.resolve(): MetadataRecord(
                date_time_original=datetime(2025, 5, 1, 12, 1, 0),
                raw={"MotionPhoto": 1, "DirectoryItemLength": str(len(VIDEO_BYTES))},
            ),
        }
    )
    backend_calls = []

    result = run_live_workflow(
        input_root=source_root,
        work_dir=tmp_path / "work",
        output=tmp_path / "out",
        client=client,
        makelive_path="/usr/local/bin/makelive",
        backend_runner=lambda image_path, video_path, makelive_path: backend_calls.append(
            (image_path, video_path, makelive_path)
        ),
    )

    assert result.extract.extracted_count == 1
    assert result.planned_count == 2
    assert result.built_count == 2
    assert len(backend_calls) == 2
    assert all(call[2] == "/usr/local/bin/makelive" for call in backend_calls)
    assert any(call[0].is_relative_to((tmp_path / "out" / "direct").resolve()) for call in backend_calls)
    assert any(call[0].is_relative_to((tmp_path / "out" / "extracted").resolve()) for call in backend_calls)


def test_rescue_live_manifest_reports_xiaomi_extract_source_counts(tmp_path):
    source_root = tmp_path / "source"
    embedded = _write_motion_photo(source_root / "DCIM/Camera/MVIMG_20250518_214522.jpg")
    client = FakeWorkflowExifToolClient(
        {
            embedded.resolve(): MetadataRecord(
                date_time_original=datetime(2025, 5, 18, 21, 45, 22),
                raw={
                    "Make": "Xiaomi",
                    "Model": "23127PN0CC",
                    "MicroVideo": 1,
                    "MicroVideoOffset": len(VIDEO_BYTES),
                    "MicroVideoVersion": 1,
                },
            ),
        }
    )

    result = run_live_workflow(
        input_root=source_root,
        work_dir=tmp_path / "work",
        output=tmp_path / "out",
        client=client,
        dry_run=True,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.extract.source_type_counts["xiaomi_native_camera"]["planned"] == 1
    assert manifest["extract_source_type_counts"]["xiaomi_native_camera"]["planned"] == 1


def _write_file(path: Path, payload: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


STILL_BYTES = b"\xff\xd8fake-jpeg-still\xff\xd9"
VIDEO_BYTES = b"\x00\x00\x00\x18ftypmp42fake-video"


def _write_motion_photo(path: Path) -> Path:
    return _write_file(path, STILL_BYTES + VIDEO_BYTES)
