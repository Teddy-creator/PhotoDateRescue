"""Build Apple Live Photo-compatible copies from audited image/video pairs."""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence


ELIGIBLE_CATEGORY = "paired_candidate"
DEFAULT_CONFIDENCES = {"high", "medium"}
SUPPORTED_BACKENDS = {"makelive", "portable-pair"}
PORTABLE_PAIR_NOTE = "Portable pair package only; Apple Photos Live Photo recognition is not guaranteed."
LIVE_BUILD_FIELDS = [
    "pair_id",
    "status",
    "category",
    "confidence",
    "reason",
    "image_source",
    "video_source",
    "image_output",
    "video_output",
    "backend",
    "dry_run",
]
LIVE_BUILD_ERROR_FIELDS = [
    "pair_id",
    "category",
    "confidence",
    "image_source",
    "video_source",
    "error",
]


@dataclass
class LiveBuildResult:
    planned_count: int
    built_count: int
    skipped_count: int
    error_count: int
    manifest_path: Path
    rows_path: Path
    errors_path: Path


@dataclass
class LiveBuildPair:
    pair_id: str
    category: str
    confidence: str
    reason: str
    image_relative_path: str
    video_relative_path: str


BackendRunner = Callable[[Path, Path, str], None]


def build_live_photos(
    pairs_csv: Path,
    source_root: Path,
    output: Path,
    report_dir: Path,
    backend: str = "makelive",
    makelive_path: str = "makelive",
    include_uncertain: bool = False,
    dry_run: bool = False,
    backend_runner: Optional[BackendRunner] = None,
    validate_sources: bool = True,
) -> LiveBuildResult:
    if backend not in SUPPORTED_BACKENDS:
        raise ValueError("Unsupported live-build backend: {0}".format(backend))

    pairs_csv = pairs_csv.expanduser().resolve()
    source_root = source_root.expanduser().resolve()
    output = output.expanduser().resolve()
    report_dir = report_dir.expanduser().resolve()
    pairs = _read_pairs_csv(pairs_csv)
    runner = backend_runner or _run_makelive

    rows: List[Dict[str, str]] = []
    errors: List[Dict[str, str]] = []
    status_counts: Counter[str] = Counter()

    for pair in pairs:
        try:
            image_source = _resolve_source_path(source_root, pair.image_relative_path)
            video_source = _resolve_source_path(source_root, pair.video_relative_path)
            pair_output = _resolve_pair_output(output, pair.pair_id)
        except ValueError as exc:
            status_counts["error"] += 1
            errors.append(_error_row(pair, source_root / pair.image_relative_path, source_root / pair.video_relative_path, str(exc)))
            continue
        image_output = pair_output / image_source.name
        video_output = pair_output / video_source.name

        eligibility_error = _eligibility_error(pair, include_uncertain)
        if eligibility_error:
            status_counts["skipped"] += 1
            rows.append(
                _row(
                    pair=pair,
                    status="skipped",
                    image_source=image_source,
                    video_source=video_source,
                    image_output=image_output,
                    video_output=video_output,
                    backend=backend,
                    dry_run=dry_run,
                    reason=eligibility_error,
                )
            )
            continue

        source_error = _source_error(image_source, video_source) if validate_sources else ""
        if source_error:
            status_counts["error"] += 1
            errors.append(_error_row(pair, image_source, video_source, source_error))
            continue

        if pair_output.exists() and not dry_run:
            status_counts["error"] += 1
            errors.append(_error_row(pair, image_source, video_source, "Output pair directory already exists"))
            continue

        if dry_run:
            status_counts["planned"] += 1
            rows.append(
                _row(
                    pair=pair,
                    status="planned",
                    image_source=image_source,
                    video_source=video_source,
                    image_output=image_output,
                    video_output=video_output,
                    backend=backend,
                    dry_run=dry_run,
                )
            )
            continue

        try:
            pair_output.mkdir(parents=True, exist_ok=False)
            shutil.copy2(image_source, image_output)
            shutil.copy2(video_source, video_output)
            if backend == "makelive":
                runner(image_output, video_output, makelive_path)
            elif backend == "portable-pair":
                _write_pair_manifest(pair_output, pair, image_source, video_source, image_output, video_output)
        except Exception as exc:
            status_counts["error"] += 1
            errors.append(_error_row(pair, image_source, video_source, str(exc)))
            continue

        built_status = "built_pair" if backend == "portable-pair" else "built"
        status_counts[built_status] += 1
        rows.append(
            _row(
                pair=pair,
                status=built_status,
                image_source=image_source,
                video_source=video_source,
                image_output=image_output,
                video_output=video_output,
                backend=backend,
                dry_run=dry_run,
            )
        )

    report_dir.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)
    rows_path = report_dir / "live-build.csv"
    errors_path = report_dir / "errors.csv"
    manifest_path = report_dir / "live-build-manifest.json"
    _write_csv(rows_path, LIVE_BUILD_FIELDS, rows)
    _write_csv(errors_path, LIVE_BUILD_ERROR_FIELDS, errors)
    built_count = status_counts.get("built", 0) + status_counts.get("built_pair", 0)
    planned_count = status_counts.get("planned", 0) + built_count + status_counts.get("error", 0)
    manifest = {
        "pairs_csv": str(pairs_csv),
        "source_root": str(source_root),
        "output": str(output),
        "backend": backend,
        "dry_run": dry_run,
        "planned_count": planned_count,
        "built_count": built_count,
        "skipped_count": status_counts.get("skipped", 0),
        "error_count": status_counts.get("error", 0),
        "status_counts": dict(status_counts),
        "reports": {
            "rows": "live-build.csv",
            "errors": "errors.csv",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return LiveBuildResult(
        planned_count=planned_count,
        built_count=built_count,
        skipped_count=status_counts.get("skipped", 0),
        error_count=status_counts.get("error", 0),
        manifest_path=manifest_path,
        rows_path=rows_path,
        errors_path=errors_path,
    )


def _run_makelive(image_path: Path, video_path: Path, makelive_path: str) -> None:
    command = [makelive_path, "--manual", str(image_path), str(video_path)]
    completed = subprocess.run(command, capture_output=True, check=False, text=True)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "makelive failed"
        raise RuntimeError(message)


def _write_pair_manifest(
    pair_output: Path,
    pair: LiveBuildPair,
    image_source: Path,
    video_source: Path,
    image_output: Path,
    video_output: Path,
) -> None:
    manifest = {
        "pair_id": pair.pair_id,
        "category": pair.category,
        "confidence": pair.confidence,
        "reason": pair.reason,
        "backend": "portable-pair",
        "apple_live_status": "not_attempted",
        "import_validation_status": "not_tested",
        "note": PORTABLE_PAIR_NOTE,
        "sources": {
            "image": str(image_source),
            "video": str(video_source),
        },
        "outputs": {
            "image": str(image_output),
            "video": str(video_output),
        },
    }
    (pair_output / "pair.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_pairs_csv(path: Path) -> List[LiveBuildPair]:
    if not path.exists():
        raise FileNotFoundError("Pairs CSV does not exist: {0}".format(path))
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    required = {"pair_id", "category", "confidence", "reason", "image_relative_path", "video_relative_path"}
    if rows:
        missing = required - set(rows[0].keys())
        if missing:
            raise ValueError("pairs.csv is missing required columns: {0}".format(", ".join(sorted(missing))))

    return [
        LiveBuildPair(
            pair_id=row["pair_id"],
            category=row["category"],
            confidence=row["confidence"],
            reason=row.get("reason", ""),
            image_relative_path=row["image_relative_path"],
            video_relative_path=row["video_relative_path"],
        )
        for row in rows
    ]


def _resolve_source_path(source_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError("pairs.csv paths must be relative: {0}".format(value))
    resolved = (source_root / path).resolve()
    if not _is_relative_to(resolved, source_root):
        raise ValueError("pairs.csv path escapes source root: {0}".format(value))
    return resolved


def _resolve_pair_output(output: Path, pair_id: str) -> Path:
    path = Path(pair_id)
    if path.is_absolute() or any(part in {"..", ""} for part in path.parts) or len(path.parts) != 1:
        raise ValueError("Invalid pair_id for output folder: {0}".format(pair_id))
    resolved = (output / path).resolve()
    if not _is_relative_to(resolved, output):
        raise ValueError("pair_id escapes output root: {0}".format(pair_id))
    return resolved


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _eligibility_error(pair: LiveBuildPair, include_uncertain: bool) -> str:
    if pair.category == "uncertain_candidate" and include_uncertain:
        return ""
    if pair.category != ELIGIBLE_CATEGORY:
        return "Skipped category {0}".format(pair.category)
    if pair.confidence not in DEFAULT_CONFIDENCES:
        return "Skipped confidence {0}".format(pair.confidence)
    return ""


def _source_error(image_source: Path, video_source: Path) -> str:
    missing = [str(path) for path in (image_source, video_source) if not path.exists()]
    if missing:
        return "Missing source file(s): {0}".format(", ".join(missing))
    if not image_source.is_file() or not video_source.is_file():
        return "Source path is not a file"
    return ""


def _row(
    pair: LiveBuildPair,
    status: str,
    image_source: Path,
    video_source: Path,
    image_output: Path,
    video_output: Path,
    backend: str,
    dry_run: bool,
    reason: str = "",
) -> Dict[str, str]:
    return {
        "pair_id": pair.pair_id,
        "status": status,
        "category": pair.category,
        "confidence": pair.confidence,
        "reason": reason or pair.reason,
        "image_source": str(image_source),
        "video_source": str(video_source),
        "image_output": str(image_output),
        "video_output": str(video_output),
        "backend": backend,
        "dry_run": str(dry_run),
    }


def _error_row(pair: LiveBuildPair, image_source: Path, video_source: Path, error: str) -> Dict[str, str]:
    return {
        "pair_id": pair.pair_id,
        "category": pair.category,
        "confidence": pair.confidence,
        "image_source": str(image_source),
        "video_source": str(video_source),
        "error": error,
    }


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
