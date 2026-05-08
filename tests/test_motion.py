import csv
import json
from datetime import datetime

from photodaterescue.metadata import ExifToolClient
from photodaterescue.models import MetadataRecord
from photodaterescue.motion import audit_motion_directory
from tests.factories import create_image


class FakeMotionExifToolClient(ExifToolClient):
    def __init__(self, mapping):
        super().__init__(exiftool_path="exiftool")
        self.mapping = mapping
        self.extra_tags_seen = None

    def read_metadata(self, paths, extra_tags=None):
        self.extra_tags_seen = list(extra_tags or [])
        return {path.resolve(): self.mapping.get(path.resolve(), MetadataRecord(raw={})) for path in paths}


def test_motion_audit_detects_same_stem_image_video_pair(sample_root, tmp_path):
    image = create_image(sample_root / "DCIM" / "Camera" / "IMG_001.jpg")
    video = sample_root / "DCIM" / "Camera" / "IMG_001.mp4"
    video.write_bytes(b"fake-video")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(date_time_original=datetime(2025, 5, 1, 12, 0, 0), raw={}),
            video.resolve(): MetadataRecord(
                file_type_extension="mp4",
                create_date=datetime(2025, 5, 1, 12, 0, 1),
                raw={},
            ),
        }
    )

    result = audit_motion_directory(sample_root, tmp_path, client)
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    pair_rows = list(csv.DictReader((tmp_path / "pairs.csv").open(encoding="utf-8")))
    candidate_rows = list(csv.DictReader((tmp_path / "motion_candidates.csv").open(encoding="utf-8")))

    assert result.pair_count == 1
    assert summary["category_counts"]["paired_candidate"] == 2
    assert pair_rows[0]["image_relative_path"] == "DCIM/Camera/IMG_001.jpg"
    assert pair_rows[0]["video_relative_path"] == "DCIM/Camera/IMG_001.mp4"
    assert len(candidate_rows) == 2


def test_motion_audit_detects_shared_live_photo_identifier(sample_root, tmp_path):
    image = create_image(sample_root / "IMG_1234.HEIC", fmt="PNG")
    video = sample_root / "VID_9999.MOV"
    video.write_bytes(b"fake-video")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(
                file_type_extension="heic",
                date_time_original=datetime(2025, 5, 1, 12, 0, 0),
                raw={"ContentIdentifier": "abc-123"},
            ),
            video.resolve(): MetadataRecord(
                file_type_extension="mov",
                create_date=datetime(2025, 5, 1, 12, 0, 0),
                raw={"ContentIdentifier": "abc-123"},
            ),
        }
    )

    audit_motion_directory(sample_root, tmp_path, client)
    pair_rows = list(csv.DictReader((tmp_path / "pairs.csv").open(encoding="utf-8")))

    assert pair_rows[0]["confidence"] == "high"
    assert pair_rows[0]["shared_identifier"] == "ContentIdentifier:abc-123"


def test_motion_audit_detects_embedded_motion_marker(sample_root, tmp_path):
    image = create_image(sample_root / "motion.jpg")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(
                date_time_original=datetime(2025, 5, 1, 12, 0, 0),
                raw={"MotionPhoto": 1, "MicroVideoOffset": 1234},
            ),
        }
    )

    result = audit_motion_directory(sample_root, tmp_path, client)
    rows = list(csv.DictReader((tmp_path / "motion_candidates.csv").open(encoding="utf-8")))

    assert result.embedded_candidate_count == 1
    assert rows[0]["category"] == "embedded_motion_candidate"
    assert rows[0]["confidence"] == "high"
    assert "MotionPhoto=1" in rows[0]["motion_markers"]


