from photodaterescue.discovery import discover_files
from tests.factories import create_image


def test_discover_files_marks_supported_extensions(sample_root):
    create_image(sample_root / "a.jpg")
    create_image(sample_root / "b.png", fmt="PNG")
    (sample_root / "c.txt").write_text("hello", encoding="utf-8")

    files = discover_files(sample_root)

    assert [item.extension for item in files] == [".jpg", ".png", ".txt"]
    assert files[0].has_supported_extension is True
    assert files[1].has_supported_extension is True
    assert files[2].has_supported_extension is False


def test_discover_files_marks_heif_family_extensions_as_supported(sample_root):
    create_image(sample_root / "a.heic")
    create_image(sample_root / "b.webp", fmt="WEBP")

    files = discover_files(sample_root)

    assert [item.extension for item in files] == [".heic", ".webp"]
    assert all(item.has_supported_extension for item in files)


def test_discover_files_marks_video_extensions_as_supported(sample_root):
    (sample_root / "clip.mp4").write_bytes(b"fake")
    (sample_root / "movie.m4v").write_bytes(b"fake")

    files = discover_files(sample_root)

    assert [item.extension for item in files] == [".mp4", ".m4v"]
    assert all(item.has_supported_extension for item in files)
    assert all(item.path_media_kind == "video" for item in files)


def test_discover_files_preserves_relative_paths(sample_root):
    create_image(sample_root / "DCIM" / "tieba" / "example.jpg")

    files = discover_files(sample_root)

    assert files[0].relative_path.as_posix() == "DCIM/tieba/example.jpg"


def test_discover_files_can_exclude_directory_prefixes(sample_root):
    create_image(sample_root / "Pictures" / ".thumbnails" / "cache.jpg")
    create_image(sample_root / "Pictures" / "WeiXin" / "keep.jpg")

    files = discover_files(sample_root, exclude_patterns=["Pictures/.thumbnails"])

    assert [item.relative_path.as_posix() for item in files] == ["Pictures/WeiXin/keep.jpg"]


def test_discover_files_can_include_glob_patterns(sample_root):
    create_image(sample_root / "DCIM" / "Camera" / "camera.jpg")
    create_image(sample_root / "Pictures" / "WeiXin" / "chat.jpg")

    files = discover_files(sample_root, include_patterns=["DCIM/**"])

    assert [item.relative_path.as_posix() for item in files] == ["DCIM/Camera/camera.jpg"]
