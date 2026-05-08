"""Platform detection and user-facing capability hints."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformInfo:
    system: str
    is_macos: bool
    is_windows: bool
    is_linux: bool

    @property
    def label(self) -> str:
        if self.is_macos:
            return "macOS"
        if self.is_windows:
            return "Windows"
        if self.is_linux:
            return "Linux"
        return self.system or "unknown"

    @property
    def live_build_supported(self) -> bool:
        # Apple Live Photo metadata writing currently depends on a macOS
        # makelive workflow. Other platforms can still scan, repair, audit,
        # extract, and preserve dynamic-photo pairs as portable packages.
        return self.is_macos


def current_platform() -> PlatformInfo:
    system = os.environ.get("PHOTODATERESCUE_PLATFORM_OVERRIDE") or sys.platform
    normalized = system.lower()
    return PlatformInfo(
        system=system,
        is_macos=normalized == "darwin",
        is_windows=normalized.startswith("win"),
        is_linux=normalized.startswith("linux"),
    )


def exiftool_install_hint(platform: PlatformInfo) -> str:
    if platform.is_macos:
        return "hint: macOS 可用 `brew install exiftool` 安装。"
    if platform.is_windows:
        return "hint: Windows 可下载 ExifTool 并把 exiftool.exe 加入 PATH。"
    return "hint: 请先安装 ExifTool，并确保 `exiftool` 在 PATH 中。"


def ffmpeg_install_hint(platform: PlatformInfo) -> str:
    if platform.is_macos:
        return "hint: macOS 可用 `brew install ffmpeg` 安装。"
    if platform.is_windows:
        return "hint: Windows 可用 winget/choco/scoop 安装 FFmpeg，或手动加入 PATH。"
    return "hint: 请安装 FFmpeg，并确保 `ffmpeg` / `ffprobe` 在 PATH 中。"


def adb_install_hint(platform: PlatformInfo) -> str:
    if platform.is_windows:
        return "hint: Windows 请安装 Android SDK Platform-Tools，并把 adb.exe 加入 PATH。"
    return "hint: install Android platform-tools for `photodaterescue android-pull`"


def makelive_install_hint(platform: PlatformInfo) -> str:
    if platform.live_build_supported:
        return "hint: install makelive for optional `photodaterescue live-build` support on macOS"
    return "hint: 当前平台不支持构建 Apple Live Photo；可先使用 scan/repair/motion-audit/motion-extract/portable-pair。"
