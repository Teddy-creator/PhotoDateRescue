"""External tool discovery helpers."""

from __future__ import annotations

import os
import shutil
import sys
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
    """Find an external command, including platform-specific app locations."""

    resolved = shutil.which(name)
    if resolved:
        return resolved

    platform = current_platform()
    if platform.is_windows:
        adjacent = _find_windows_adjacent_tool(name)
        if adjacent:
            return adjacent

    if not platform.is_macos:
        return None

    for directory in MACOS_FALLBACK_TOOL_DIRS:
        candidate = directory / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def _find_windows_adjacent_tool(name: str) -> str | None:
    """Find tools placed next to the running Windows executable."""

    executable_dir = Path(sys.executable).resolve().parent
    names = [name]
    if not name.lower().endswith(".exe"):
        names.append("{0}.exe".format(name))

    for tool_name in names:
        candidate = executable_dir / tool_name
        if candidate.is_file():
            return str(candidate)
    return None
