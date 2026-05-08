"""Shared pytest helpers."""

from pathlib import Path

import pytest


@pytest.fixture
def sample_root(tmp_path: Path) -> Path:
    root = tmp_path / "library"
    root.mkdir()
    return root
