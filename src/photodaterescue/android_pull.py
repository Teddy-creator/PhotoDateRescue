"""Android export helpers backed by adb pull -a."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass
class AndroidPullResult:
    output: Path
    commands: List[List[str]]
    pulled_roots: List[str]
    dry_run: bool = False


class AdbMissingError(RuntimeError):
    """Raised when adb is unavailable."""


def android_pull(
    device_paths: Sequence[str],
    output: Path,
    adb_path: str = "adb",
    dry_run: bool = False,
) -> AndroidPullResult:
    if not device_paths:
        raise ValueError("At least one --device-path is required")

    resolved_adb = _resolve_adb(adb_path)
    output = output.expanduser().resolve()
    if not dry_run:
        output.mkdir(parents=True, exist_ok=True)

    commands = []
    pulled_roots = []
    for device_path in device_paths:
        normalized_path = _normalize_device_path(device_path)
        command = [resolved_adb, "pull", "-a", normalized_path, str(output)]
        commands.append(command)
        pulled_roots.append(normalized_path)
        if not dry_run:
            subprocess.run(command, check=True)

    return AndroidPullResult(
        output=output,
        commands=commands,
        pulled_roots=pulled_roots,
        dry_run=dry_run,
    )


def _resolve_adb(adb_path: str) -> str:
    if "/" in adb_path or "\\" in adb_path or Path(adb_path).is_absolute():
        return adb_path
    resolved = shutil.which(adb_path)
    if not resolved:
        raise AdbMissingError("adb is not available on PATH")
    return resolved


def _normalize_device_path(value: str) -> str:
    cleaned = value.strip().rstrip("/")
    if not cleaned:
        raise ValueError("Device path cannot be empty")
    if not cleaned.startswith("/"):
        raise ValueError("Device path must be absolute, for example /sdcard/DCIM")
    return cleaned
