from photodaterescue.wizard_defaults import DEFAULT_EXCLUDES, build_output_layout, suggest_run_dir
from photodaterescue.cli import main
from photodaterescue.wizard import run_wizard
from photodaterescue.wizard_prompts import ScriptedPrompts


def test_default_excludes_include_common_android_cache_dirs():
    assert "Pictures/.thumbnails" in DEFAULT_EXCLUDES
    assert "DCIM/.globalTrash" in DEFAULT_EXCLUDES


def test_build_output_layout_uses_predictable_subdirectories(tmp_path):
    layout = build_output_layout(tmp_path / "PhotoDateRescue-output")

    assert layout.base == tmp_path / "PhotoDateRescue-output"
    assert layout.scan_report == layout.base / "scan-report"
    assert layout.repaired_media == layout.base / "repaired-media"
    assert layout.live_work == layout.base / "live-work"
    assert layout.live_output == layout.base / "live-output"


def test_suggest_run_dir_adds_suffix_when_base_exists(tmp_path):
    base = tmp_path / "run"
    base.mkdir()

    suggested = suggest_run_dir(base, suffix="2026-05-06-120000")

    assert suggested == tmp_path / "run-2026-05-06-120000"


def test_wizard_can_exit_without_running_work():
    prompts = ScriptedPrompts(["exit"])
    result = run_wizard(prompts=prompts)

    assert result.mode == "exit"
    assert result.completed is True
    assert "你想做什么" in prompts.messages[0]


def test_wizard_can_run_doctor_only(monkeypatch):
    calls = []
    monkeypatch.setattr("photodaterescue.wizard.run_doctor", lambda: calls.append("doctor") or 0)

    result = run_wizard(prompts=ScriptedPrompts(["doctor"]))

    assert calls == ["doctor"]
    assert result.mode == "doctor"
    assert result.completed is True


def test_cli_help_lists_wizard(capsys):
    exit_code = main(["--help"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "wizard" in captured.out


def test_cli_wizard_delegates_to_run_wizard(monkeypatch):
    calls = []

    class Result:
        completed = True
        mode = "exit"
        message = "bye"

    monkeypatch.setattr("photodaterescue.cli.run_wizard", lambda: calls.append("wizard") or Result())

    assert main(["wizard"]) == 0
    assert calls == ["wizard"]


def test_repair_flow_runs_scan_then_repair_after_confirmation(monkeypatch, tmp_path):
    calls = []
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    class RepairResult:
        copied = 2
        repaired = 1
        failed = 0
        skipped = 0
        manifest_path = tmp_path / "manifest.json"

    monkeypatch.setattr("photodaterescue.wizard.run_doctor", lambda: 0)
    monkeypatch.setattr("photodaterescue.wizard.ExifToolClient", lambda: object())
    monkeypatch.setattr("photodaterescue.wizard.analyze_directory", lambda *args, **kwargs: calls.append("scan") or [])
    monkeypatch.setattr("photodaterescue.wizard.write_reports", lambda *args, **kwargs: calls.append("write_reports"))
    monkeypatch.setattr("photodaterescue.wizard.repair_directory", lambda *args, **kwargs: calls.append("repair") or RepairResult())

    result = run_wizard(
        prompts=ScriptedPrompts(
            [
                "repair",
                str(input_dir),
                str(tmp_path / "out"),
                True,
                True,
            ]
        )
    )

    assert calls == ["scan", "write_reports", "repair"]
    assert result.mode == "repair"


def test_live_flow_runs_dry_run_then_build_after_confirmation(monkeypatch, tmp_path):
    calls = []
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    class Audit:
        pair_count = 1
        embedded_candidate_count = 1

    class Result:
        audit = Audit()
        planned_count = 2
        built_count = 0
        error_count = 0
        manifest_path = tmp_path / "manifest.json"
        extract_source_type_counts = {}

    def fake_live_workflow(*args, dry_run=False, **kwargs):
        calls.append(("live", dry_run))
        result = Result()
        if not dry_run:
            result.built_count = 2
        return result

    monkeypatch.setattr("photodaterescue.wizard.run_doctor", lambda: 0)
    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "darwin")
    monkeypatch.setattr("photodaterescue.wizard.ExifToolClient", lambda: object())
    monkeypatch.setattr("photodaterescue.wizard.run_live_workflow", fake_live_workflow)

    result = run_wizard(
        prompts=ScriptedPrompts(
            [
                "live",
                str(input_dir),
                str(tmp_path / "out"),
                True,
                True,
            ]
        )
    )

    assert calls == [("live", True), ("live", False)]
    assert result.mode == "live"


def test_recommended_flow_can_build_repair_and_live(monkeypatch, tmp_path):
    calls = []
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    class RepairResult:
        copied = 1
        repaired = 1
        failed = 0
        skipped = 0
        manifest_path = tmp_path / "repair-manifest.json"

    class Audit:
        pair_count = 1
        embedded_candidate_count = 1

    class LiveResult:
        audit = Audit()
        planned_count = 2
        built_count = 2
        error_count = 0
        manifest_path = tmp_path / "live-manifest.json"
        extract_source_type_counts = {}

    monkeypatch.setattr("photodaterescue.wizard.run_doctor", lambda: 0)
    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "darwin")
    monkeypatch.setattr("photodaterescue.wizard.ExifToolClient", lambda: object())
    monkeypatch.setattr("photodaterescue.wizard.analyze_directory", lambda *args, **kwargs: calls.append("scan") or [])
    monkeypatch.setattr("photodaterescue.wizard.write_reports", lambda *args, **kwargs: calls.append("write_reports"))
    monkeypatch.setattr("photodaterescue.wizard.repair_directory", lambda *args, **kwargs: calls.append("repair") or RepairResult())
    monkeypatch.setattr(
        "photodaterescue.wizard.run_live_workflow",
        lambda *args, dry_run=False, **kwargs: calls.append(("live", dry_run)) or LiveResult(),
    )

    result = run_wizard(
        prompts=ScriptedPrompts(
            [
                "recommended",
                str(input_dir),
                str(tmp_path / "out"),
                True,
                "both",
                True,
            ]
        )
    )

    assert calls == ["scan", "write_reports", ("live", True), "repair", ("live", False)]
    assert result.mode == "recommended"


