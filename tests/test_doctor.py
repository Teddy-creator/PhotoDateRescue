from photodaterescue.cli import main


def test_doctor_passes_when_exiftool_exists(monkeypatch, capsys):
    def fake_which(name):
        return {
            "exiftool": "/usr/local/bin/exiftool",
            "ffprobe": "/usr/local/bin/ffprobe",
            "ffmpeg": "/usr/local/bin/ffmpeg",
            "adb": "/usr/local/bin/adb",
            "makelive": "/usr/local/bin/makelive",
        }.get(name)

    monkeypatch.setattr("photodaterescue.doctor.find_tool", fake_which)
    exit_code = main(["doctor"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "platform:" in captured.out.lower()
    assert "exiftool: ok" in captured.out.lower()
    assert "ffprobe: ok" in captured.out.lower()
    assert "ffmpeg: ok" in captured.out.lower()
    assert "adb: ok" in captured.out.lower()
    assert "makelive: ok" in captured.out.lower()


def test_doctor_fails_when_exiftool_missing(monkeypatch, capsys):
    monkeypatch.setattr("photodaterescue.doctor.find_tool", lambda name: None)
    exit_code = main(["doctor"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "exiftool: missing" in captured.out.lower()
    assert "exiftool" in captured.out.lower()
    assert "ffprobe: missing" in captured.out.lower()
    assert "ffmpeg: missing" in captured.out.lower()
    assert "adb: missing" in captured.out.lower()
    assert "makelive: missing" in captured.out.lower()


def test_doctor_prints_windows_specific_hints(monkeypatch, capsys):
    def fake_which(name):
        return "C:\\Tools\\exiftool.exe" if name == "exiftool" else None

    monkeypatch.setattr("photodaterescue.doctor.find_tool", fake_which)
    monkeypatch.setenv("PHOTODATERESCUE_PLATFORM_OVERRIDE", "win32")

    exit_code = main(["doctor"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "platform: windows" in captured.out.lower()
    assert "adb.exe" in captured.out.lower()
    assert "windows_note" in captured.out.lower()
    assert "不支持构建 apple live photo" in captured.out.lower()
    assert "portable-pair" in captured.out.lower()
