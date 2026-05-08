"""Read-only inspection for Apple Live Photo pairing signals."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .metadata import ExifToolClient


LIVE_INSPECT_TAGS = [
    "ContentIdentifier",
    "MediaGroupUUID",
    "StillImageTime",
    "MakerNoteApple",
    "Duration",
    "Rotation",
    "ImageWidth",
    "ImageHeight",
]


def inspect_live_pair(image: Path, video: Path, client: ExifToolClient) -> Dict[str, Any]:
    image = image.expanduser().resolve()
    video = video.expanduser().resolve()
    _ensure_file(image, "image")
    _ensure_file(video, "video")

    records = client.read_metadata([image, video], extra_tags=LIVE_INSPECT_TAGS)
    image_raw = records[image].raw or {}
    video_raw = records[video].raw or {}
    image_identifier = _first_present(image_raw, ["ContentIdentifier", "MediaGroupUUID"])
    video_identifier = _first_present(video_raw, ["ContentIdentifier", "MediaGroupUUID"])
    identifiers_match = bool(image_identifier and video_identifier and image_identifier == video_identifier)

    return {
        "image_path": str(image),
        "video_path": str(video),
        "apple_live_status": _apple_live_status(image_identifier, video_identifier, identifiers_match),
        "content_identifier_match": identifiers_match,
        "import_validation_status": "not_tested",
        "image": {
            "content_identifier": image_identifier,
            "apple_makernotes_present": _has_apple_makernotes(image_raw),
            "still_image_time": _value_or_none(image_raw.get("StillImageTime")),
            "width": _to_int(_first_present(image_raw, ["ImageWidth", "ExifImageWidth"])),
            "height": _to_int(_first_present(image_raw, ["ImageHeight", "ExifImageHeight"])),
            "file_type": image_raw.get("FileType"),
        },
        "video": {
            "content_identifier": video_identifier,
            "duration": _to_float(video_raw.get("Duration")),
            "still_image_time": _value_or_none(video_raw.get("StillImageTime")),
            "width": _to_int(_first_present(video_raw, ["ImageWidth", "SourceImageWidth"])),
            "height": _to_int(_first_present(video_raw, ["ImageHeight", "SourceImageHeight"])),
            "rotation": _value_or_none(video_raw.get("Rotation")),
            "file_type": video_raw.get("FileType"),
        },
    }


def _ensure_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError("{0} file does not exist: {1}".format(label, path))
    if not path.is_file():
        raise ValueError("{0} path is not a file: {1}".format(label, path))


def _first_present(raw: Dict[str, Any], keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = raw.get(key)
        if value is None or value == "":
            continue
        return str(value)
    return None


def _has_apple_makernotes(raw: Dict[str, Any]) -> bool:
    return any(key.startswith("MakerNoteApple") or key.startswith("Apple") for key in raw)


def _apple_live_status(image_identifier: Optional[str], video_identifier: Optional[str], identifiers_match: bool) -> str:
    if identifiers_match:
        return "metadata_match"
    if image_identifier or video_identifier:
        return "metadata_mismatch"
    return "no_live_metadata"


def _value_or_none(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    return str(value)


def _to_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
