"""Tiny image test fixture builders."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image


def create_image(path: Path, fmt: str = "JPEG", size: Tuple[int, int] = (32, 32), color=(20, 40, 60)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", size, color)
    image.save(path, format=fmt)
    return path
