from photodaterescue import __version__
from photodaterescue.cli import main


def test_package_exposes_version():
    assert __version__ == "0.3.3"


def test_pyproject_version_matches_package():
    from pathlib import Path

    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == __version__


def test_module_entrypoint_runs_help():
    exit_code = main(["--help"])
    assert exit_code == 0


def test_cli_help_lists_primary_commands(capsys):
    exit_code = main(["--help"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "扫描相册导出目录" in captured.out
    assert "wizard" in captured.out
    assert "运行中文终端向导" in captured.out
    assert "android-pull" in captured.out
    assert "scan" in captured.out
    assert "motion-audit" in captured.out
    assert "motion-extract" in captured.out
    assert "live-build" in captured.out
    assert "rescue-live" in captured.out
    assert "repair" in captured.out
    assert "reconcile" in captured.out
    assert "classify-unmatched" in captured.out
    assert "materialize-unmatched" in captured.out


def test_gui_modules_import_without_launching_window():
    import photodaterescue.gui_app as gui_app
    import photodaterescue.gui_launcher as gui_launcher

    assert hasattr(gui_app, "PhotoDateRescueApp")
    assert callable(gui_launcher.main)


def test_pyproject_exposes_gui_script():
    from pathlib import Path

    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'photodaterescue-gui = "photodaterescue.gui_launcher:main"' in text


def test_gui_busy_state_disables_primary_buttons():
    from photodaterescue.gui_app import PhotoDateRescueApp

    calls = []

    class FakeButton:
        def __init__(self):
            self.state = "normal"

        def configure(self, **kwargs):
            self.state = kwargs["state"]
            calls.append(self.state)

    app = object.__new__(PhotoDateRescueApp)
    app._busy = False
    app._scan_completed = True
    app._output_ready = True
    app.source_button = FakeButton()
    app.output_button = FakeButton()
    app.scan_button = FakeButton()
    app.repair_button = FakeButton()
    app.open_button = FakeButton()
    app.status_var = None

    app._set_busy(True)

    assert app.source_button.state == "disabled"
    assert app.output_button.state == "disabled"
    assert app.scan_button.state == "disabled"
    assert app.repair_button.state == "disabled"
    assert app.open_button.state == "disabled"

    app._set_busy(False)

    assert app.source_button.state == "normal"
    assert app.output_button.state == "normal"
    assert app.scan_button.state == "normal"
    assert app.repair_button.state == "normal"
    assert app.open_button.state == "normal"
    assert calls


def test_gui_suggests_output_without_overwriting_existing_choice(tmp_path):
    from photodaterescue.gui_app import PhotoDateRescueApp

    status_updates = []

    class FakeVar:
        def __init__(self, value=""):
            self.value = value

        def get(self):
            return self.value

        def set(self, value):
            self.value = value

    class FakeController:
        def suggest_output_folder(self, source_path):
            return tmp_path / (source_path.split("/")[-1] + "-PhotoDateRescue-output")

    app = object.__new__(PhotoDateRescueApp)
    app.controller = FakeController()
    app.output_var = FakeVar()
    app.status_var = FakeVar()

    app._suggest_output_from_source("/tmp/Xiaomi14-raw-export")

    assert app.output_var.get().endswith("Xiaomi14-raw-export-PhotoDateRescue-output")
    status_updates.append(app.status_var.get())
    assert "推荐安全输出文件夹" in status_updates[-1]

    app.output_var.set("/tmp/custom-output")
    app._suggest_output_from_source("/tmp/Another")

    assert app.output_var.get() == "/tmp/custom-output"
    assert app.status_var.get() == status_updates[-1]


def test_gui_open_folder_uses_windows_startfile(monkeypatch, tmp_path):
    from photodaterescue.gui_app import open_folder

    calls = []
    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "win32")
    monkeypatch.setattr("os.startfile", lambda path: calls.append(path), raising=False)

    open_folder(tmp_path)

    assert calls == [tmp_path]


def test_gui_formats_scan_summary_as_categories(tmp_path):
    from photodaterescue.gui_app import PhotoDateRescueApp
    from photodaterescue.gui_models import GuiScanSummary

    app = object.__new__(PhotoDateRescueApp)
    summary = GuiScanSummary(
        total_files=10,
        photo_files=7,
        video_files=3,
        repairable_files=4,
        ok_files=2,
        high_risk_files=1,
        unsupported_files=2,
        error_files=1,
        report_dir=tmp_path / "scan-report",
    )

    text = app._format_scan_summary(summary)

    assert "结果分类" in text
    assert "可以尝试修复：4" in text
    assert "建议先人工抽查：1" in text
    assert "暂不支持：2" in text
    assert "读取出错：1" in text


def test_gui_repair_summary_includes_next_steps(tmp_path):
    from photodaterescue.gui_app import PhotoDateRescueApp
    from photodaterescue.gui_models import GuiRepairSummary

    app = object.__new__(PhotoDateRescueApp)
    summary = GuiRepairSummary(copied=2, repaired=3, failed=0, skipped=1, output_dir=tmp_path / "out")

    text = app._format_repair_summary(summary)

    assert "建议下一步" in text
    assert "打开输出文件夹" in text
    assert "手动导入 Apple Photos" in text
    assert "不要删除" in text


def test_gui_platform_guidance_mentions_windows_boundary(monkeypatch):
    from photodaterescue.gui_app import format_platform_guidance

    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "win32")

    text = format_platform_guidance()

    assert "普通照片 / 视频" in text
    assert "不承诺 Live Photo" in text
