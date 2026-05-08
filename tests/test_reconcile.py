import csv
import json

from photodaterescue.reconcile import reconcile_directories
from tests.factories import create_image


def test_reconcile_matches_same_image_across_formats(tmp_path):
    candidate = tmp_path / "candidate"
    baseline = tmp_path / "baseline"
    report = tmp_path / "report"

    create_image(candidate / "shot.png", fmt="PNG", size=(64, 48), color=(10, 20, 30))
    create_image(baseline / "shot.jpg", fmt="JPEG", size=(64, 48), color=(10, 20, 30))

    result = reconcile_directories(candidate, baseline, report)
    matched_rows = list(csv.DictReader((report / "matched.csv").open(encoding="utf-8")))

    assert result.matched_count == 1
    assert result.unmatched_count == 0
    assert matched_rows[0]["candidate_path"].endswith("shot.png")
    assert matched_rows[0]["baseline_path"].endswith("shot.jpg")


def test_reconcile_reports_unmatched_and_decode_errors(tmp_path):
    candidate = tmp_path / "candidate"
    baseline = tmp_path / "baseline"
    report = tmp_path / "report"

    create_image(candidate / "keep.png", fmt="PNG", size=(64, 48), color=(90, 10, 20))
    baseline.mkdir(parents=True, exist_ok=True)
    (candidate / "broken.jpg").parent.mkdir(parents=True, exist_ok=True)
    (candidate / "broken.jpg").write_text("not an image", encoding="utf-8")

    result = reconcile_directories(candidate, baseline, report)
    summary = json.loads((report / "summary.json").read_text(encoding="utf-8"))
    unmatched_rows = list(csv.DictReader((report / "unmatched.csv").open(encoding="utf-8")))
    error_rows = list(csv.DictReader((report / "errors.csv").open(encoding="utf-8")))

    assert result.unmatched_count == 1
    assert summary["candidate_error_count"] == 1
    assert unmatched_rows[0]["candidate_path"].endswith("keep.png")
    assert error_rows[0]["path"].endswith("broken.jpg")


def test_reconcile_skips_manifest_like_artifacts(tmp_path):
    candidate = tmp_path / "candidate"
    baseline = tmp_path / "baseline"
    report = tmp_path / "report"

    create_image(candidate / "a.png", fmt="PNG", size=(32, 32), color=(1, 2, 3))
    create_image(baseline / "a.jpg", fmt="JPEG", size=(32, 32), color=(1, 2, 3))
    (baseline / "_manifest.json").write_text("{}", encoding="utf-8")

    result = reconcile_directories(candidate, baseline, report)
    summary = json.loads((report / "summary.json").read_text(encoding="utf-8"))

    assert result.baseline_error_count == 0
    assert summary["baseline_total"] == 1
