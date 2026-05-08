"""Read-only Motion Photo and Live Photo audit helpers."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .decision import choose_embedded_timestamp
from .discovery import discover_files
from .formats import MEDIA_KIND_IMAGE, MEDIA_KIND_VIDEO, resolve_media_kind
from .metadata import ExifToolClient
from .models import MetadataRecord, isoformat_or_empty


MOTION_EXTRA_TAGS = [
    "ContentIdentifier",
    "MediaGroupUUID",
    "LivePhotoAuto",
    "MotionPhoto",
    "MotionPhotoVersion",
    "MotionPhotoPresentationTimestampUs",
    "MicroVideo",
    "MicroVideoVersion",
    "MicroVideoOffset",
    "EmbeddedVideoFile",
    "EmbeddedVideoType",
    "EmbeddedVideoLength",
]

MOTION_KEYWORDS = (
    "motionphoto",
    "motion photo",
    "microvideo",
    "micro video",
    "embeddedvideo",
    "embedded video",
    "livephoto",
    "live photo",
)

XIAOHONGSHU_IMAGE_RE = re.compile(r"^camera_xhs_(\d{13})", re.IGNORECASE)
XIAOHONGSHU_VIDEO_RE = re.compile(r"^xhs_live_photo_(\d{13})", re.IGNORECASE)
XIAOHONGSHU_PAIR_MAX_NAME_DELTA_MS = 2_000
XIAOHONGSHU_PAIR_MAX_TIME_DELTA_SECONDS = 3
XIAOHONGSHU_SIDECAR_REASON = "Xiaohongshu sidecar timestamp match"
XIAOMI_NATIVE_EMBEDDED_REASON = "Xiaomi native camera embedded dynamic photo marker found"
GENERIC_MOTION_MARKER_REASON = "motion-related metadata marker found"
LIVE_IDENTIFIER_REASON = "live-photo grouping identifier found"

IDENTIFIER_KEYS = (
    "ContentIdentifier",
    "MediaGroupUUID",
)

CANDIDATE_FIELDS = [
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

PAIR_FIELDS = [
    "pair_id",
    "category",
    "confidence",
    "reason",
    "image_relative_path",
    "video_relative_path",
    "time_delta_seconds",
    "shared_identifier",
]

ERROR_FIELDS = ["relative_path", "absolute_path", "error"]


@dataclass
class MotionAuditResult:
    total_files: int
    supported_files: int
    candidate_count: int
    pair_count: int
    embedded_candidate_count: int
    uncertain_candidate_count: int
    error_count: int
    summary_path: Path
    candidates_path: Path
    pairs_path: Path
    errors_path: Path


@dataclass
class _MotionFile:
    absolute_path: Path
    relative_path: Path
    media_kind: Optional[str]
    metadata: MetadataRecord
    chosen_time: Optional[datetime]
    raw: Dict[str, Any]
    motion_markers: List[str]
    identifier: Optional[str]


@dataclass
class _PairCandidate:
    pair_id: str
    category: str
    confidence: str
    reason: str
    image: _MotionFile
    video: _MotionFile
    time_delta_seconds: Optional[int]
    shared_identifier: str = ""


def audit_motion_directory(
    root: Path,
    report_dir: Path,
    client: ExifToolClient,
    include_patterns: Iterable[str] | None = None,
    exclude_patterns: Iterable[str] | None = None,
) -> MotionAuditResult:
    root = root.expanduser().resolve()
    report_dir = report_dir.expanduser().resolve()
    discovered = discover_files(root, include_patterns=include_patterns, exclude_patterns=exclude_patterns)
    supported = [item for item in discovered if item.has_supported_extension]
    paths = [item.absolute_path.resolve() for item in supported]

    errors: List[Dict[str, str]] = []
    try:
        metadata_by_path = client.read_metadata(paths, extra_tags=MOTION_EXTRA_TAGS)
    except Exception as exc:  # pragma: no cover - validated by CLI-level behavior in real use
        metadata_by_path = {}
        message = str(exc)
        for item in supported:
            errors.append(
                {
                    "relative_path": item.relative_path.as_posix(),
                    "absolute_path": str(item.absolute_path),
                    "error": message,
                }
            )

    motion_files = []
    for item in supported:
        metadata = metadata_by_path.get(item.absolute_path.resolve(), MetadataRecord(raw={}))
        media_kind = resolve_media_kind(item.extension, metadata.file_type_extension)
        _, chosen_time = choose_embedded_timestamp(metadata, media_kind)
        if chosen_time is None:
            stat = item.absolute_path.stat()
            chosen_time = datetime.fromtimestamp(stat.st_mtime)
        raw = metadata.raw or {}
        motion_files.append(
            _MotionFile(
                absolute_path=item.absolute_path,
                relative_path=item.relative_path,
                media_kind=media_kind,
                metadata=metadata,
                chosen_time=chosen_time,
                raw=raw,
                motion_markers=_find_motion_markers(raw),
                identifier=_find_identifier(raw),
            )
        )

    pairs = _detect_pairs(motion_files)
    candidate_rows = _build_candidate_rows(motion_files, pairs)
    pair_rows = [_pair_to_row(pair) for pair in pairs]
    summary = _build_summary(
        total_files=len(discovered),
        supported_files=len(supported),
        motion_files=motion_files,
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        errors=errors,
    )

    report_dir.mkdir(parents=True, exist_ok=True)
    summary_path = report_dir / "summary.json"
    candidates_path = report_dir / "motion_candidates.csv"
    pairs_path = report_dir / "pairs.csv"
    errors_path = report_dir / "errors.csv"

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_csv(candidates_path, CANDIDATE_FIELDS, candidate_rows)
    _write_csv(pairs_path, PAIR_FIELDS, pair_rows)
    _write_csv(errors_path, ERROR_FIELDS, errors)

    category_counts = Counter(row["category"] for row in candidate_rows)
    return MotionAuditResult(
        total_files=len(discovered),
        supported_files=len(supported),
        candidate_count=len(candidate_rows),
        pair_count=len(pair_rows),
        embedded_candidate_count=category_counts.get("embedded_motion_candidate", 0),
        uncertain_candidate_count=category_counts.get("uncertain_candidate", 0),
        error_count=len(errors),
        summary_path=summary_path,
        candidates_path=candidates_path,
        pairs_path=pairs_path,
        errors_path=errors_path,
    )


def _detect_pairs(files: Sequence[_MotionFile]) -> List[_PairCandidate]:
    images = [item for item in files if item.media_kind == MEDIA_KIND_IMAGE]
    videos = [item for item in files if item.media_kind == MEDIA_KIND_VIDEO]
    pairs: List[_PairCandidate] = []
    used_images: set[Path] = set()
    used_videos: set[Path] = set()

    pairs.extend(_metadata_identifier_pairs(images, videos, used_images, used_videos))
    pairs.extend(_same_stem_pairs(images, videos, used_images, used_videos))
    pairs.extend(_xiaohongshu_sidecar_pairs(images, videos, used_images, used_videos))
    pairs.extend(_uncertain_near_pairs(images, videos, used_images, used_videos))
    return pairs


def _metadata_identifier_pairs(
    images: Sequence[_MotionFile],
    videos: Sequence[_MotionFile],
    used_images: set[Path],
    used_videos: set[Path],
) -> List[_PairCandidate]:
    image_by_identifier: Dict[str, List[_MotionFile]] = defaultdict(list)
    video_by_identifier: Dict[str, List[_MotionFile]] = defaultdict(list)
    for image in images:
        if image.identifier:
            image_by_identifier[image.identifier].append(image)
    for video in videos:
        if video.identifier:
            video_by_identifier[video.identifier].append(video)

    pairs = []
    for identifier in sorted(set(image_by_identifier) & set(video_by_identifier)):
        for image in image_by_identifier[identifier]:
            if image.absolute_path in used_images:
                continue
            videos_for_identifier = [video for video in video_by_identifier[identifier] if video.absolute_path not in used_videos]
            if not videos_for_identifier:
                continue
            video = _nearest_by_time(image, videos_for_identifier)
            pairs.append(
                _make_pair(
                    image=image,
                    video=video,
                    category="paired_candidate",
                    confidence="high",
                    reason="image and video share metadata identifier",
                    shared_identifier=identifier,
                )
            )
            used_images.add(image.absolute_path)
            used_videos.add(video.absolute_path)
    return pairs


def _same_stem_pairs(
    images: Sequence[_MotionFile],
    videos: Sequence[_MotionFile],
    used_images: set[Path],
    used_videos: set[Path],
) -> List[_PairCandidate]:
    videos_by_key: Dict[Tuple[str, str], List[_MotionFile]] = defaultdict(list)
    for video in videos:
        videos_by_key[(video.relative_path.parent.as_posix(), _normalized_stem(video.relative_path))].append(video)

    pairs = []
    for image in images:
        if image.absolute_path in used_images:
            continue
        key = (image.relative_path.parent.as_posix(), _normalized_stem(image.relative_path))
        candidates = [video for video in videos_by_key.get(key, []) if video.absolute_path not in used_videos]
        if not candidates:
            continue
        video = _nearest_by_time(image, candidates)
        pairs.append(
            _make_pair(
                image=image,
                video=video,
                category="paired_candidate",
                confidence="medium",
                reason="image and video share the same normalized stem in the same folder",
            )
        )
        used_images.add(image.absolute_path)
        used_videos.add(video.absolute_path)
    return pairs


def _xiaohongshu_sidecar_pairs(
    images: Sequence[_MotionFile],
    videos: Sequence[_MotionFile],
    used_images: set[Path],
    used_videos: set[Path],
) -> List[_PairCandidate]:
    videos_by_dir: Dict[str, List[_MotionFile]] = defaultdict(list)
    for video in videos:
        if _xiaohongshu_sidecar_video_timestamp_ms(video.relative_path) is not None:
            videos_by_dir[video.relative_path.parent.as_posix()].append(video)

    pairs = []
    for image in images:
        if image.absolute_path in used_images:
            continue
        image_timestamp = _xiaohongshu_sidecar_image_timestamp_ms(image.relative_path)
        if image_timestamp is None:
            continue
        candidates = []
        for video in videos_by_dir.get(image.relative_path.parent.as_posix(), []):
            if video.absolute_path in used_videos:
                continue
            video_timestamp = _xiaohongshu_sidecar_video_timestamp_ms(video.relative_path)
            if video_timestamp is None:
                continue
            name_delta = abs(image_timestamp - video_timestamp)
            if name_delta > XIAOHONGSHU_PAIR_MAX_NAME_DELTA_MS:
                continue
            time_delta = _time_delta_seconds(image, video)
            if time_delta is not None and time_delta > XIAOHONGSHU_PAIR_MAX_TIME_DELTA_SECONDS:
                continue
            candidates.append((name_delta, time_delta if time_delta is not None else 10**9, video))
        if not candidates:
            continue
        _, _, video = sorted(candidates, key=lambda item: (item[0], item[1], item[2].relative_path.as_posix()))[0]
        pairs.append(
            _make_pair(
                image=image,
                video=video,
                category="paired_candidate",
                confidence="medium",
                reason=XIAOHONGSHU_SIDECAR_REASON,
            )
        )
        used_images.add(image.absolute_path)
        used_videos.add(video.absolute_path)
    return pairs


def _uncertain_near_pairs(
    images: Sequence[_MotionFile],
    videos: Sequence[_MotionFile],
    used_images: set[Path],
    used_videos: set[Path],
) -> List[_PairCandidate]:
    pairs = []
    for image in images:
        if image.absolute_path in used_images:
            continue
        image_dir = image.relative_path.parent
        image_tokens = _stem_tokens(image.relative_path)
        candidates = []
        for video in videos:
            if video.absolute_path in used_videos or video.relative_path.parent != image_dir:
                continue
            delta = _time_delta_seconds(image, video)
            if delta is None or delta > 3:
                continue
            if _stems_related(image_tokens, _stem_tokens(video.relative_path)):
                candidates.append(video)
        if not candidates:
            continue
        video = _nearest_by_time(image, candidates)
        pairs.append(
            _make_pair(
                image=image,
                video=video,
                category="uncertain_candidate",
                confidence="low",
                reason="image and video have related names and very close timestamps",
            )
        )
        used_images.add(image.absolute_path)
        used_videos.add(video.absolute_path)
    return pairs


def _build_candidate_rows(files: Sequence[_MotionFile], pairs: Sequence[_PairCandidate]) -> List[Dict[str, str]]:
    rows = []
    pair_by_path: Dict[Path, _PairCandidate] = {}
    paired_path: Dict[Path, _MotionFile] = {}
    for pair in pairs:
        pair_by_path[pair.image.absolute_path] = pair
        pair_by_path[pair.video.absolute_path] = pair
        paired_path[pair.image.absolute_path] = pair.video
        paired_path[pair.video.absolute_path] = pair.image

    seen_paths = set()
    for path, pair in sorted(pair_by_path.items(), key=lambda item: item[0].as_posix()):
        file = pair.image if path == pair.image.absolute_path else pair.video
        other = paired_path[path]
        seen_paths.add(path)
        rows.append(
            _candidate_row(
                file=file,
                category=pair.category,
                confidence=pair.confidence,
                reason=pair.reason,
                paired_relative_path=other.relative_path.as_posix(),
                pair_id=pair.pair_id,
                time_delta_seconds=pair.time_delta_seconds,
            )
        )

    for file in files:
        if file.absolute_path in seen_paths or not (file.motion_markers or file.identifier):
            continue
        confidence = "high" if _has_strong_motion_marker(file.motion_markers) else "medium"
        reason = _embedded_candidate_reason(file)
        rows.append(
            _candidate_row(
                file=file,
                category="embedded_motion_candidate",
                confidence=confidence,
                reason=reason,
                paired_relative_path="",
                pair_id="",
                time_delta_seconds=None,
            )
        )

    return sorted(rows, key=lambda row: (row["category"], row["relative_path"]))


def _embedded_candidate_reason(file: _MotionFile) -> str:
    if file.motion_markers and _is_xiaomi_native_camera_motion(file):
        return XIAOMI_NATIVE_EMBEDDED_REASON
    if file.motion_markers:
        return GENERIC_MOTION_MARKER_REASON
    return LIVE_IDENTIFIER_REASON


def _candidate_row(
    file: _MotionFile,
    category: str,
    confidence: str,
    reason: str,
    paired_relative_path: str,
    pair_id: str,
    time_delta_seconds: Optional[int],
) -> Dict[str, str]:
    return {
        "relative_path": file.relative_path.as_posix(),
        "absolute_path": str(file.absolute_path),
        "category": category,
        "confidence": confidence,
        "reason": reason,
        "media_kind": file.media_kind or "",
        "paired_relative_path": paired_relative_path,
        "pair_id": pair_id,
        "time_delta_seconds": "" if time_delta_seconds is None else str(time_delta_seconds),
        "motion_markers": ";".join(file.motion_markers),
        "chosen_time": isoformat_or_empty(file.chosen_time),
    }


def _pair_to_row(pair: _PairCandidate) -> Dict[str, str]:
    return {
        "pair_id": pair.pair_id,
        "category": pair.category,
        "confidence": pair.confidence,
        "reason": pair.reason,
        "image_relative_path": pair.image.relative_path.as_posix(),
        "video_relative_path": pair.video.relative_path.as_posix(),
        "time_delta_seconds": "" if pair.time_delta_seconds is None else str(pair.time_delta_seconds),
        "shared_identifier": pair.shared_identifier,
    }


def _build_summary(
    total_files: int,
    supported_files: int,
    motion_files: Sequence[_MotionFile],
    candidate_rows: Sequence[Dict[str, str]],
    pair_rows: Sequence[Dict[str, str]],
    errors: Sequence[Dict[str, str]],
) -> Dict[str, object]:
    category_counts = Counter(row["category"] for row in candidate_rows)
    confidence_counts = Counter(row["confidence"] for row in candidate_rows)
    media_kind_counts = Counter((file.media_kind or "unknown") for file in motion_files)
    return {
        "total_files": total_files,
        "supported_files": supported_files,
        "candidate_count": len(candidate_rows),
        "pair_count": len(pair_rows),
        "embedded_candidate_count": category_counts.get("embedded_motion_candidate", 0),
        "uncertain_candidate_count": category_counts.get("uncertain_candidate", 0),
        "error_count": len(errors),
        "category_counts": dict(category_counts),
        "confidence_counts": dict(confidence_counts),
        "media_kind_counts": dict(media_kind_counts),
        "reports": {
            "candidates": "motion_candidates.csv",
            "pairs": "pairs.csv",
            "errors": "errors.csv",
        },
    }


def _make_pair(
    image: _MotionFile,
    video: _MotionFile,
    category: str,
    confidence: str,
    reason: str,
    shared_identifier: str = "",
) -> _PairCandidate:
    return _PairCandidate(
        pair_id=_pair_id(image, video),
        category=category,
        confidence=confidence,
        reason=reason,
        image=image,
        video=video,
        time_delta_seconds=_time_delta_seconds(image, video),
        shared_identifier=shared_identifier,
    )


def _find_motion_markers(raw: Dict[str, Any]) -> List[str]:
    markers = []
    for key, value in sorted(raw.items()):
        if not _is_truthy_marker_value(value):
            continue
        compact_key = _compact_text(key)
        compact_value = _compact_text(str(value))
        if any(keyword.replace(" ", "") in compact_key for keyword in MOTION_KEYWORDS):
            markers.append("{0}={1}".format(key, value))
            continue
        if any(keyword.replace(" ", "") in compact_value for keyword in MOTION_KEYWORDS):
            markers.append("{0}={1}".format(key, value))
    return markers


def _find_identifier(raw: Dict[str, Any]) -> Optional[str]:
    for key in IDENTIFIER_KEYS:
        value = raw.get(key)
        if value:
            return "{0}:{1}".format(key, value)
    return None


def _has_strong_motion_marker(markers: Sequence[str]) -> bool:
    joined = _compact_text(";".join(markers))
    strong = ("motionphoto", "microvideo", "embeddedvideo")
    return any(value in joined for value in strong)


def _is_xiaomi_native_camera_motion(file: _MotionFile) -> bool:
    if not file.motion_markers:
        return False
    make = _compact_text(str(file.raw.get("Make", "")))
    model = _compact_text(str(file.raw.get("Model", "")))
    return "xiaomi" in make or "xiaomi" in model or model == "23127pn0cc"


def _nearest_by_time(reference: _MotionFile, candidates: Sequence[_MotionFile]) -> _MotionFile:
    return sorted(
        candidates,
        key=lambda item: (
            _time_delta_seconds(reference, item) if _time_delta_seconds(reference, item) is not None else 10**9,
            item.relative_path.as_posix(),
        ),
    )[0]


def _time_delta_seconds(first: _MotionFile, second: _MotionFile) -> Optional[int]:
    if first.chosen_time is None or second.chosen_time is None:
        return None
    return int(abs((first.chosen_time - second.chosen_time).total_seconds()))


def _pair_id(image: _MotionFile, video: _MotionFile) -> str:
    value = "{0}|{1}".format(image.relative_path.as_posix(), video.relative_path.as_posix())
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def _normalized_stem(path: Path) -> str:
    stem = path.stem.lower()
    stem = re.sub(r"[\s_-]+", "", stem)
    stem = re.sub(r"(?:_?live|_?motion|_?video|_?vid)$", "", stem)
    return stem


def _stem_tokens(path: Path) -> set[str]:
    stem = path.stem.lower()
    return {token for token in re.split(r"[^a-z0-9]+", stem) if token}


def _xiaohongshu_sidecar_image_timestamp_ms(path: Path) -> Optional[int]:
    match = XIAOHONGSHU_IMAGE_RE.match(path.name)
    return int(match.group(1)) if match else None


def _xiaohongshu_sidecar_video_timestamp_ms(path: Path) -> Optional[int]:
    match = XIAOHONGSHU_VIDEO_RE.match(path.name)
    return int(match.group(1)) if match else None


def _stems_related(first: set[str], second: set[str]) -> bool:
    if not first or not second:
        return False
    if first & second:
        return True
    first_digits = {token for token in first if token.isdigit()}
    second_digits = {token for token in second if token.isdigit()}
    return bool(first_digits & second_digits)


def _compact_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _is_truthy_marker_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    return text not in {"", "0", "false", "no", "none", "null"}


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
