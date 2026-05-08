"""Shared file-format normalization helpers."""

from __future__ import annotations

from typing import Optional

MEDIA_KIND_IMAGE = "image"
MEDIA_KIND_VIDEO = "video"

_IMAGE_EXTENSION_MAP = {
    "jpg": ".jpg",
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
    "heic": ".heic",
    "heif": ".heif",
}

_VIDEO_EXTENSION_MAP = {
    "mp4": ".mp4",
    "mov": ".mov",
    "m4v": ".m4v",
    "3gp": ".3gp",
}

_EXTENSION_MAP = {
    **_IMAGE_EXTENSION_MAP,
    **_VIDEO_EXTENSION_MAP,
}

_MEDIA_KIND_BY_EXTENSION = {
    **{value: MEDIA_KIND_IMAGE for value in _IMAGE_EXTENSION_MAP.values()},
    **{value: MEDIA_KIND_VIDEO for value in _VIDEO_EXTENSION_MAP.values()},
}

SUPPORTED_EXTENSIONS = set(_EXTENSION_MAP.values())


def normalize_extension(value: str | None) -> Optional[str]:
    if not value:
        return None
    normalized = value.lower().lstrip(".")
    return _EXTENSION_MAP.get(normalized)


def is_supported_metadata_extension(value: str | None) -> bool:
    return normalize_extension(value) is not None


def media_kind_from_extension(value: str | None) -> Optional[str]:
    normalized = normalize_extension(value)
    if normalized is None:
        return None
    return _MEDIA_KIND_BY_EXTENSION.get(normalized)


def resolve_supported_extension(
    path_extension: str | None,
    metadata_extension: str | None,
) -> Optional[str]:
    metadata_supported = normalize_extension(metadata_extension)
    if metadata_supported is not None:
        return metadata_supported

    if metadata_extension:
        return None

    return normalize_extension(path_extension)


def resolve_media_kind(
    path_extension: str | None,
    metadata_extension: str | None,
) -> Optional[str]:
    supported_extension = resolve_supported_extension(path_extension, metadata_extension)
    if supported_extension is None:
        return None
    return media_kind_from_extension(supported_extension)
