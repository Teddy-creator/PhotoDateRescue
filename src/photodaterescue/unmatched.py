"""Classification and materialization helpers for unmatched reconcile rows."""

from __future__ import annotations

import csv
import json
import re
import shutil
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .reconcile import _build_visual_signature, _discover_visible_files

CLASSIFIED_HEADERS = [
    "candidate_path",
    "width",
    "height",
    "category",
    "reason",
    "nearest_baseline_path",
    "nearest_baseline_width",
    "nearest_baseline_height",
    "nearest_baseline_dhash_distance",
    "same_dim_best_distance",
    "duplicate_group_size_within_unmatched",
    "large_phone_like",
    "weird_dimension_flag",
]

CLASSIFICATION_ERROR_HEADERS = ["side", "path", "error"]
MATERIALIZE_LOG_HEADERS = ["category", "mode", "old_path", "new_path"]
MATERIALIZE_ERROR_HEADERS = ["category", "path", "error"]

CATEGORY_RECOMMENDED_KEEP = "recommended_keep"
CATEGORY_MANUAL_REVIEW = "manual_review"
CATEGORY_HIGH_SUSPECTED_DUPLICATE = "high_suspected_duplicate"

BUCKET_DIRS = {
    CATEGORY_RECOMMENDED_KEEP: "06-unmatched-recommended-keep",
    CATEGORY_MANUAL_REVIEW: "07-unmatched-manual-review",
    CATEGORY_HIGH_SUSPECTED_DUPLICATE: "08-unmatched-high-suspected-duplicate",
}

_DUPLICATE_SUFFIX_RE = re.compile(r"\s+\(\d+\)$")


@dataclass
class BaselineSignature:
    path: Path
    width: int
    height: int
    dhash: str


@dataclass
class UnmatchedClassificationResult:
    classified_csv_path: Path
    summary_path: Path
    errors_path: Path
    total_rows: int
    baseline_total: int
    baseline_error_count: int
    category_counts: Dict[str, int]


@dataclass
class UnmatchedMaterializeResult:
    summary_path: Path
    move_log_path: Path
    errors_path: Path
    processed_count: int
    error_count: int
    category_counts: Dict[str, int]