def test_recommended_flow_skips_live_build_on_windows(monkeypatch, tmp_path):
    calls = []
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    class RepairResult:
        copied = 1
        repaired = 1
        failed = 0
        skipped = 0
        manifest_path = tmp_path / "repair-manifest.json"

    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "win32")
    monkeypatch.setattr("photodaterescue.wizard.run_doctor", lambda: 0)
    monkeypatch.setattr("photodaterescue.wizard.ExifToolClient", lambda: object())
    monkeypatch.setattr("photodaterescue.wizard.analyze_directory", lambda *args, **kwargs: calls.append("scan") or [])
    monkeypatch.setattr("photodaterescue.wizard.write_reports", lambda *args, **kwargs: calls.append("write_reports"))
    monkeypatch.setattr("photodaterescue.wizard.repair_directory", lambda *args, **kwargs: calls.append("repair") or RepairResult())

    def fail_live_workflow(*args, **kwargs):
        raise AssertionError("Windows recommended flow should not run live workflow")

    monkeypatch.setattr("photodaterescue.wizard.run_live_workflow", fail_live_workflow)

    result = run_wizard(
        prompts=ScriptedPrompts(
            [
                "recommended",
                str(input_dir),
                str(tmp_path / "out"),
                True,
                "repair",
                True,
            ]
        )
    )

    assert calls == ["scan", "write_reports", "repair"]
    assert result.mode == "recommended"
    assert "repaired_media" in result.outputs


def test_live_flow_explains_windows_limitation(monkeypatch):
    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "win32")

    result = run_wizard(prompts=ScriptedPrompts(["live"]))

    assert result.completed is False
    assert "Windows" in result.message
    assert "不支持构建 Apple Photos 可识别的 Live Photo" in result.message
    assert "portable-pair" in result.message


def test_live_summary_prints_source_type_counts(capsys, tmp_path):
    from photodaterescue.wizard import _print_live_summary

    class Audit:
        pair_count = 1
        embedded_candidate_count = 3

    class Result:
        audit = Audit()
        planned_count = 4
        built_count = 0
        error_count = 1
        manifest_path = tmp_path / "manifest.json"
        extract_source_type_counts = {
            "xiaomi_native_camera": {"planned": 2, "extracted": 0, "errors": 0},
            "generic_embedded_motion": {"planned": 1, "extracted": 0, "errors": 1},
        }

    _print_live_summary(Result(), dry_run=True)
    captured = capsys.readouterr()

    assert "小米原生相机动态照片" in captured.out
    assert "planned=2" in captured.out
    assert "通用 Motion/MicroVideo 候选" in captured.out
    assert "errors=1" in captured.out


def test_live_summary_explains_xiaomi_native_next_step_only_for_dry_run(capsys, tmp_path):
    from photodaterescue.wizard import _print_live_summary

    class Audit:
        pair_count = 0
        embedded_candidate_count = 2

    class Result:
        audit = Audit()
        planned_count = 2
        built_count = 0
        error_count = 0
        manifest_path = tmp_path / "manifest.json"
        extract_source_type_counts = {
            "xiaomi_native_camera": {"planned": 2, "extracted": 0, "errors": 0},
        }

    _print_live_summary(Result(), dry_run=True)
    dry_run_output = capsys.readouterr().out
    _print_live_summary(Result(), dry_run=False)
    build_output = capsys.readouterr().out

    assert "可提取出静态图 + 短视频配对" in dry_run_output
    assert "不等于 Apple Photos 一定识别为 Live Photo" in dry_run_output
    assert "可提取出静态图 + 短视频配对" not in build_output
