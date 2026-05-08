"""Extract embedded Android Motion Photo video trailers into separate files."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .metadata import ExifToolClient
from .models import MetadataRecord


MOTION_EXTRACT_TAGS = [
    "DirectoryItemLength",
    "ContainerDirectoryItemLength",
    "DirectoryItemSemantic",
    "ContainerDirectoryItemSemantic",
    "DirectoryItemMime",
    "ContainerDirectoryItemMime",
    "MicroVideoOffset",
]

EXTRACTION_FIELDS = [
    "pair_id",
    "status",
    "relative_path",
    "source_type",
    "source_reason",
    "still_output",
    "video_output",
    "video_length",
    "offset_source",
    "dry_run",
]
EXTRACTED_PAIR_FIELDS = [
    "pair_id",
    "category",
    "confidence",
    "reason",
    "source_type",
    "source_reason",
    "image_relative_path",
    "video_relative_path",
    "time_delta_seconds",
    "shared_identifier",
]
EXTRACTION_ERROR_FIELDS = ["relative_path", "absolute_path", "source_type", "source_reason", "error"]


@dataclass
class MotionExtractResult:
    planned_count: int
    extracted_count: int
    skipped_count: int
    error_count: int
    manifest_path: Path
    extraction_path: Path
    pairs_path: Path
    errors_path: Path
    source_type_counts: Dict[str, Dict[str, int]]


@dataclass
class _Candidate:
    relative_path: str
    absolute_path: str
    category: str
    confidence: str
    reason: str
    media_kind: str
    motion_markers: str


@dataclass
class _ExtractionPlan:
    candidate: _Candidate
    source_path: Path
    pair_id: str
    pair_output: Path
    still_output: Path
    video_output: Path
    video_length: int
    offset_source: str


def extract_motion_photos(
    candidates_csv: Path,
    source_root: Path,
    output: Path,
    report_dir: Path,
    client: ExifToolClient,
    dry_run: bool = False,
) -> MotionExtractResult:
    candidates_csv = candidates_csv.expanduser().resolve()
    source_root = source_root.expanduser().resolve()
    output = output.expanduser().resolve()
    report_dir = report_dir.expanduser().resolve()
    candidates = _read_candidates_csv(candidates_csv)
    supported_candidates = [candidate for candidate in candidates if candidate.category == "embedded_motion_candidate"]

    paths = []
    path_by_candidate: Dict[str, Path] = {}
    pre_errors: List[Dict[str, str]] = []
    invalid_candidate_paths: set[str] = set()
    for candidate in supported_candidates:
        try:
            source_path = _resolve_source_path(source_root, candidate.relative_path)
        except ValueError as exc:
            pre_errors.append(_error_row(candidate, source_root / candidate.relative_path, str(exc)))
            invalid_candidate_paths.add(candidate.relative_path)
            continue
        paths.append(source_path)
        path_by_candidate[candidate.relative_path] = source_path

    metadata_by_path = client.read_metadata(paths, extra_tags=MOTION_EXTRACT_TAGS) if paths else {}
    extraction_rows: List[Dict[str, str]] = []
    pair_rows: List[Dict[str, str]] = []
    errors: List[Dict[str, str]] = list(pre_errors)
    status_counts: Counter[str] = Counter()
    source_type_counts = _new_source_type_counts()
    if pre_errors:
        status_counts["error"] += len(pre_errors)

    skipped_count = len(candidates) - len(supported_candidates)
    if skipped_count:
        status_counts["skipped"] += skipped_count

    for candidate in supported_candidates:
        if candidate.relative_path in invalid_candidate_paths:
            continue
        source_path = path_by_candidate.get(candidate.relative_path)
        if source_path is None:
            status_counts["error"] += 1
            continue
        try:
            metadata = metadata_by_path.get(source_path.resolve(), MetadataRecord(raw={}))
            plan = _build_extraction_plan(candidate, source_path, output, metadata)
        except Exception as exc:
            status_counts["error"] += 1
            _increment_source_type_count(source_type_counts, candidate, "errors")
            errors.append(_error_row(candidate, source_path, str(exc)))
            continue

        if dry_run:
            status_counts["planned"] += 1
            _increment_source_type_count(source_type_counts, candidate, "planned")
            extraction_rows.append(_extraction_row(plan, "planned", dry_run=True))
            pair_rows.append(_pair_row(plan))
            continue

        if plan.pair_output.exists():
            status_counts["error"] += 1
            _increment_source_type_count(source_type_counts, candidate, "errors")
            errors.append(_error_row(candidate, source_path, "Output pair directory already exists"))
            continue

        try:
            _write_extracted_pair(plan)
        except Exception as exc:
            status_counts["error"] += 1
            _increment_source_type_count(source_type_counts, candidate, "errors")
            errors.append(_error_row(candidate, source_path, str(exc)))
            continue

        status_counts["extracted"] += 1
        _increment_source_type_count(source_type_counts, candidate, "extracted")
        extraction_rows.append(_extraction_row(plan, "extracted", dry_run=False))
        pair_rows.append(_pair_row(plan))

    report_dir.mkdir(parents=True, exist_ok=True)
    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)
    extraction_path = report_dir / "extraction.csv"
    pairs_path = report_dir / "extracted_pairs.csv"
    errors_path = report_dir / "errors.csv"
    manifest_path = report_dir / "motion-extract-manifest.json"
    _write_csv(extraction_path, EXTRACTION_FIELDS, extraction_rows)
    _write_csv(pairs_path, EXTRACTED_PAIR_FIELDS, pair_rows)
    _write_csv(errors_path, EXTRACTION_ERROR_FIELDS, errors)
    planned_count = status_counts.get("planned", 0) + status_counts.get("extracted", 0) + status_counts.get("error", 0)
    manifest = {
        "candidates_csv": str(candidates_csv),
        "source_root": str(source_root),
        "output": str(output),
        "dry_run": dry_run,
        "planned_count": planned_count,
        "extracted_count": status_counts.get("extracted", 0),
        "skipped_count": status_counts.get("skipped", 0),
        "error_count": status_counts.get("error", 0),
        "status_counts": dict(status_counts),
        "source_type_counts": _source_type_counts_for_json(source_type_counts),
        "reports": {
            "extraction": "extraction.csv",
            "pairs": "extracted_pairs.csv",
            "errors": "errors.csv",
        },
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return MotionExtractResult(
        planned_count=planned_count,
        extracted_count=status_counts.get("extracted", 0),
        skipped_count=status_counts.get("skipped", 0),
        error_count=status_counts.get("error", 0),
        manifest_path=manifest_path,
        extraction_path=extraction_path,
        pairs_path=pairs_path,
        errors_path=errors_path,
        source_type_counts=_source_type_counts_for_json(source_type_counts),
    )


def _build_extraction_plan(
    candidate: _Candidate,
    source_path: Path,
    output: Path,
    metadata: MetadataRecord,
) -> _ExtractionPlan:
    if source_path.suffix.lower() not in {".jpg", ".jpeg"}:
        raise ValueError("Only JPEG/JPG embedded Motion Photos are supported in this phase")
    if not source_path.exists():
        raise FileNotFoundError("Source file does not exist")
    if not source_path.is_file():
        raise ValueError("Source path is not a file")

    video_length, offset_source = _video_length_from_metadata(metadata.raw or {})
    file_size = source_path.stat().st_size
    if video_length <= 0 or video_length >= file_size:
        raise ValueError("Invalid embedded video length: {0}".format(video_length))
    video_start = file_size - video_length
    with source_path.open("rb") as handle:
        handle.seek(video_start)
        header = handle.read(16)
    if not _looks_like_mp4(header):
        raise ValueError("Embedded video does not start with an MP4/MOV ftyp box")

    pair_id = _pair_id(candidate.relative_path)
    pair_output = _resolve_pair_output(output, pair_id)
    still_name = Path(candidate.relative_path).name
    video_name = Path(candidate.relative_path).with_suffix(".mp4").name
    return _ExtractionPlan(
        candidate=candidate,
        source_path=source_path,
        pair_id=pair_id,
        pair_output=pair_output,
        still_output=pair_output / still_name,
        video_output=pair_output / video_name,
        video_length=video_length,
        offset_source=offset_source,
    )


def _write_extracted_pair(plan: _ExtractionPlan) -> None:
    plan.pair_output.mkdir(parents=True, exist_ok=False)
    video_start = plan.source_path.stat().st_size - plan.video_length
    with plan.source_path.open("rb") as source:
        still_bytes = source.read(video_start)
        video_bytes = source.read()
    plan.still_output.write_bytes(still_bytes)
    plan.video_output.write_bytes(video_bytes)
    shutil.copystat(plan.source_path, plan.still_output)
    shutil.copystat(plan.source_path, plan.video_output)


def _video_length_from_metadata(raw: Dict[str, Any]) -> tuple[int, str]:
    directory_length = _extract_directory_item_length(raw)
    if directory_length:
        return directory_length, "directory_item_length"

    micro_video_offset = _first_positive_int(raw, ["MicroVideoOffset"])
    if micro_video_offset:
        return micro_video_offset, "micro_video_offset"

    raise ValueError("No embedded video length metadata found")


def _extract_directory_item_length(raw: Dict[str, Any]) -> Optional[int]:
    lengths = _all_positive_ints(raw, ("DirectoryItemLength", "ContainerDirectoryItemLength"))
    if not lengths:
        return None
    semantics = [str(value).lower() for key, value in raw.items() if "semantic" in key.lower()]
    mimes = [str(value).lower() for key, value in raw.items() if "mime" in key.lower()]
    if semantics or mimes:
        for length in reversed(lengths):
            if any("motionphoto" in value or "video" in value for value in semantics + mimes):
                return length
    return lengths[-1]


def _read_candidates_csv(path: Path) -> List[_Candidate]:
    if not path.exists():
        raise FileNotFoundError("Motion candidates CSV does not exist: {0}".format(path))
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    required = {"relative_path", "absolute_path", "category", "confidence", "media_kind", "motion_markers"}
    if rows:
        missing = required - set(rows[0].keys())
        if missing:
            raise ValueError("motion_candidates.csv is missing required columns: {0}".format(", ".join(sorted(missing))))

    return [
        _Candidate(
            relative_path=row["relative_path"],
            absolute_path=row.get("absolute_path", ""),
            category=row["category"],
            confidence=row["confidence"],
            reason=row.get("reason", ""),
            media_kind=row["media_kind"],
            motion_markers=row.get("motion_markers", ""),
        )
        for row in rows
    ]


def _resolve_source_path(source_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise ValueError("motion_candidates.csv paths must be relative: {0}".format(value))
    resolved = (source_root / path).resolve()
    if not _is_relative_to(resolved, source_root):
        raise ValueError("motion_candidates.csv path escapes source root: {0}".format(value))
    return resolved


def _resolve_pair_output(output: Path, pair_id: str) -> Path:
    resolved = (output / pair_id).resolve()
    if not _is_relative_to(resolved, output):
        raise ValueError("pair_id escapes output root: {0}".format(pair_id))
    return resolved


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _looks_like_mp4(header: bytes) -> bool:
    return len(header) >= 12 and header[4:8] == b"ftyp"


def _pair_id(relative_path: str) -> str:
    return hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:12]


def _first_positive_int(raw: Dict[str, Any], names: Sequence[str]) -> Optional[int]:
    values = _all_positive_ints(raw, names)
    return values[0] if values else None


def _all_positive_ints(raw: Dict[str, Any], names: Sequence[str]) -> List[int]:
    wanted = {name.lower() for name in names}
    result = []
    for key, value in raw.items():
        compact_key = key.lower().replace(" ", "")
        if not any(name.lower().replace(" ", "") in compact_key for name in wanted):
            continue
        if isinstance(value, list):
            values = value
        else:
            values = [value]
        for item in values:
            parsed = _to_positive_int(item)
            if parsed is not None:
                result.append(parsed)
    return result


def _to_positive_int(value: Any) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _extraction_row(plan: _ExtractionPlan, status: str, dry_run: bool) -> Dict[str, str]:
    source_type = _source_type(plan.candidate)
    return {
        "pair_id": plan.pair_id,
        "status": status,
        "relative_path": plan.candidate.relative_path,
        "source_type": source_type,
        "source_reason": plan.candidate.reason,
        "still_output": str(plan.still_output),
        "video_output": str(plan.video_output),
        "video_length": str(plan.video_length),
        "offset_source": plan.offset_source,
        "dry_run": str(dry_run),
    }


def _pair_row(plan: _ExtractionPlan) -> Dict[str, str]:
    source_type = _source_type(plan.candidate)
    return {
        "pair_id": plan.pair_id,
        "category": "paired_candidate",
        "confidence": plan.candidate.confidence or "medium",
        "reason": "extracted from embedded Motion Photo",
        "source_type": source_type,
        "source_reason": plan.candidate.reason,
        "image_relative_path": plan.still_output.relative_to(plan.pair_output.parent).as_posix(),
        "video_relative_path": plan.video_output.relative_to(plan.pair_output.parent).as_posix(),
        "time_delta_seconds": "",
        "shared_identifier": "",
    }


def _source_type(candidate: _Candidate) -> str:
    reason = candidate.reason.lower()
    markers = candidate.motion_markers.lower()
    if "xiaomi native camera" in reason:
        return "xiaomi_native_camera"
    if "motion" in reason or "microvideo" in markers or "motionphoto" in markers:
        return "generic_embedded_motion"
    return "embedded_motion"


def _new_source_type_counts() -> Dict[str, Counter[str]]:
    return defaultdict(Counter)


def _increment_source_type_count(counts: Dict[str, Counter[str]], candidate: _Candidate, field: str) -> None:
    counts[_source_type(candidate)][field] += 1


def _source_type_counts_for_json(counts: Dict[str, Counter[str]]) -> Dict[str, Dict[str, int]]:
    result = {}
    for source_type, counter in sorted(counts.items()):
        result[source_type] = {
            "planned": int(counter.get("planned", 0)),
            "extracted": int(counter.get("extracted", 0)),
            "errors": int(counter.get("errors", 0)),
        }
    return result


def _error_row(candidate: _Candidate, source_path: Path, error: str) -> Dict[str, str]:
    return {
        "relative_path": candidate.relative_path,
        "absolute_path": str(source_path),
        "source_type": _source_type(candidate),
        "source_reason": candidate.reason,
        "error": error,
    }


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
