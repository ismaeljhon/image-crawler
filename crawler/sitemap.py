from __future__ import annotations

from pathlib import Path


def read_urls(file_path: str) -> list[str]:
    """Read URLs from a plain text file, one URL per line. Blank lines and
    lines starting with '#' are ignored."""
    lines = Path(file_path).read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]
