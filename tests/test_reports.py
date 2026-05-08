import csv
import json
from datetime import datetime
from pathlib import Path

from photodaterescue.models import ScanRecord, ScanStatus
from photodaterescue.reports import write_reports


def make_record(status: ScanStatus, rel: str) -> ScanRecord:
    return ScanRecord(
        absolute_path=Path("/tmp") / rel,
        relative_path=Path(rel),
        extension=".jpg",
        width=10,
        height=10,
        has_exif_datetime=status == ScanStatus.OK,
        exif_datetime=datetime(2025, 1, 1, 0, 0, 0) if status == ScanStatus.OK else None,
        file_mtime=datetime(2025, 1, 2, 0, 0, 0),
        file_ctime=datetime(2025, 1, 3, 0, 0, 0),
        chosen_time_source="file_mtime" if status != ScanStatus.OK else "exif",
        chosen_datetime=datetime(2025, 1, 2, 0, 0, 0),
        status=status,
        reason="reason",
        is_supported=True,
        media_kind="image",
    )


def test_write_reports_creates_expected_files(tmp_path):
    write_reports([make_record(ScanStatus.REPAIRABLE, "a.jpg")], tmp_path)
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "files.csv").exists()
    assert (tmp_path / "high_risk.csv").exists()


def test_summary_counts_match_scan_records(tmp_path):
    write_reports(
        [
            make_record(ScanStatus.REPAIRABLE, "a.jpg"),
            make_record(ScanStatus.REPAIRABLE, "b.jpg"),
            make_record(ScanStatus.OK, "c.jpg"),
        ],
        tmp_path,
    )
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["status_counts"]["repairable"] == 2
    assert summary["media_kind_counts"]["image"] == 3


def test_high_risk_csv_contains_only_high_risk_rows(tmp_path):
    write_reports(
        [
            make_record(ScanStatus.HIGH_RISK, "a.jpg"),
            make_record(ScanStatus.OK, "b.jpg"),
        ],
        tmp_path,
    )
    rows = list(csv.DictReader((tmp_path / "high_risk.csv").open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["status"] == "high_risk"
