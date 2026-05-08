import subprocess

from photodaterescue.android_pull import AdbMissingError, android_pull
from photodaterescue.cli import main


def test_android_pull_uses_adb_pull_archive_mode(monkeypatch, tmp_path):
    commands = []

    def fake_which(name):
        return "/usr/local/bin/adb" if name == "adb" else None

    def fake_run(command, check):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("photodaterescue.android_pull.shutil.which", fake_which)
    monkeypatch.setattr("photodaterescue.android_pull.subprocess.run", fake_run)

    result = android_pull(
        device_paths=["/sdcard/DCIM/", "/sdcard/Pictures"],
        output=tmp_path / "export",
    )

    assert result.pulled_roots == ["/sdcard/DCIM", "/sdcard/Pictures"]
    assert commands == [
        ["/usr/local/bin/adb", "pull", "-a", "/sdcard/DCIM", str((tmp_path / "export").resolve())],
        ["/usr/local/bin/adb", "pull", "-a", "/sdcard/Pictures", str((tmp_path / "export").resolve())],
    ]


def test_android_pull_dry_run_does_not_call_adb(monkeypatch, tmp_path):
    monkeypatch.setattr("photodaterescue.android_pull.shutil.which", lambda name: "/usr/local/bin/adb")

    def fail_run(command, check):
        raise AssertionError("dry-run should not execute adb")

    monkeypatch.setattr("photodaterescue.android_pull.subprocess.run", fail_run)

    result = android_pull(["/sdcard/DCIM"], tmp_path / "export", dry_run=True)

    assert result.dry_run is True
    assert result.commands[0][1:4] == ["pull", "-a", "/sdcard/DCIM"]
    assert not (tmp_path / "export").exists()


def test_android_pull_rejects_relative_device_path(monkeypatch, tmp_path):
    monkeypatch.setattr("photodaterescue.android_pull.shutil.which", lambda name: "/usr/local/bin/adb")

    try:
        android_pull(["sdcard/DCIM"], tmp_path / "export")
    except ValueError as exc:
        assert "must be absolute" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_android_pull_reports_missing_adb(monkeypatch, tmp_path):
    monkeypatch.setattr("photodaterescue.android_pull.shutil.which", lambda name: None)

    try:
        android_pull(["/sdcard/DCIM"], tmp_path / "export")
    except AdbMissingError as exc:
        assert "adb is not available" in str(exc)
    else:
        raise AssertionError("Expected AdbMissingError")


def test_android_pull_accepts_windows_style_adb_path(tmp_path):
    result = android_pull(
        ["/sdcard/DCIM"],
        tmp_path / "export",
        adb_path="C:\\Android\\platform-tools\\adb.exe",
        dry_run=True,
    )

    assert result.commands[0][0] == "C:\\Android\\platform-tools\\adb.exe"


def test_cli_android_pull_dry_run_does_not_require_exiftool(monkeypatch, tmp_path, capsys):
    def fake_which(name):
        return "/usr/local/bin/adb" if name == "adb" else None

    monkeypatch.setattr("photodaterescue.android_pull.shutil.which", fake_which)

    exit_code = main(
        [
            "android-pull",
            "--device-path",
            "/sdcard/DCIM",
            "--output",
            str(tmp_path / "export"),
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "adb pull -a /sdcard/DCIM" in captured.out
