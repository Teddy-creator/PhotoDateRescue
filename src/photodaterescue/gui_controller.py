"""Display-independent controller for the beginner macOS GUI."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Union

from .gui_models import DependencyStatus, GuiRepairSummary, GuiScanSummary
from .metadata import ExifToolClient
from .models import ScanStatus
from .repair import repair_directory
from .reports import write_reports
from .scan import analyze_directory
from .tools import find_tool
from .wizard_defaults import DEFAULT_EXCLUDES, build_output_layout

PathInput = Union[str, Path]


class GuiValidationError(ValueError):
    """Raised when GUI user input is invalid."""


class PhotoDateRescueGuiController:
    def check_dependencies(self) -> list[DependencyStatus]:
        exiftool_path = find_tool("exiftool")
        ffmpeg_path = find_tool("ffmpeg")
        ffprobe_path = find_tool("ffprobe")
        return [
            DependencyStatus(
                name="ExifTool",
                available=bool(exiftool_path),
                path=exiftool_path,
                required=True,
                hint="缺少 ExifTool，无法可靠读取照片和视频时间信息。",
            ),
            DependencyStatus(
                name="FFmpeg",
                available=bool(ffmpeg_path and ffprobe_path),
                path=ffmpeg_path or ffprobe_path,
                required=False,
                hint="缺少 FFmpeg 时，部分视频信息可能无法完整处理。",
            ),
        ]

    def validate_required_dependencies(self) -> None:
        missing = [status for status in self.check_dependencies() if status.required and not status.available]
        if not missing:
            return
        lines = [
            "缺少必需依赖：{0}".format(", ".join(status.name for status in missing)),
            "",
            "PhotoDateRescue 需要 ExifTool 来读取照片和视频时间信息。",
            "请先安装 ExifTool，再重新打开本工具。",
            "",
            "macOS 推荐安装命令：brew install exiftool",
        ]
        raise GuiValidationError("\n".join(lines))

    def suggest_output_folder(self, source: PathInput) -> Path:
        source = self._coerce_path(source, "请选择安卓照片 / 视频导出文件夹。")
        return source.with_name("{0}-PhotoDateRescue-output".format(source.name))

    def validate_folders(self, source: PathInput, output_base: PathInput) -> None:
        source = self._coerce_path(source, "请选择安卓照片 / 视频导出文件夹。")
        output_base = self._coerce_path(output_base, "请选择安全输出文件夹。")
        if not source.exists() or not source.is_dir():
            raise GuiValidationError("源文件夹不存在，请重新选择安卓照片 / 视频导出目录。")
        if source.resolve() == output_base.resolve():
            raise GuiValidationError("输出文件夹不能和源文件夹相同，请选择一个单独的安全输出目录。")
        output_base.mkdir(parents=True, exist_ok=True)
        if not output_base.is_dir():
            raise GuiValidationError("输出路径不是文件夹，请重新选择。")

    def scan(self, source: PathInput, output_base: PathInput) -> GuiScanSummary:
        self.validate_required_dependencies()
        self.validate_folders(source, output_base)
        source = self._coerce_path(source, "请选择安卓照片 / 视频导出文件夹。")
        output_base = self._coerce_path(output_base, "请选择安全输出文件夹。")
        layout = build_output_layout(output_base)
        client = ExifToolClient()
        records = analyze_directory(source, client, exclude_patterns=DEFAULT_EXCLUDES)
        write_reports(records, layout.scan_report)
        status_counts = Counter(record.status for record in records)
        media_counts = Counter(record.media_kind or "unknown" for record in records)
        return GuiScanSummary(
            total_files=len(records),
            photo_files=media_counts.get("image", 0),
            video_files=media_counts.get("video", 0),
            repairable_files=status_counts.get(ScanStatus.REPAIRABLE, 0),
            ok_files=status_counts.get(ScanStatus.OK, 0),
            high_risk_files=status_counts.get(ScanStatus.HIGH_RISK, 0),
            unsupported_files=status_counts.get(ScanStatus.UNSUPPORTED, 0),
            error_files=status_counts.get(ScanStatus.ERROR, 0),
            report_dir=layout.scan_report,
        )

    def repair(self, source: PathInput, output_base: PathInput) -> GuiRepairSummary:
        self.validate_required_dependencies()
        self.validate_folders(source, output_base)
        source = self._coerce_path(source, "请选择安卓照片 / 视频导出文件夹。")
        output_base = self._coerce_path(output_base, "请选择安全输出文件夹。")
        layout = build_output_layout(output_base)
        client = ExifToolClient()
        result = repair_directory(
            source=source,
            output=layout.repaired_media,
            report_dir=layout.scan_report,
            client=client,
            exclude_patterns=DEFAULT_EXCLUDES,
        )
        return GuiRepairSummary(
            copied=result.copied,
            repaired=result.repaired,
            failed=result.failed,
            skipped=result.skipped,
            output_dir=layout.repaired_media,
        )

    def _coerce_path(self, value: PathInput, empty_message: str) -> Path:
        if isinstance(value, str) and not value.strip():
            raise GuiValidationError(empty_message)
        return Path(value).expanduser()