def test_motion_audit_classifies_xiaomi_native_camera_embedded_microvideo(sample_root, tmp_path):
    image = create_image(sample_root / "DCIM" / "Camera" / "MVIMG_20250518_214522.jpg")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(
                date_time_original=datetime(2025, 5, 18, 21, 45, 22),
                raw={
                    "Make": "Xiaomi",
                    "Model": "23127PN0CC",
                    "MicroVideo": 1,
                    "MicroVideoOffset": 2934141,
                    "MicroVideoVersion": 1,
                },
            ),
        }
    )

    audit_motion_directory(sample_root, tmp_path, client)
    rows = list(csv.DictReader((tmp_path / "motion_candidates.csv").open(encoding="utf-8")))

    assert rows[0]["category"] == "embedded_motion_candidate"
    assert rows[0]["confidence"] == "high"
    assert rows[0]["reason"] == "Xiaomi native camera embedded dynamic photo marker found"


def test_motion_audit_keeps_non_xiaomi_microvideo_marker_generic(sample_root, tmp_path):
    image = create_image(sample_root / "DCIM" / "Camera" / "DOUYIN_LP_1768846657746.jpg")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(
                date_time_original=datetime(2026, 1, 20, 2, 17, 37),
                raw={
                    "MicroVideo": 1,
                    "MicroVideoOffset": 237372,
                    "MicroVideoVersion": 1,
                },
            ),
        }
    )

    audit_motion_directory(sample_root, tmp_path, client)
    rows = list(csv.DictReader((tmp_path / "motion_candidates.csv").open(encoding="utf-8")))

    assert rows[0]["category"] == "embedded_motion_candidate"
    assert rows[0]["confidence"] == "high"
    assert rows[0]["reason"] == "motion-related metadata marker found"


def test_motion_audit_ignores_false_motion_marker_values(sample_root, tmp_path):
    image = create_image(sample_root / "not-motion.jpg")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(
                date_time_original=datetime(2025, 5, 1, 12, 0, 0),
                raw={"MotionPhoto": 0, "MicroVideo": "false"},
            ),
        }
    )

    result = audit_motion_directory(sample_root, tmp_path, client)
    rows = list(csv.DictReader((tmp_path / "motion_candidates.csv").open(encoding="utf-8")))

    assert result.candidate_count == 0
    assert rows == []


def test_motion_audit_reports_unpaired_live_photo_identifier_as_embedded_candidate(sample_root, tmp_path):
    image = create_image(sample_root / "lonely-live.jpg")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(
                date_time_original=datetime(2025, 5, 1, 12, 0, 0),
                raw={"ContentIdentifier": "abc-123"},
            ),
        }
    )

    audit_motion_directory(sample_root, tmp_path, client)
    rows = list(csv.DictReader((tmp_path / "motion_candidates.csv").open(encoding="utf-8")))

    assert rows[0]["category"] == "embedded_motion_candidate"
    assert rows[0]["confidence"] == "medium"
    assert rows[0]["reason"] == "live-photo grouping identifier found"


def test_motion_audit_marks_related_near_time_pair_as_uncertain(sample_root, tmp_path):
    image = create_image(sample_root / "IMG_20250501_120000.jpg")
    video = sample_root / "VID_20250501_120000.mp4"
    video.write_bytes(b"fake-video")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(date_time_original=datetime(2025, 5, 1, 12, 0, 0), raw={}),
            video.resolve(): MetadataRecord(
                file_type_extension="mp4",
                create_date=datetime(2025, 5, 1, 12, 0, 2),
                raw={},
            ),
        }
    )

    result = audit_motion_directory(sample_root, tmp_path, client)
    pair_rows = list(csv.DictReader((tmp_path / "pairs.csv").open(encoding="utf-8")))

    assert result.uncertain_candidate_count == 2
    assert pair_rows[0]["category"] == "uncertain_candidate"
    assert pair_rows[0]["confidence"] == "low"
    assert len(pair_rows[0]["pair_id"]) == 12


