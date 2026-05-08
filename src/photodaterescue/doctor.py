"""Environment checks."""

from __future__ import annotations

import sys
from typing import List

from .platforms import (
    adb_install_hint,
    current_platform,
    exiftool_install_hint,
    ffmpeg_install_hint,
    makelive_install_hint,
)
from .tools import find_tool


def run_doctor() -> int:
    platform = current_platform()
    python_ok = sys.version_info >= (3, 9)
    exiftool_path = find_tool("exiftool")
    ffprobe_path = find_tool("ffprobe")
    ffmpeg_path = find_tool("ffmpeg")
    adb_path = find_tool("adb")
    makelive_path = find_tool("makelive")

    print("platform: {0}".format(platform.label))
    print("python: {0}".format("ok" if python_ok else "unsupported"))
    print("python_version: {0}".format(sys.version.split()[0]))
    print("exiftool: {0}".format("ok" if exiftool_path else "missing"))
    if exiftool_path:
        print("exiftool_path: {0}".format(exiftool_path))
    else:
        print(exiftool_install_hint(platform))
    print("ffprobe: {0}".format("ok" if ffprobe_path else "missing"))
    if ffprobe_path:
        print("ffprobe_path: {0}".format(ffprobe_path))
    else:
        print(ffmpeg_install_hint(platform))
    print("ffmpeg: {0}".format("ok" if ffmpeg_path else "missing"))
    if ffmpeg_path:
        print("ffmpeg_path: {0}".format(ffmpeg_path))
    else:
        print(ffmpeg_install_hint(platform))
    print("adb: {0}".format("ok" if adb_path else "missing"))
    if adb_path:
        print("adb_path: {0}".format(adb_path))
    else:
        print(adb_install_hint(platform))
    print("makelive: {0}".format("ok" if makelive_path else "missing"))
    if makelive_path:
        print("makelive_path: {0}".format(makelive_path))
    else:
        print(makelive_install_hint(platform))
    if platform.is_windows:
        print("windows_note: 当前 Windows 重点支持 scan/repair/android-pull 和普通照片 / 视频修复；动态照片只支持审计、提取和 portable-pair 配对包，不支持构建 Apple Live Photo。")

    return 0 if python_ok and exiftool_path else 1
