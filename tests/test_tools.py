import os

from photodaterescue.tools import find_tool


def test_find_tool_uses_path_first(monkeypatch):
    monkeypatch.setattr("photodaterescue.tools.shutil.which", lambda name: "/custom/bin/{0}".format(name))

    assert find_tool("exiftool") == "/custom/bin/exiftool"


def test_find_tool_checks_macos_fallback_dirs_when_gui_path_is_sparse(monkeypatch, tmp_path):
    tool = tmp_path / "exiftool"
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    tool.chmod(tool.stat().st_mode | 0o111)

    monkeypatch.setattr("photodaterescue.tools.shutil.which", lambda name: None)
    monkeypatch.setattr("photodaterescue.tools.MACOS_FALLBACK_TOOL_DIRS", (tmp_path,))
    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "darwin")

    assert find_tool("exiftool") == str(tool)


def test_find_tool_ignores_macos_fallback_dirs_on_windows(monkeypatch, tmp_path):
    tool = tmp_path / "exiftool"
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    tool.chmod(tool.stat().st_mode | 0o111)

    monkeypatch.setattr("photodaterescue.tools.shutil.which", lambda name: None)
    monkeypatch.setattr("photodaterescue.tools.MACOS_FALLBACK_TOOL_DIRS", (tmp_path,))
    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "win32")

    assert find_tool("exiftool") is None


def test_find_tool_requires_executable_fallback(monkeypatch, tmp_path):
    tool = tmp_path / "exiftool"
    tool.write_text("#!/bin/sh\n", encoding="utf-8")
    tool.chmod(tool.stat().st_mode & ~0o111)

    monkeypatch.setattr("photodaterescue.tools.shutil.which", lambda name: None)
    monkeypatch.setattr("photodaterescue.tools.MACOS_FALLBACK_TOOL_DIRS", (tmp_path,))
    monkeypatch.setattr("photodaterescue.tools.os.access", lambda path, mode: False)
    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "darwin")

    assert find_tool("exiftool") is None