def test_motion_audit_detects_xiaohongshu_live_photo_sidecar_pair(sample_root, tmp_path):
    image = create_image(sample_root / "DCIM" / "Camera_XHS_1743314261438.jpg")
    video = sample_root / "DCIM" / "xhs_live_photo_1743314261947.mp4"
    video.write_bytes(b"fake-video")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(date_time_original=datetime(2025, 3, 30, 13, 57, 41), raw={}),
            video.resolve(): MetadataRecord(
                file_type_extension="mp4",
                create_date=datetime(2025, 3, 30, 13, 57, 41),
                raw={},
            ),
        }
    )

    result = audit_motion_directory(sample_root, tmp_path, client)
    pair_rows = list(csv.DictReader((tmp_path / "pairs.csv").open(encoding="utf-8")))

    assert result.pair_count == 1
    assert result.uncertain_candidate_count == 0
    assert pair_rows[0]["category"] == "paired_candidate"
    assert pair_rows[0]["confidence"] == "medium"
    assert pair_rows[0]["reason"] == "Xiaohongshu sidecar timestamp match"


def test_motion_audit_detects_long_xiaohongshu_sidecar_filename(sample_root, tmp_path):
    image = create_image(sample_root / "DCIM" / "Camera_XHS_17431033035601040g2sg3130v2rdb40a042a68ci3qrbpia9p9vg.jpg")
    video = sample_root / "DCIM" / "xhs_live_photo_1743103304210.mp4"
    video.write_bytes(b"fake-video")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(date_time_original=datetime(2025, 3, 28, 3, 21, 43), raw={}),
            video.resolve(): MetadataRecord(
                file_type_extension="mp4",
                create_date=datetime(2025, 3, 28, 3, 21, 44),
                raw={},
            ),
        }
    )

    result = audit_motion_directory(sample_root, tmp_path, client)
    pair_rows = list(csv.DictReader((tmp_path / "pairs.csv").open(encoding="utf-8")))

    assert result.pair_count == 1
    assert pair_rows[0]["image_relative_path"] == "DCIM/Camera_XHS_17431033035601040g2sg3130v2rdb40a042a68ci3qrbpia9p9vg.jpg"
    assert pair_rows[0]["video_relative_path"] == "DCIM/xhs_live_photo_1743103304210.mp4"
    assert pair_rows[0]["reason"] == "Xiaohongshu sidecar timestamp match"


def test_motion_audit_does_not_pair_unmatched_xiaohongshu_image(sample_root, tmp_path):
    image = create_image(sample_root / "DCIM" / "Camera_XHS_17431033035601040g2sg3130v2rdb40a042a68ci3qrbpia9p9vg.jpg")
    unrelated_video = sample_root / "DCIM" / "xhs_live_photo_1743109999999.mp4"
    unrelated_video.write_bytes(b"fake-video")
    client = FakeMotionExifToolClient(
        {
            image.resolve(): MetadataRecord(date_time_original=datetime(2025, 3, 28, 3, 21, 43), raw={}),
            unrelated_video.resolve(): MetadataRecord(
                file_type_extension="mp4",
                create_date=datetime(2025, 3, 28, 5, 13, 19),
                raw={},
            ),
        }
    )

    result = audit_motion_directory(sample_root, tmp_path, client)
    pair_rows = list(csv.DictReader((tmp_path / "pairs.csv").open(encoding="utf-8")))

    assert result.pair_count == 0
    assert pair_rows == []


def test_motion_audit_respects_exclude_patterns(sample_root, tmp_path):
    create_image(sample_root / "Pictures" / ".thumbnails" / "IMG_001.jpg")
    video = sample_root / "Pictures" / ".thumbnails" / "IMG_001.mp4"
    video.write_bytes(b"fake-video")
    client = FakeMotionExifToolClient({})

    result = audit_motion_directory(sample_root, tmp_path, client, exclude_patterns=["Pictures/.thumbnails"])

    assert result.total_files == 0
    assert result.candidate_count == 0
