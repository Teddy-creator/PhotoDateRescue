from datetime import datetime
from pathlib import Path

from photodaterescue.gui_models import DependencyStatus, GuiRepairSummary, GuiScanSummary
from photodaterescue.models import RepairResult, ScanRecord, ScanStatus


def _record(path, relative, status, media_kind):
    return ScanRecord(
        absolute_path=path,
        relative_path=relative,
        extension=relative.suffix,
        width=None,
        height=None,
        has_exif_datetime=False,
        exif_datetime=None,
        file_mtime=datetime(2026, 1, 1),
        file_ctime=datetime(2026, 1, 1),
        chosen_time_source="file_mtime",
        chosen_datetime=datetime(2026, 1, 1),
        status=status,
        reason="test",
        is_supported=True,
        media_kind=media_kind,
    )


def test_gui_summary_models_are_plain_data(tmp_path):
    dependency = DependencyStatus(name="ExifTool", available=True, path="/usr/local/bin/exiftool", required=True)
    scan = GuiScanSummary(
        total_files=3,
        photo_files=2,
        video_files=1,
        repairable_files=1,
        ok_files=1,
        high_risk_files=1,
        unsupported_files=0,
        error_files=0,
        report_dir=tmp_path / "scan-report",
    )
    repair = GuiRepairSummary(copied=1, repaired=1, failed=0, skipped=2, output_dir=tmp_path / "repaired")

    assert dependency.available is True
    assert scan.total_files == 3
    assert repair.output_dir == tmp_path / "repaired"


def test_gui_controller_rejects_missing_source(tmp_path):
    from photodaterescue.gui_controller import GuiValidationError, PhotoDateRescueGuiController

    controller = PhotoDateRescueGuiController()
    missing = tmp_path / "missing"

    try:
        controller.validate_folders(missing, tmp_path / "out")
    except GuiValidationError as exc:
        assert "源文件夹不存在" in str(exc)
    else:
        raise AssertionError("expected missing source to fail")


def test_gui_controller_rejects_empty_paths():
    from photodaterescue.gui_controller import GuiValidationError, PhotoDateRescueGuiController

    controller = PhotoDateRescueGuiController()

    try:
        controller.validate_folders("", "")
    except GuiValidationError as exc:
        assert "请选择安卓照片 / 视频导出文件夹" in str(exc)
    else:
        raise AssertionError("expected empty paths to fail")


def test_gui_controller_rejects_same_source_and_output(tmp_path):
    from photodaterescue.gui_controller import GuiValidationError, PhotoDateRescueGuiController

    source = tmp_path / "source"
    source.mkdir()
    controller = PhotoDateRescueGuiController()

    try:
        controller.validate_folders(source, source)
    except GuiValidationError as exc:
        assert "输出文件夹不能和源文件夹相同" in str(exc)
    else:
        raise AssertionError("expected same folder to fail")


def test_gui_controller_suggests_output_folder_next_to_source(tmp_path):
    from photodaterescue.gui_controller import PhotoDateRescueGuiController

    source = tmp_path / "Xiaomi14-raw-export"
    source.mkdir()

    suggested = PhotoDateRescueGuiController().suggest_output_folder(source)

    assert suggested == tmp_path / "Xiaomi14-raw-export-PhotoDateRescue-output"


def test_gui_controller_reports_required_and_optional_dependencies(monkeypatch):
    from photodaterescue.gui_controller import PhotoDateRescueGuiController

    def fake_which(name):
        return {
            "exiftool": "/usr/local/bin/exiftool",
            "ffmpeg": None,
            "ffprobe": None,
        }.get(name)

    monkeypatch.setattr("photodaterescue.gui_controller.find_tool", fake_which)
    statuses = PhotoDateRescueGuiController().check_dependencies()

    by_name = {status.name: status for status in statuses}
    assert by_name["ExifTool"].available is True
    assert by_name["ExifTool"].required is True
    assert by_name["FFmpeg"].available is False
    assert by_name["FFmpeg"].required is False


