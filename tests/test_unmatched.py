import csv
import json
from pathlib import Path

from photodaterescue.reconcile import _build_visual_signature
from photodaterescue.unmatched import classify_unmatched_rows, materialize_unmatched_rows
from tests.factories import create_image


def test_classify_unmatched_rows_writes_expected_buckets(tmp_path):
    report = tmp_path / "report"
    baseline = tmp_path / "baseline"
    report.mkdir(parents=True, exist_ok=True)

    baseline_image = create_image(baseline / "base.jpg", fmt="JPEG", size=(100, 100), color=(10, 20, 30))
    _, _, baseline_hash = _build_visual_signature(baseline_image)

    rows = [
        {
            "candidate_path": str(tmp_path / "keep.jpg"),
            "width": "600",
            "height": "300",
            "dhash": _mutate_hash(baseline_hash, 10),
        },
        {
            "candidate_path": str(tmp_path / "duplicate.jpg"),
            "width": "100",
            "height": "100",
            "dhash": _mutate_hash(baseline_hash, 2),
        },
        {
            "candidate_path": str(tmp_path / "moderate.jpg"),
            "width": "400",
            "height": "410",
            "dhash": _mutate_hash(baseline_hash, 7),
        },
        {
            "candidate_path": str(tmp_path / "odd-size.jpg"),
            "width": "120",
            "height": "120",
            "dhash": _mutate_hash(baseline_hash, 20),
        },
        {
            "candidate_path": str(tmp_path / "dup (1).jpg"),
            "width": "500",
            "height": "600",
            "dhash": _mutate_hash(baseline_hash, 20),
        },
    ]
    _write_csv(report / "unmatched.csv", ["candidate_path", "width", "height", "dhash"], rows)

    result = classify_unmatched_rows(report, baseline)
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    classified_rows = list(csv.DictReader(result.classified_csv_path.open(encoding="utf-8")))

    assert summary["category_counts"] == {
        "recommended_keep": 1,
        "high_suspected_duplicate": 1,
        "manual_review": 3,
    }
    by_name = {Path(row["candidate_path"]).name: row for row in classified_rows}
    assert by_name["keep.jpg"]["category"] == "recommended_keep"
    assert by_name["duplicate.jpg"]["category"] == "high_suspected_duplicate"
    assert by_name["duplicate.jpg"]["reason"] == "same dimensions and low dhash distance=2"
    assert by_name["moderate.jpg"]["category"] == "manual_review"
    assert by_name["moderate.jpg"]["reason"] == "moderately close to baseline distance=7"
    assert by_name["odd-size.jpg"]["weird_dimension_flag"] == "True"
    assert by_name["dup (1).jpg"]["category"] == "manual_review"


def test_materialize_unmatched_rows_copy_mode_handles_collisions_and_missing_files(tmp_path):
    source_a = tmp_path / "source-a" / "photo.jpg"
    source_b = tmp_path / "source-b" / "photo.jpg"
    source_a.parent.mkdir(parents=True, exist_ok=True)
    source_b.parent.mkdir(parents=True, exist_ok=True)
    source_a.write_text("a", encoding="utf-8")
    source_b.write_text("b", encoding="utf-8")

    classified_csv = tmp_path / "classified.csv"
    _write_csv(
        classified_csv,
        ["candidate_path", "category"],
        [
            {"candidate_path": str(source_a), "category": "recommended_keep"},
            {"candidate_path": str(source_b), "category": "recommended_keep"},
            {"candidate_path": str(tmp_path / "missing.jpg"), "category": "manual_review"},
        ],
    )

    output_root = tmp_path / "quarantine"
    result = materialize_unmatched_rows(classified_csv, output_root, mode="copy")
    summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    copied_names = sorted(path.name for path in (output_root / "06-unmatched-recommended-keep").iterdir())

    assert source_a.exists()
    assert source_b.exists()
    assert copied_names == ["photo.jpg", "photo__2.jpg"]
    assert result.processed_count == 2
    assert result.error_count == 1
    assert summary["category_counts"] == {"recommended_keep": 2}


def test_materialize_unmatched_rows_move_mode_supports_relative_paths(tmp_path):
    source_root = tmp_path / "source-root"
    source_file = source_root / "nested" / "clip.jpg"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_text("demo", encoding="utf-8")

    classified_csv = tmp_path / "classified.csv"
    _write_csv(
        classified_csv,
        ["candidate_path", "category"],
        [{"candidate_path": "nested/clip.jpg", "category": "manual_review"}],
    )

    output_root = tmp_path / "quarantine"
    result = materialize_unmatched_rows(
        classified_csv,
        output_root,
        mode="move",
        source_root=source_root,
    )

    moved_path = output_root / "07-unmatched-manual-review" / "clip.jpg"
    assert moved_path.exists()
    assert not source_file.exists()
    assert result.processed_count == 1
    assert result.error_count == 0


def _mutate_hash(value: str, distance: int) -> str:
    mutated = int(value, 16)
    for bit in range(distance):
        mutated ^= 1 << bit
    return "{0:016x}".format(mutated)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
