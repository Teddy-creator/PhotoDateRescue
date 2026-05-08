from photodaterescue import __version__
from photodaterescue.cli import main


def test_package_exposes_version():
    assert __version__ == "0.1.1"


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

    app._suggest_output_from_source("/tmp/Xiaomi14-raw-export")

    assert app.output_var.get().endswith("Xiaomi14-raw-export-PhotoDateRescue-output")

    app.output_var.set("/tmp/custom-output")
    app._suggest_output_from_source("/tmp/Another")

    assert app.output_var.get() == "/tmp/custom-output"


def test_gui_open_folder_uses_windows_startfile(monkeypatch, tmp_path):
    from photodaterescue.gui_app import open_folder

    calls = []
    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "win32")
    monkeypatch.setattr("os.startfile", lambda path: calls.append(path), raising=False)

    open_folder(tmp_path)

    assert calls == [tmp_path]