def test_gui_controller_rejects_missing_required_dependency(monkeypatch):
    from photodaterescue.gui_controller import GuiValidationError, PhotoDateRescueGuiController

    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "darwin")
    monkeypatch.setattr("photodaterescue.gui_controller.find_tool", lambda name: None)

    try:
        PhotoDateRescueGuiController().validate_required_dependencies()
    except GuiValidationError as exc:
        message = str(exc)
        assert "缺少必需依赖" in message
        assert "brew install exiftool" in message
    else:
        raise AssertionError("expected missing ExifTool to fail")


def test_gui_controller_uses_windows_dependency_hint(monkeypatch):
    from photodaterescue.gui_controller import GuiValidationError, PhotoDateRescueGuiController

    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "win32")
    monkeypatch.setattr("photodaterescue.gui_controller.find_tool", lambda name: None)

    try:
        PhotoDateRescueGuiController().validate_required_dependencies()
    except GuiValidationError as exc:
        message = str(exc)
        assert "exiftool.exe" in message
        assert "PATH" in message
    else:
        raise AssertionError("expected missing ExifTool to fail")


def test_gui_formats_missing_dependency_as_readable_lines():
    from photodaterescue.gui_app import PhotoDateRescueApp

    status = DependencyStatus(
        name="ExifTool",
        available=False,
        path=None,
        required=True,
        hint="缺少 ExifTool，无法可靠读取照片和视频时间信息。hint: Windows 可下载 ExifTool 并把 exiftool.exe 加入 PATH。",
    )
    app = object.__new__(PhotoDateRescueApp)

    message = app._format_dependency(status)

    assert "ExifTool: 缺少（必需）" in message
    assert "影响：缺少 ExifTool" in message
    assert "安装提示：Windows 可下载 ExifTool" in message


def test_gui_scan_writes_reports_and_returns_summary(monkeypatch, tmp_path):
    from photodaterescue.gui_controller import PhotoDateRescueGuiController

    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "out"
    calls = []
    records = [
        _record(source / "a.jpg", Path("a.jpg"), ScanStatus.REPAIRABLE, "image"),
        _record(source / "b.mp4", Path("b.mp4"), ScanStatus.OK, "video"),
        _record(source / "c.bin", Path("c.bin"), ScanStatus.UNSUPPORTED, None),
    ]

    monkeypatch.setattr("photodaterescue.gui_controller.ExifToolClient", lambda: object())
    monkeypatch.setattr("photodaterescue.gui_controller.find_tool", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr("photodaterescue.gui_controller.analyze_directory", lambda *args, **kwargs: records)
    monkeypatch.setattr("photodaterescue.gui_controller.write_reports", lambda *args, **kwargs: calls.append(args))

    summary = PhotoDateRescueGuiController().scan(source, output)

    assert summary.total_files == 3
    assert summary.photo_files == 1
    assert summary.video_files == 1
    assert summary.repairable_files == 1
    assert summary.ok_files == 1
    assert summary.unsupported_files == 1
    assert calls


def test_gui_repair_returns_summary(monkeypatch, tmp_path):
    from photodaterescue.gui_controller import PhotoDateRescueGuiController

    source = tmp_path / "source"
    source.mkdir()
    output = tmp_path / "out"
    calls = []

    monkeypatch.setattr("photodaterescue.gui_controller.ExifToolClient", lambda: object())
    monkeypatch.setattr("photodaterescue.gui_controller.find_tool", lambda name: "/usr/bin/" + name)
    monkeypatch.setattr(
        "photodaterescue.gui_controller.repair_directory",
        lambda *args, **kwargs: calls.append((args, kwargs))
        or RepairResult(
            copied=2,
            repaired=1,
            failed=0,
            skipped=3,
            manifest_path=tmp_path / "manifest.json",
        ),
    )

    summary = PhotoDateRescueGuiController().repair(source, output)

    assert summary.copied == 2
    assert summary.repaired == 1
    assert summary.failed == 0
    assert summary.skipped == 3
    assert summary.output_dir == output / "repaired-media"
    assert calls
