"""Filesystem discovery helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from .formats import media_kind_from_extension, normalize_extension
from .models import DiscoveredFile
from .path_filters import should_include_path


def discover_files(
    root: Path,
    include_patterns: Iterable[str] | None = None,
    exclude_patterns: Iterable[str] | None = None,
) -> List[DiscoveredFile]:
    root = root.expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError("Input directory does not exist: {0}".format(root))
    if not root.is_dir():
        raise NotADirectoryError("Input path is not a directory: {0}".format(root))

    discovered = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative_path = path.relative_to(root)
        if not should_include_path(
            relative_path=relative_path,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        ):
            continue
        extension = path.suffix.lower()
        normalized_extension = normalize_extension(extension)
        discovered.append(
            DiscoveredFile(
                absolute_path=path,
                relative_path=relative_path,
                extension=extension,
                has_supported_extension=normalized_extension is not None,
                path_media_kind=media_kind_from_extension(extension),
            )
        )
    return discovered
