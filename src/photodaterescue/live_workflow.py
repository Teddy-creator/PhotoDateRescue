"""Orchestrate Motion Photo audit, extraction, and Live Photo build steps."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .live_build import BackendRunner, LiveBuildResult, build_live_photos
from .metadata import ExifToolClient
from .motion import MotionAuditResult, audit_motion_directory
from .motion_extract import MotionExtractResult, extract_motion_photos


@dataclass
class LiveWorkflowResult:
    audit: MotionAuditResult
    extract: MotionExtractResult
    direct_build: LiveBuildResult
    extracted_build: LiveBuildResult
    manifest_path: Path

    @property
    def planned_count(self) -> int:
        return self.direct_build.planned_count + self.extracted_build.planned_count

    @property
    def built_count(self) -> int:
        return self.direct_build.built_count + self.extracted_build.built_count

    @property
    def error_count(self) -> int:
        return self.audit.error_count + self.extract.error_count + self.direct_build.error_count + self.extracted_build.error_count


def run_live_workflow(
    input_root: Path,
    work_dir: Path,
    output: Path,
    client: ExifToolClient,
    include_patterns: Iterable[str] | None = None,
    exclude_patterns: Iterable[str] | None = None,
    makelive_path: str = "makelive",
    include_uncertain: bool = False,
    dry_run: bool = False,
    backend_runner: Optional[BackendRunner] = None,
) -> LiveWorkflowResult:
    input_root = input_root.expanduser().resolve()
    work_dir = work_dir.expanduser().resolve()
    output = output.expanduser().resolve()

    audit_report_dir = work_dir / "motion-audit"
    extracted_motion_dir = work_dir / "extracted-motion"
    extract_report_dir = work_dir / "motion-extract"
    direct_report_dir = work_dir / "live-build-direct"
    extracted_report_dir = work_dir / "live-build-extracted"
    direct_output = output / "direct"
    extracted_output = output / "extracted"

    work_dir.mkdir(parents=True, exist_ok=True)

    audit = audit_motion_directory(
        root=input_root,
        report_dir=audit_report_dir,
        client=client,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    )
    extract = extract_motion_photos(
        candidates_csv=audit.candidates_path,
        source_root=input_root,
        output=extracted_motion_dir,
        report_dir=extract_report_dir,
        client=client,
        dry_run=dry_run,
    )
    direct_build = build_live_photos(
        pairs_csv=audit.pairs_path,
        source_root=input_root,
        output=direct_output,
        report_dir=direct_report_dir,
        makelive_path=makelive_path,
        include_uncertain=include_uncertain,
        dry_run=dry_run,
        backend_runner=backend_runner,
    )
    extracted_build = build_live_photos(
        pairs_csv=extract.pairs_path,
        source_root=extracted_motion_dir,
        output=extracted_output,
        report_dir=extracted_report_dir,
        makelive_path=makelive_path,
        include_uncertain=include_uncertain,
        dry_run=dry_run,
        backend_runner=backend_runner,
        validate_sources=not dry_run,
    )

    manifest_path = work_dir / "rescue-live-manifest.json"
    result = LiveWorkflowResult(
        audit=audit,
        extract=extract,
        direct_build=direct_build,
        extracted_build=extracted_build,
        manifest_path=manifest_path,
    )
    manifest_path.write_text(
        json.dumps(_manifest(result, input_root, work_dir, output, extracted_motion_dir, dry_run), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return result


def _manifest(
    result: LiveWorkflowResult,
    input_root: Path,
    work_dir: Path,
    output: Path,
    extracted_motion_dir: Path,
    dry_run: bool,
) -> dict:
    return {
        "input": str(input_root),
        "work_dir": str(work_dir),
        "output": str(output),
        "extracted_motion_output": str(extracted_motion_dir),
        "dry_run": dry_run,
        "counts": {
            "audit_candidates": result.audit.candidate_count,
            "audit_pairs": result.audit.pair_count,
            "embedded_candidates": result.audit.embedded_candidate_count,
            "extract_planned": result.extract.planned_count,
            "extract_extracted": result.extract.extracted_count,
            "direct_live_planned": result.direct_build.planned_count,
            "direct_live_built": result.direct_build.built_count,
            "extracted_live_planned": result.extracted_build.planned_count,
            "extracted_live_built": result.extracted_build.built_count,
            "total_live_planned": result.planned_count,
            "total_live_built": result.built_count,
            "total_errors": result.error_count,
        },
        "extract_source_type_counts": result.extract.source_type_counts,
        "reports": {
            "motion_audit_summary": str(result.audit.summary_path),
            "motion_candidates": str(result.audit.candidates_path),
            "motion_pairs": str(result.audit.pairs_path),
            "motion_extract_manifest": str(result.extract.manifest_path),
            "extracted_pairs": str(result.extract.pairs_path),
            "direct_live_manifest": str(result.direct_build.manifest_path),
            "extracted_live_manifest": str(result.extracted_build.manifest_path),
        },
    }
