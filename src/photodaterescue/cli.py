"""Command-line interface for PhotoDateRescue."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from .android_pull import AdbMissingError, android_pull
from .doctor import run_doctor
from .live_build import build_live_photos
from .live_inspect import inspect_live_pair
from .live_probe import probe_live_pairs
from .live_workflow import run_live_workflow
from .metadata import ExifToolClient, ExifToolMissingError
from .motion import audit_motion_directory
from .motion_extract import extract_motion_photos
from .reconcile import reconcile_directories
from .repair import repair_directory
from .reports import write_reports
from .scan import analyze_directory
from .unmatched import classify_unmatched_rows, materialize_unmatched_rows
from .wizard import run_wizard


def add_path_filter_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="PATTERN",
        help="可重复的相对路径包含过滤器，支持目录前缀或 glob。",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="可重复的相对路径排除过滤器，用于跳过缓存或不需要处理的目录。",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="photodaterescue",
        description="扫描相册导出目录，并在不改动源文件的前提下生成安全修复副本。",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("doctor", help="检查本机依赖")
    subparsers.add_parser("wizard", help="运行中文终端向导")

    android_pull_parser = subparsers.add_parser(
        "android-pull",
        help="使用 adb pull -a 导出安卓媒体目录并尽量保留文件时间",
    )
    android_pull_parser.add_argument(
        "--device-path",
        action="append",
        required=True,
        help="要导出的安卓绝对路径，可重复传入 /sdcard/DCIM、/sdcard/Pictures 等。",
    )
    android_pull_parser.add_argument("--output", required=True, help="本地导出目录")
    android_pull_parser.add_argument(
        "--adb",
        default="adb",
        help="adb 可执行文件路径或命令名，默认使用 PATH 中的 adb。",
    )
    android_pull_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印 adb 命令，不实际执行。",
    )

    scan_parser = subparsers.add_parser("scan", help="扫描媒体目录并写出报告")
    scan_parser.add_argument("--input", required=True, help="要扫描的媒体目录")
    scan_parser.add_argument("--report", required=True, help="报告输出目录")
    add_path_filter_arguments(scan_parser)

    motion_parser = subparsers.add_parser(
        "motion-audit",
        help="只读审计疑似安卓动态照片 / Live Photo 候选",
    )
    motion_parser.add_argument("--input", required=True, help="要审计的媒体目录")
    motion_parser.add_argument("--report", required=True, help="动态照片审计报告目录")
    add_path_filter_arguments(motion_parser)

    motion_extract_parser = subparsers.add_parser(
        "motion-extract",
        help="从嵌入式 JPEG 动态照片中提取视频并生成配对",
    )
    motion_extract_parser.add_argument("--candidates-csv", required=True, help="motion-audit 生成的 motion_candidates.csv 路径")
    motion_extract_parser.add_argument(
        "--source-root",
        required=True,
        help="用于解析 motion_candidates.csv 中相对路径的源目录",
    )
    motion_extract_parser.add_argument("--output", required=True, help="提取后配对文件输出目录")
    motion_extract_parser.add_argument("--report", required=True, help="提取报告目录")
    motion_extract_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只验证提取计划，不写出媒体文件。",
    )

    live_build_parser = subparsers.add_parser(
        "live-build",
        help="从图片 / 视频配对生成 Apple Live Photo 兼容输出副本",
    )
    live_build_parser.add_argument("--pairs-csv", required=True, help="motion-audit 生成的 pairs.csv 路径")
    live_build_parser.add_argument("--source-root", required=True, help="用于解析 pairs.csv 中相对路径的源目录")
    live_build_parser.add_argument("--output", required=True, help="Live Photo 配对副本输出目录")
    live_build_parser.add_argument("--report", required=True, help="live-build 报告目录")
    live_build_parser.add_argument(
        "--backend",
        choices=["makelive", "portable-pair"],
        default="makelive",
        help="Live Photo 输出后端：makelive 写 Apple 元数据；portable-pair 只生成跨平台配对包。",
    )
    live_build_parser.add_argument(
        "--makelive",
        default="makelive",
        help="makelive 可执行文件路径或命令名，默认使用 PATH 中的 makelive。",
    )
    live_build_parser.add_argument(
        "--include-uncertain",
        action="store_true",
        help="同时处理 uncertain_candidate 行，默认关闭。",
    )
    live_build_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只验证可处理配对和计划输出，不复制文件、不写元数据。",
    )

    live_inspect_parser = subparsers.add_parser(
        "live-inspect",
        help="只读检查一对图片 / 视频是否包含 Live Photo 配对元数据",
    )
    live_inspect_parser.add_argument("--image", required=True, help="要检查的静态图片路径")
    live_inspect_parser.add_argument("--video", required=True, help="要检查的短视频路径")

    live_probe_parser = subparsers.add_parser(
        "live-probe",
        help="批量只读检查 pairs.csv 中的 Live Photo 元数据信号",
    )
    live_probe_parser.add_argument("--pairs-csv", required=True, help="motion-audit 生成的 pairs.csv 路径")
    live_probe_parser.add_argument("--source-root", required=True, help="用于解析 pairs.csv 中相对路径的源目录")
    live_probe_parser.add_argument("--report", required=True, help="live-probe 报告输出目录")

    rescue_live_parser = subparsers.add_parser(
        "rescue-live",
        help="安全串联 motion-audit、motion-extract 和 live-build",
    )
    rescue_live_parser.add_argument("--input", required=True, help="安卓媒体导出目录")
    rescue_live_parser.add_argument("--work-dir", required=True, help="中间报告和提取配对目录")
    rescue_live_parser.add_argument("--output", required=True, help="最终 Live Photo 配对副本输出目录")
    rescue_live_parser.add_argument(
        "--makelive",
        default="makelive",
        help="makelive 可执行文件路径或命令名，默认使用 PATH 中的 makelive。",
    )
    rescue_live_parser.add_argument(
        "--include-uncertain",
        action="store_true",
        help="同时处理 uncertain_candidate 行，默认关闭。",
    )
    rescue_live_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只写报告和计划，不提取、不复制、不写元数据。",
    )
    add_path_filter_arguments(rescue_live_parser)

    repair_parser = subparsers.add_parser("repair", help="生成修复后的媒体副本和报告")
    repair_parser.add_argument("--input", required=True, help="要扫描的媒体目录")
    repair_parser.add_argument("--output", required=True, help="修复副本输出目录")
    repair_parser.add_argument("--report", required=True, help="报告输出目录")
    repair_parser.add_argument(
        "--copy-all",
        action="store_true",
        help="把原本正常的文件也复制到输出目录。",
    )
    add_path_filter_arguments(repair_parser)

    reconcile_parser = subparsers.add_parser("reconcile", help="对比候选导出目录和已修复基线目录")
    reconcile_parser.add_argument("--candidate", required=True, help="待审计的候选目录")
    reconcile_parser.add_argument("--baseline", required=True, help="已确认较好的修复基线目录")
    reconcile_parser.add_argument("--report", required=True, help="对账报告目录")

    classify_parser = subparsers.add_parser(
        "classify-unmatched",
        help="把 reconcile 的 unmatched 行分类为保留、人工检查或疑似重复",
    )
    classify_parser.add_argument(
        "--report",
        required=True,
        help="包含 unmatched.csv 的 reconcile 报告目录",
    )
    classify_parser.add_argument("--baseline", required=True, help="已确认较好的修复基线目录")
    classify_parser.add_argument(
        "--output",
        help="可选分类输出目录，默认使用 reconcile 报告目录。",
    )

    materialize_parser = subparsers.add_parser(
        "materialize-unmatched",
        help="把分类后的剩余文件复制或移动到实体分类目录",
    )
    materialize_parser.add_argument(
        "--classified-csv",
        required=True,
        help="unmatched-classified.csv 或等价分类 CSV 路径",
    )
    materialize_parser.add_argument(
        "--output-root",
        required=True,
        help="分类目录和日志的输出根目录",
    )
    materialize_parser.add_argument(
        "--mode",
        choices=["copy", "move"],
        default="copy",
        help="如何实体化文件，默认 copy 更安全。",
    )
    materialize_parser.add_argument(
        "--source-root",
        help="可选源目录，用于解析分类 CSV 中的相对候选路径。",
    )

    return parser


def _path_exists_for_cli(value: str) -> bool:
    try:
        return Path(value).expanduser().exists()
    except OSError:
        return False


def _has_missing_existing_path_args(*values: str) -> bool:
    return any(not _path_exists_for_cli(value) for value in values)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if args.command is None:
        try:
            parser.print_help()
            return 0
        except SystemExit as exc:
            return int(exc.code)

    if args.command == "doctor":
        return run_doctor()

    if args.command == "wizard":
        result = run_wizard()
        if result.message:
            print(result.message)
        return 0 if result.completed else 1

    if args.command == "android-pull":
        try:
            result = android_pull(
                device_paths=args.device_path,
                output=Path(args.output),
                adb_path=args.adb,
                dry_run=args.dry_run,
            )
        except AdbMissingError:
            print("adb is required for android-pull. Install Android platform-tools or pass --adb /path/to/adb.")
            return 1
        except ValueError as exc:
            print(str(exc))
            return 2

        if result.dry_run:
            print("Dry run. Commands:")
            for command in result.commands:
                print(" ".join(command))
        else:
            print("Android pull complete: roots={0} output={1}".format(len(result.pulled_roots), result.output))
        return 0

    if args.command == "live-build":
        try:
            result = build_live_photos(
                pairs_csv=Path(args.pairs_csv),
                source_root=Path(args.source_root),
                output=Path(args.output),
                report_dir=Path(args.report),
                backend=args.backend,
                makelive_path=args.makelive,
                include_uncertain=args.include_uncertain,
                dry_run=args.dry_run,
            )
        except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
            print(str(exc))
            return 2
        print(
            "Live build complete: planned={0} built={1} skipped={2} errors={3}".format(
                result.planned_count,
                result.built_count,
                result.skipped_count,
                result.error_count,
            )
        )
        print("Manifest: {0}".format(result.manifest_path))
        return 0

    if args.command == "live-inspect":
        if _has_missing_existing_path_args(args.image, args.video):
            try:
                inspect_live_pair(Path(args.image), Path(args.video), ExifToolClient(exiftool_path="exiftool"))
            except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
                print(str(exc))
                return 2
        client = ExifToolClient()
        if not client.is_available():
            print("exiftool is required. Run `photodaterescue doctor` for details.")
            return 1
        try:
            result = inspect_live_pair(Path(args.image), Path(args.video), client)
        except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
            print(str(exc))
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "live-probe":
        client = ExifToolClient()
        if not client.is_available():
            print("exiftool is required. Run `photodaterescue doctor` for details.")
            return 1
        try:
            result = probe_live_pairs(
                pairs_csv=Path(args.pairs_csv),
                source_root=Path(args.source_root),
                report_dir=Path(args.report),
                client=client,
            )
        except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
            print(str(exc))
            return 2
        print(
            "Live probe complete: total={0} metadata_match={1} metadata_blocked={2} errors={3}".format(
                result.total_count,
                result.metadata_match_count,
                result.metadata_blocked_count,
                result.error_count,
            )
        )
        print("Manifest: {0}".format(result.manifest_path))
        return 0

    if args.command == "motion-extract" and not _path_exists_for_cli(args.candidates_csv):
        print("Motion candidates CSV does not exist: {0}".format(Path(args.candidates_csv)))
        return 2

    client = ExifToolClient()
    if not client.is_available():
        print("exiftool is required. Run `photodaterescue doctor` for details.")
        return 1

    if args.command == "scan":
        input_dir = Path(args.input)
        report_dir = Path(args.report)
        records = analyze_directory(
            input_dir,
            client,
            include_patterns=args.include,
            exclude_patterns=args.exclude,
        )
        write_reports(records, report_dir)
        print("Scanned {0} files into {1}".format(len(records), report_dir))
        return 0

    if args.command == "motion-audit":
        result = audit_motion_directory(
            root=Path(args.input),
            report_dir=Path(args.report),
            client=client,
            include_patterns=args.include,
            exclude_patterns=args.exclude,
        )
        print(
            "Motion audit complete: files={0} supported={1} candidates={2} pairs={3} embedded={4} uncertain={5} errors={6}".format(
                result.total_files,
                result.supported_files,
                result.candidate_count,
                result.pair_count,
                result.embedded_candidate_count,
                result.uncertain_candidate_count,
                result.error_count,
            )
        )
        print("Summary: {0}".format(result.summary_path))
        return 0

    if args.command == "motion-extract":
        try:
            result = extract_motion_photos(
                candidates_csv=Path(args.candidates_csv),
                source_root=Path(args.source_root),
                output=Path(args.output),
                report_dir=Path(args.report),
                client=client,
                dry_run=args.dry_run,
            )
        except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
            print(str(exc))
            return 2
        print(
            "Motion extract complete: planned={0} extracted={1} skipped={2} errors={3}".format(
                result.planned_count,
                result.extracted_count,
                result.skipped_count,
                result.error_count,
            )
        )
        print("Manifest: {0}".format(result.manifest_path))
        return 0

    if args.command == "rescue-live":
        try:
            result = run_live_workflow(
                input_root=Path(args.input),
                work_dir=Path(args.work_dir),
                output=Path(args.output),
                client=client,
                include_patterns=args.include,
                exclude_patterns=args.exclude,
                makelive_path=args.makelive,
                include_uncertain=args.include_uncertain,
                dry_run=args.dry_run,
            )
        except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
            print(str(exc))
            return 2
        print(
            "Live rescue workflow complete: audit_pairs={0} embedded={1} live_planned={2} live_built={3} errors={4}".format(
                result.audit.pair_count,
                result.audit.embedded_candidate_count,
                result.planned_count,
                result.built_count,
                result.error_count,
            )
        )
        print("Manifest: {0}".format(result.manifest_path))
        return 0

    if args.command == "repair":
        input_dir = Path(args.input)
        output_dir = Path(args.output)
        report_dir = Path(args.report)
        result = repair_directory(
            source=input_dir,
            output=output_dir,
            report_dir=report_dir,
            client=client,
            copy_all=args.copy_all,
            include_patterns=args.include,
            exclude_patterns=args.exclude,
        )
        print(
            "Repair complete: copied={0} repaired={1} failed={2} skipped={3}".format(
                result.copied,
                result.repaired,
                result.failed,
                result.skipped,
            )
        )
        print("Manifest: {0}".format(result.manifest_path))
        return 0

    if args.command == "reconcile":
        result = reconcile_directories(
            candidate=Path(args.candidate),
            baseline=Path(args.baseline),
            report_dir=Path(args.report),
        )
        print(
            "Reconcile complete: candidate={0} baseline={1} matched={2} unmatched={3} candidate_errors={4} baseline_errors={5}".format(
                result.candidate_total,
                result.baseline_total,
                result.matched_count,
                result.unmatched_count,
                result.candidate_error_count,
                result.baseline_error_count,
            )
        )
        print("Summary: {0}".format(result.summary_path))
        return 0

    if args.command == "classify-unmatched":
        result = classify_unmatched_rows(
            report_dir=Path(args.report),
            baseline=Path(args.baseline),
            output_dir=Path(args.output) if args.output else None,
        )
        print(
            "Classify complete: rows={0} baseline={1} baseline_errors={2} recommended_keep={3} manual_review={4} high_suspected_duplicate={5}".format(
                result.total_rows,
                result.baseline_total,
                result.baseline_error_count,
                result.category_counts.get("recommended_keep", 0),
                result.category_counts.get("manual_review", 0),
                result.category_counts.get("high_suspected_duplicate", 0),
            )
        )
        print("Classified CSV: {0}".format(result.classified_csv_path))
        return 0

    if args.command == "materialize-unmatched":
        result = materialize_unmatched_rows(
            classified_csv=Path(args.classified_csv),
            output_root=Path(args.output_root),
            mode=args.mode,
            source_root=Path(args.source_root) if args.source_root else None,
        )
        print(
            "Materialize complete: processed={0} errors={1} recommended_keep={2} manual_review={3} high_suspected_duplicate={4}".format(
                result.processed_count,
                result.error_count,
                result.category_counts.get("recommended_keep", 0),
                result.category_counts.get("manual_review", 0),
                result.category_counts.get("high_suspected_duplicate", 0),
            )
        )
        print("Summary: {0}".format(result.summary_path))
        return 0

    parser.error("Unknown command: {0}".format(args.command))
    return 2
