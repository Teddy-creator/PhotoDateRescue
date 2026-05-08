from pathlib import Path

from PIL import Image

from photodaterescue.media_decode import load_rgb_image


def test_load_rgb_image_falls_back_to_ffmpeg_when_pillow_fails(monkeypatch, tmp_path):
    target = tmp_path / "odd.heic"
    target.write_bytes(b"fake")

    def fake_load_with_pillow(path):
        raise RuntimeError("pillow failed")

    def fake_load_with_ffmpeg(path):
        return Image.new("RGB", (12, 8), (1, 2, 3))

    monkeypatch.setattr("photodaterescue.media_decode._load_with_pillow", fake_load_with_pillow)
    monkeypatch.setattr("photodaterescue.media_decode._load_with_ffmpeg", fake_load_with_ffmpeg)

    image = load_rgb_image(target)
    try:
        assert image.size == (12, 8)
    finally:
        image.close()


def test_load_rgb_image_raises_combined_error_when_all_decoders_fail(monkeypatch, tmp_path):
    target = tmp_path / "broken.bin"
    target.write_bytes(b"fake")

    monkeypatch.setattr(
        "photodaterescue.media_decode._load_with_pillow",
        lambda path: (_ for _ in ()).throw(RuntimeError("pillow failed")),
    )
    monkeypatch.setattr(
        "photodaterescue.media_decode._load_with_ffmpeg",
        lambda path: (_ for _ in ()).throw(RuntimeError("ffmpeg failed")),
    )

    try:
        load_rgb_image(target)
    except RuntimeError as exc:
        message = str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("expected load_rgb_image to fail")

    assert "Pillow error" in message
    assert "FFmpeg error" in message