def classify_unmatched_rows(
    report_dir: Path,
    baseline: Path,
    output_dir: Optional[Path] = None,
) -> UnmatchedClassificationResult:
    report_dir = report_dir.expanduser().resolve()
    baseline = baseline.expanduser().resolve()
    output_dir = (output_dir or report_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    unmatched_rows = _read_unmatched_rows(report_dir / "unmatched.csv")
    baseline_entries, baseline_errors = _load_baseline_signatures(baseline)
    duplicate_counts = Counter(
        (int(row["width"]), int(row["height"]), _normalize_hash(row["dhash"])) for row in unmatched_rows
    )
    same_dim_index: Dict[Tuple[int, int], List[BaselineSignature]] = {}
    for entry in baseline_entries:
        same_dim_index.setdefault((entry.width, entry.height), []).append(entry)

    classified_rows = []
    category_counts: Counter[str] = Counter()
    for row in unmatched_rows:
        width = int(row["width"])
        height = int(row["height"])
        dhash = _normalize_hash(row["dhash"])
        nearest = _find_nearest_baseline(width, height, dhash, baseline_entries)
        same_dim_best_distance = _find_same_dim_best_distance(width, height, dhash, same_dim_index)
        duplicate_group_size = duplicate_counts[(width, height, dhash)]
        weird_dimension_flag = _is_weird_dimension(width, height)
        large_phone_like = _is_large_phone_like(width, height)
        candidate_path = row["candidate_path"]
        category, reason = _classify_row(
            candidate_path=candidate_path,
            width=width,
            height=height,
            nearest=nearest,
            same_dim_best_distance=same_dim_best_distance,
            duplicate_group_size=duplicate_group_size,
            weird_dimension_flag=weird_dimension_flag,
        )
        category_counts[category] += 1
        classified_rows.append(
            {
                "candidate_path": candidate_path,
                "width": str(width),
                "height": str(height),
                "category": category,
                "reason": reason,
                "nearest_baseline_path": str(nearest.path) if nearest else "",
                "nearest_baseline_width": str(nearest.width) if nearest else "",
                "nearest_baseline_height": str(nearest.height) if nearest else "",
                "nearest_baseline_dhash_distance": str(nearest.distance) if nearest else "",
                "same_dim_best_distance": (
                    str(same_dim_best_distance) if same_dim_best_distance is not None else ""
                ),
                "duplicate_group_size_within_unmatched": str(duplicate_group_size),
                "large_phone_like": str(large_phone_like),
                "weird_dimension_flag": str(weird_dimension_flag),
            }
        )

    classified_csv_path = output_dir / "unmatched-classified.csv"
    summary_path = output_dir / "unmatched-classification-summary.json"
    errors_path = output_dir / "unmatched-classification-errors.csv"

    _write_csv(classified_csv_path, CLASSIFIED_HEADERS, classified_rows)
    _write_csv(
        output_dir / "recommended-keep.csv",
        CLASSIFIED_HEADERS,
        [row for row in classified_rows if row["category"] == CATEGORY_RECOMMENDED_KEEP],
    )
    _write_csv(
        output_dir / "manual-review.csv",
        CLASSIFIED_HEADERS,
        [row for row in classified_rows if row["category"] == CATEGORY_MANUAL_REVIEW],
    )
    _write_csv(
        output_dir / "high-suspected-duplicate.csv",
        CLASSIFIED_HEADERS,
        [row for row in classified_rows if row["category"] == CATEGORY_HIGH_SUSPECTED_DUPLICATE],
    )
    _write_csv(errors_path, CLASSIFICATION_ERROR_HEADERS, baseline_errors)
    summary_path.write_text(
        json.dumps(
            {
                "total_rows": len(classified_rows),
                "baseline_total": len(baseline_entries),
                "baseline_error_count": len(baseline_errors),
                "category_counts": dict(category_counts),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return UnmatchedClassificationResult(
        classified_csv_path=classified_csv_path,
        summary_path=summary_path,
        errors_path=errors_path,
        total_rows=len(classified_rows),
        baseline_total=len(baseline_entries),
        baseline_error_count=len(baseline_errors),
        category_counts=dict(category_counts),
    )


def materialize_unmatched_rows(
    classified_csv: Path,
    output_root: Path,
    mode: str = "copy",
    source_root: Optional[Path] = None,
) -> UnmatchedMaterializeResult:
    classified_csv = classified_csv.expanduser().resolve()
    output_root = output_root.expanduser().resolve()
    source_root = source_root.expanduser().resolve() if source_root else None
    output_root.mkdir(parents=True, exist_ok=True)
    docs_dir = output_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    rows = _read_csv_rows(classified_csv)
    move_log_rows = []
    error_rows = []
    category_counts: Counter[str] = Counter()

    for row in rows:
        category = row.get("category", "")
        if category not in BUCKET_DIRS:
            error_rows.append(
                {
                    "category": category or "unknown",
                    "path": row.get("candidate_path", ""),
                    "error": "Unsupported category in classified CSV",
                }
            )
            continue
        source_path = _resolve_candidate_path(row.get("candidate_path", ""), source_root)
        if not source_path.exists():
            error_rows.append(
                {
                    "category": category,
                    "path": str(source_path),
                    "error": "Source file does not exist",
                }
            )
            continue
        bucket_dir = output_root / BUCKET_DIRS[category]
        bucket_dir.mkdir(parents=True, exist_ok=True)
        destination = _allocate_destination(bucket_dir / source_path.name)
        if mode == "copy":
            shutil.copy2(source_path, destination)
        elif mode == "move":
            shutil.move(str(source_path), str(destination))
        else:  # pragma: no cover - guarded by CLI and unit tests on public function
            raise ValueError("Unsupported materialize mode: {0}".format(mode))
        category_counts[category] += 1
        move_log_rows.append(
            {
                "category": category,
                "mode": mode,
                "old_path": str(source_path),
                "new_path": str(destination),
            }
        )

    move_log_path = docs_dir / "unmatched-materialize-log.csv"
    errors_path = docs_dir / "unmatched-materialize-errors.csv"
    summary_path = docs_dir / "unmatched-materialize-summary.json"
    _write_csv(move_log_path, MATERIALIZE_LOG_HEADERS, move_log_rows)
    _write_csv(errors_path, MATERIALIZE_ERROR_HEADERS, error_rows)
    summary_path.write_text(
        json.dumps(
            {
                "mode": mode,
                "processed_count": len(move_log_rows),
                "error_count": len(error_rows),
                "category_counts": dict(category_counts),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return UnmatchedMaterializeResult(
        summary_path=summary_path,
        move_log_path=move_log_path,
        errors_path=errors_path,
        processed_count=len(move_log_rows),
        error_count=len(error_rows),
        category_counts=dict(category_counts),
    )


@dataclass
class _NearestBaseline:
    path: Path
    width: int
    height: int
    distance: int


def _load_baseline_signatures(baseline: Path) -> Tuple[List[BaselineSignature], List[dict]]:
    baseline_files = _discover_visible_files(baseline)
    baseline_entries: List[BaselineSignature] = []
    baseline_errors: List[dict] = []
    for path in baseline_files:
        try:
            width, height, dhash = _build_visual_signature(path)
        except Exception as exc:  # pragma: no cover - exercised through monkeypatching patterns
            baseline_errors.append({"side": "baseline", "path": str(path), "error": str(exc)})
            continue
        baseline_entries.append(BaselineSignature(path=path, width=width, height=height, dhash=dhash))
    return baseline_entries, baseline_errors


def _read_unmatched_rows(path: Path) -> List[dict]:
    rows = _read_csv_rows(path)
    required = {"candidate_path", "width", "height", "dhash"}
    if rows:
        missing = required - set(rows[0].keys())
        if missing:
            raise ValueError("unmatched.csv is missing required columns: {0}".format(", ".join(sorted(missing))))
    return rows


def _read_csv_rows(path: Path) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError("CSV file does not exist: {0}".format(path))
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _find_nearest_baseline(
    width: int,
    height: int,
    dhash: str,
    baseline_entries: Sequence[BaselineSignature],
) -> Optional[_NearestBaseline]:
    best: Optional[_NearestBaseline] = None
    candidate_ratio = _aspect_ratio(width, height)
    for entry in baseline_entries:
        distance = _hash_distance(dhash, entry.dhash)
        if best is None:
            best = _NearestBaseline(entry.path, entry.width, entry.height, distance)
            continue
        current_ratio = _aspect_ratio(entry.width, entry.height)
        best_ratio = _aspect_ratio(best.width, best.height)
        current_key = (distance, abs(candidate_ratio - current_ratio), abs(width - entry.width) + abs(height - entry.height))
        best_key = (best.distance, abs(candidate_ratio - best_ratio), abs(width - best.width) + abs(height - best.height))
        if current_key < best_key:
            best = _NearestBaseline(entry.path, entry.width, entry.height, distance)
    return best


def _find_same_dim_best_distance(
    width: int,
    height: int,
    dhash: str,
    same_dim_index: Dict[Tuple[int, int], List[BaselineSignature]],
) -> Optional[int]:
    entries = same_dim_index.get((width, height), [])
    if not entries:
        return None
    return min(_hash_distance(dhash, entry.dhash) for entry in entries)


def _classify_row(
    candidate_path: str,
    width: int,
    height: int,
    nearest: Optional[_NearestBaseline],
    same_dim_best_distance: Optional[int],
    duplicate_group_size: int,
    weird_dimension_flag: bool,
) -> Tuple[str, str]:
    if same_dim_best_distance is not None and same_dim_best_distance <= 2:
        return (
            CATEGORY_HIGH_SUSPECTED_DUPLICATE,
            "same dimensions and low dhash distance={0}".format(same_dim_best_distance),
        )
    if nearest and nearest.distance == 0 and _aspect_ratio_delta(width, height, nearest.width, nearest.height) <= 0.02:
        return (
            CATEGORY_HIGH_SUSPECTED_DUPLICATE,
            "very close visual hash distance=0 with similar aspect",
        )
    if weird_dimension_flag or duplicate_group_size > 1 or _looks_duplicate_named(candidate_path):
        return (
            CATEGORY_MANUAL_REVIEW,
            "odd dimensions or duplicate-like naming/signature",
        )
    if nearest and nearest.distance <= 10 and _aspect_ratio_delta(width, height, nearest.width, nearest.height) <= 0.25:
        return (
            CATEGORY_MANUAL_REVIEW,
            "moderately close to baseline distance={0}".format(nearest.distance),
        )
    return CATEGORY_RECOMMENDED_KEEP, "no close baseline match under current heuristic"


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[dict]) -> None:
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def _hash_distance(left: str, right: str) -> int:
    value = int(_normalize_hash(left), 16) ^ int(_normalize_hash(right), 16)
    return bin(value).count("1")


def _normalize_hash(value: str) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        raise ValueError("dhash value is empty")
    return normalized


def _is_weird_dimension(width: int, height: int) -> bool:
    smaller = min(width, height)
    larger = max(width, height)
    if smaller <= 256:
        return True
    return (larger / max(smaller, 1)) >= 4.5


def _is_large_phone_like(width: int, height: int) -> bool:
    smaller = min(width, height)
    larger = max(width, height)
    ratio = larger / max(smaller, 1)
    return smaller >= 1000 and larger >= 1800 and 1.6 <= ratio <= 2.3


def _looks_duplicate_named(candidate_path: str) -> bool:
    stem = Path(candidate_path).stem
    return bool(_DUPLICATE_SUFFIX_RE.search(stem))


def _aspect_ratio(width: int, height: int) -> float:
    return width / max(height, 1)


def _aspect_ratio_delta(left_width: int, left_height: int, right_width: int, right_height: int) -> float:
    return abs(_aspect_ratio(left_width, left_height) - _aspect_ratio(right_width, right_height))


def _resolve_candidate_path(candidate_path: str, source_root: Optional[Path]) -> Path:
    path = Path(candidate_path).expanduser()
    if path.is_absolute():
        return path.resolve()
    if source_root is not None:
        return (source_root / path).resolve()
    return path.resolve()


def _allocate_destination(destination: Path) -> Path:
    if not destination.exists():
        return destination
    counter = 2
    while True:
        candidate = destination.with_name(
            "{0}__{1}{2}".format(destination.stem, counter, destination.suffix)
        )
        if not candidate.exists():
            return candidate
        counter += 1
