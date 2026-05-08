"""External tool discovery helpers."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from .platforms import current_platform


MACOS_FALLBACK_TOOL_DIRS = (
    Path("/opt/homebrew/bin"),
    Path("/usr/local/bin"),
    Path("/usr/bin"),
    Path("/bin"),
    Path("/usr/sbin"),
    Path("/sbin"),
)


def find_tool(name: str) -> str | None:
    """Find an external command, including common macOS GUI app locations."""

    resolved = shutil.which(name)
    if resolved:
        return resolved

    if not current_platform().is_macos:
        return None

    for directory in MACOS_FALLBACK_TOOL_DIRS:
        candidate = directory / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None
