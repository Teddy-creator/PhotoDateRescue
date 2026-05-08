"""Cross-platform media decode helpers for reconcile and future audits."""

from __future__ import annotations

import os
import subprocess
import tempfile
import warnings
from pathlib import Path

from PIL import Image, ImageFile

from .tools import find_tool


ImageFile.LOAD_TRUNCATED_IMAGES = True
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)
warnings.filterwarnings("ignore", message="Corrupt EXIF data.*", category=UserWarning)
warnings.filterwarnings(
    "ignore",
    message="Palette images with Transparency expressed in bytes should be converted to RGBA images",
    category=UserWarning,
)

try:  # pragma: no cover - availability depends on local environment
    from pillow_heif import register_heif_opener
except ImportError:  # pragma: no cover - exercised by environments without pillow-heif
    register_heif_opener = None
else:  # pragma: no cover - simple import side effect
    register_heif_opener()


def load_rgb_image(path: Path) -> Image.Image:
    try:
        return _load_with_pillow(path)
    except Exception as pillow_error:
        try:
            return _load_with_ffmpeg(path)
        except Exception as ffmpeg_error:
            raise RuntimeError(
                "Failed to decode {0}. Pillow error: {1}. FFmpeg error: {2}".format(
                    path,
                    pillow_error,
                    ffmpeg_error,
                )
            )


def _load_with_pillow(path: Path) -> Image.Image:
    image = Image.open(path)
    image.load()
    return image.convert("RGB")


def _load_with_ffmpeg(path: Path) -> Image.Image:
    ffmpeg_path = find_tool("ffmpeg")
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg is not available on PATH")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
        tmp_path = Path(handle.name)
    try:
        completed = subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-i",
                str(path),
                "-frames:v",
                "1",
                str(tmp_path),
            ],
            capture_output=True,
            check=False,
            text=True,
        )
        if completed.returncode != 0:
            error = completed.stderr.strip() or completed.stdout.strip() or "ffmpeg decode failed"
            raise RuntimeError(error)
        image = Image.open(tmp_path)
        image.load()
        return image.convert("RGB")
    finally:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
