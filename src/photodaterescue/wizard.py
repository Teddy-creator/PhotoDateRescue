"""Guided terminal workflows for PhotoDateRescue."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Sequence

from .doctor import run_doctor
from .live_workflow import run_live_workflow
from .metadata import ExifToolClient
from .platforms import current_platform
from .repair import repair_directory
from .reports import build_summary, write_reports
from .scan import analyze_directory
from .wizard_defaults import DEFAULT_EXCLUDES, build_output_layout
from .wizard_prompts import TerminalPrompts, WizardPromptError


@dataclass
class WizardResult:
    mode: str
    completed: bool
    outputs: Dict[str, Path] = field(default_factory=dict)
    reports: Dict[str, Path] = field(default_factory=dict)
    message: str = ""


MAIN_CHOICES = (
    ("recommended", "推荐流程：先体检，再选择修复时间线 / 排查安卓动态照片"),
    ("repair", "只修复普通照片 / 视频的时间线"),
    ("live", "只处理安卓动态照片 / Live Photo（macOS 才构建 Apple Live Photo）"),
    ("doctor", "只检查本机环境"),
    ("exit", "退出"),
)

BUILD_CHOICES = (
    ("repair", "只生成修复时间线后的照片 / 视频副本"),
    ("live", "只生成 Live Photo 兼容输出（macOS）"),
    ("both", "两者都生成"),
    ("none", "暂不生成，只保留报告"),
)

BUILD_CHOICES_REPAIR_ONLY = (
    ("repair", "生成修复时间线后的照片 / 视频副本（推荐）"),
    ("none", "暂不生成，只保留报告"),
)


def run_wizard(prompts: Optional[object] = None, client: Optional[object] = None) -> WizardResult:
    prompts = prompts or TerminalPrompts()
    _print_banner()
    mode = prompts.choice("你想做什么？", MAIN_CHOICES, default="recommended")

    if mode == "exit":
        return WizardResult(mode="exit", completed=True, message="已退出，没有改动任何文件。")
    if mode == "doctor":
        exit_code = run_doctor()
        return WizardResult(
            mode="doctor",
            completed=exit_code == 0,
            message="环境检查完成。" if exit_code == 0 else "环境检查发现问题，请先按上面的提示补齐依赖。",
        )
    if mode == "repair":
        return _run_repair_flow(prompts, client)
    if mode == "live":
        return _run_live_flow(prompts, client)
    if mode == "recommended":
        return _run_recommended_flow(prompts, client)
    raise WizardPromptError("暂未实现的向导模式：{0}".format(mode))


def _run_repair_flow(prompts: object, client: Optional[object]) -> WizardResult:
    input_dir, layout, excludes = _ask_common_paths(prompts)

    doctor_exit = run_doctor()
    if doctor_exit != 0:
        return WizardResult(mode="repair", completed=False, message="环境检查发现问题，未写入任何媒体文件。")

    client = client or ExifToolClient()
    _run_scan_step(input_dir, layout.scan_report, client, excludes)

    if not prompts.confirm("现在生成修复后的照片 / 视频副本吗？", default=False):
        return WizardResult(
            mode="repair",
            completed=True,
            reports={"scan": layout.scan_report},
            message="已写入扫描报告；未生成修复媒体副本。",
        )

    result = repair_directory(
        source=input_dir,
        output=layout.repaired_media,
        report_dir=layout.scan_report,
        client=client,
        exclude_patterns=excludes,
    )
    return WizardResult(
        mode="repair",
        completed=result.failed == 0,
        outputs={"repaired_media": layout.repaired_media},
        reports={"scan": layout.scan_report, "manifest": result.manifest_path},
        message=(
            "修复完成：copied={0} repaired={1} failed={2} skipped={3}".format(
                result.copied,
                result.repaired,
                result.failed,
                result.skipped,
            )
        ),
    )


def _run_recommended_flow(prompts: object, client: Optional[object]) -> WizardResult:
    input_dir, layout, excludes = _ask_common_paths(prompts)
    platform = current_platform()

    doctor_exit = run_doctor()
    if doctor_exit != 0:
        return WizardResult(mode="recommended", completed=False, message="环境检查发现问题，未写入任何媒体文件。")

    client = client or ExifToolClient()
    _run_scan_step(input_dir, layout.scan_report, client, excludes)
    dry_run_result = None
    if platform.live_build_supported:
        dry_run_result = run_live_workflow(
            input_root=input_dir,
            work_dir=layout.live_work,
            output=layout.live_output,
            client=client,
            exclude_patterns=excludes,
            dry_run=True,
        )
        _print_live_summary(dry_run_result, dry_run=True)
        build_choice = prompts.choice("你想生成哪些输出？", BUILD_CHOICES, default="both")
    else:
        print("当前平台：{0}。本向导会跳过 Apple Live Photo 构建，只处理普通照片 / 视频时间线。".format(platform.label))
        print("如果需要动态照片排查，可单独使用 motion-audit / motion-extract / portable-pair 保留配对包。")
        build_choice = prompts.choice("你想生成哪些输出？", BUILD_CHOICES_REPAIR_ONLY, default="repair")

    if build_choice == "none":
        reports = {"scan": layout.scan_report}
        if dry_run_result is not None:
            reports["live_manifest"] = dry_run_result.manifest_path
        return WizardResult(
            mode="recommended",
            completed=True,
            reports=reports,
            message="已写入报告；未生成媒体输出。",
        )
    if not prompts.confirm("现在生成所选输出吗？", default=False):
        reports = {"scan": layout.scan_report}
        if dry_run_result is not None:
            reports["live_manifest"] = dry_run_result.manifest_path
        return WizardResult(
            mode="recommended",
            completed=True,
            reports=reports,
            message="已写入报告；未生成媒体输出。",
        )

    outputs: Dict[str, Path] = {}
    reports: Dict[str, Path] = {"scan": layout.scan_report}
    if dry_run_result is not None:
        reports["live_manifest"] = dry_run_result.manifest_path
    completed = True
    message_parts = []

    if build_choice in {"repair", "both"}:
        repair_result = repair_directory(
            source=input_dir,
            output=layout.repaired_media,
            report_dir=layout.scan_report,
            client=client,
            exclude_patterns=excludes,
        )
        outputs["repaired_media"] = layout.repaired_media
        reports["repair_manifest"] = repair_result.manifest_path
        completed = completed and repair_result.failed == 0
        message_parts.append(
            "时间线修复 copied={0} repaired={1} failed={2}".format(
                repair_result.copied,
                repair_result.repaired,
                repair_result.failed,
            )
        )

    if build_choice in {"live", "both"} and platform.live_build_supported:
        live_result = run_live_workflow(
            input_root=input_dir,
            work_dir=layout.live_work,
            output=layout.live_output,
            client=client,
            exclude_patterns=excludes,
            dry_run=False,
        )
        outputs["live_output"] = layout.live_output
        reports["live_manifest"] = live_result.manifest_path
        completed = completed and live_result.error_count == 0
        message_parts.append(
            "Live Photo planned={0} built={1} errors={2}".format(
                live_result.planned_count,
                live_result.built_count,
                live_result.error_count,
            )
        )

    return WizardResult(
        mode="recommended",
        completed=completed,
        outputs=outputs,
        reports=reports,
        message="推荐流程完成：{0}".format("; ".join(message_parts)),
    )


def _run_live_flow(prompts: object, client: Optional[object]) -> WizardResult:
    platform = current_platform()
    if not platform.live_build_supported:
        return WizardResult(
            mode="live",
            completed=False,
            message=(
                "当前平台是 {0}，不支持构建 Apple Photos 可识别的 Live Photo。"
                "建议先使用 scan/repair 修复普通照片和视频，或用 motion-audit / motion-extract / portable-pair 保留动态照片配对。"
            ).format(platform.label),
        )

    input_dir, layout, excludes = _ask_common_paths(prompts)

    doctor_exit = run_doctor()
    if doctor_exit != 0:
        return WizardResult(mode="live", completed=False, message="环境检查发现问题，未写入任何媒体文件。")

    client = client or ExifToolClient()
    dry_run_result = run_live_workflow(
        input_root=input_dir,
        work_dir=layout.live_work,
        output=layout.live_output,
        client=client,
        exclude_patterns=excludes,
        dry_run=True,
    )
    _print_live_summary(dry_run_result, dry_run=True)
    if dry_run_result.planned_count == 0:
        return WizardResult(
            mode="live",
            completed=True,
            reports={"live_manifest": dry_run_result.manifest_path},
            message="Live Photo 预检查没有发现计划可恢复的配对。",
        )
    if not prompts.confirm("现在生成 Live Photo 兼容输出吗？", default=False):
        return WizardResult(
            mode="live",
            completed=True,
            reports={"live_manifest": dry_run_result.manifest_path},
            message="已写入 Live Photo 预检查报告；未生成输出配对。",
        )

    build_result = run_live_workflow(
        input_root=input_dir,
        work_dir=layout.live_work,
        output=layout.live_output,
        client=client,
        exclude_patterns=excludes,
        dry_run=False,
    )
    _print_live_summary(build_result, dry_run=False)
    return WizardResult(
        mode="live",
        completed=build_result.error_count == 0,
        outputs={"live_output": layout.live_output},
        reports={"live_manifest": build_result.manifest_path},
        message="Live Photo 救援完成：planned={0} built={1} errors={2}".format(
            build_result.planned_count,
            build_result.built_count,
            build_result.error_count,
        ),
    )


def _ask_common_paths(prompts: object):
    input_dir = _ask_existing_directory(prompts, "安卓导出的原始媒体目录")
    output_base = Path(prompts.text("输出目录（建议新建一个空目录）")).expanduser()
    layout = build_output_layout(output_base)
    excludes = _ask_default_excludes(prompts)
    return input_dir, layout, excludes


def _ask_existing_directory(prompts: object, message: str) -> Path:
    while True:
        path = Path(prompts.text(message)).expanduser()
        if path.is_dir():
            return path
        print("目录不存在，请重新输入：{0}".format(path))


def _ask_default_excludes(prompts: object) -> tuple[str, ...]:
    if prompts.confirm("是否使用推荐的安卓缓存 / 回收站排除规则？", default=True):
        return DEFAULT_EXCLUDES
    return ()


def _run_scan_step(input_dir: Path, report_dir: Path, client: object, excludes: Sequence[str]) -> None:
    records = analyze_directory(
        input_dir,
        client,
        exclude_patterns=excludes,
    )
    write_reports(records, report_dir)
    summary = build_summary(records)
    _print_scan_summary(summary, report_dir)


def _print_scan_summary(summary: dict, report_dir: Path) -> None:
    status_counts = summary.get("status_counts", {})
    print("扫描完成。")
    print("  总文件数：{0}".format(summary.get("total_files", 0)))
    print("  可修复：{0}".format(status_counts.get("repairable", 0)))
    print("  高风险：{0}".format(status_counts.get("high_risk", 0)))
    print("  报告目录：{0}".format(report_dir))


def _print_live_summary(result: object, dry_run: bool) -> None:
    label = "Live Photo 预检查" if dry_run else "Live Photo 构建"
    source_counts = getattr(result, "extract_source_type_counts", {})
    print("{0}完成。".format(label))
    print("  直接配对：{0}".format(result.audit.pair_count))
    print("  嵌入式动态照片候选：{0}".format(result.audit.embedded_candidate_count))
    _print_extract_source_summary(source_counts)
    if dry_run:
        _print_live_next_step_hint(source_counts)
    print("  计划处理：{0}".format(result.planned_count))
    print("  已生成：{0}".format(result.built_count))
    print("  错误数：{0}".format(result.error_count))
    print("  manifest：{0}".format(result.manifest_path))


def _print_extract_source_summary(source_counts: dict) -> None:
    if not source_counts:
        return
    print("  嵌入式来源统计：")
    for source_type, counts in sorted(source_counts.items()):
        label = _source_type_label(source_type)
        print(
            "    {0}：planned={1} extracted={2} errors={3}".format(
                label,
                counts.get("planned", 0),
                counts.get("extracted", 0),
                counts.get("errors", 0),
            )
        )


def _source_type_label(source_type: str) -> str:
    labels = {
        "xiaomi_native_camera": "小米原生相机动态照片",
        "generic_embedded_motion": "通用 Motion/MicroVideo 候选",
        "embedded_motion": "嵌入式动态照片候选",
    }
    return labels.get(source_type, source_type)


def _print_live_next_step_hint(source_counts: dict) -> None:
    xiaomi_counts = source_counts.get("xiaomi_native_camera", {})
    xiaomi_planned = xiaomi_counts.get("planned", 0) + xiaomi_counts.get("extracted", 0)
    if xiaomi_planned <= 0:
        return
    print("  提示：小米原生相机动态照片可提取出静态图 + 短视频配对；")
    print("        这有助于保留动态照片内容，但不等于 Apple Photos 一定识别为 Live Photo。")


def _print_banner() -> None:
    print("PhotoDateRescue 向导")
    print("安全原则：不修改源文件，不自动导入 Apple Photos，不自动删除。")
