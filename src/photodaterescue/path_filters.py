"""Helpers for filtering files by relative path patterns."""

from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Iterable, Tuple


def normalize_patterns(patterns: Iterable[str] | None) -> Tuple[str, ...]:
    if not patterns:
        return ()

    normalized = []
    for pattern in patterns:
        cleaned = pattern.strip().replace("\\", "/").strip()
        if cleaned:
            normalized.append(cleaned.rstrip("/") or ".")
    return tuple(normalized)


def should_include_path(
    relative_path: Path,
    include_patterns: Iterable[str] | None = None,
    exclude_patterns: Iterable[str] | None = None,
) -> bool:
    relative_posix = PurePosixPath(relative_path.as_posix())
    includes = normalize_patterns(include_patterns)
    excludes = normalize_patterns(exclude_patterns)

    if includes and not any(_matches_pattern(relative_posix, pattern) for pattern in includes):
        return False

    if excludes and any(_matches_pattern(relative_posix, pattern) for pattern in excludes):
        return False

    return True


def _matches_pattern(relative_path: PurePosixPath, pattern: str) -> bool:
    path_value = relative_path.as_posix()
    wildcard_pattern = pattern

    if pattern in {".", "*", "**"}:
        return True

    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path_value == prefix or path_value.startswith(prefix + "/")

    if not _has_glob(pattern):
        return path_value == pattern or path_value.startswith(pattern + "/")

    return relative_path.match(wildcard_pattern) or fnmatchcase(path_value, wildcard_pattern)


def _has_glob(pattern: str) -> bool:
    return any(character in pattern for character in "*?[")
