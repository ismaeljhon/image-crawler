from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


def sanitize(name: str, max_len: int = 80) -> str:
    """Replace non-alphanumeric chars with underscores, collapse runs, truncate."""
    name = re.sub(r"[^a-zA-Z0-9]+", "_", name)
    name = name.strip("_")
    name = name[:max_len]
    return name or "untitled"


def url_to_folder_name(url: str) -> str:
    """Derive a folder name from the last meaningful path segment of a URL."""
    path = urlparse(url).path.rstrip("/")
    segment = path.split("/")[-1] if path else ""
    return sanitize(segment) if segment else "untitled"


def folder_for_page(title: str | None, url: str, output_dir: Path) -> Path:
    """Return (and create) the per-page output folder."""
    if title and title.strip():
        name = sanitize(title.strip())
    else:
        name = url_to_folder_name(url)
    folder = output_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def url_to_base_path(image_url: str, folder: Path) -> Path:
    """Return the base (no counter suffix) candidate path for an image URL."""
    parsed = urlparse(image_url)
    raw_name = parsed.path.split("/")[-1] or "image"
    raw_name = raw_name.split("?")[0] or "image"
    p = Path(raw_name)
    stem = sanitize(p.stem, max_len=195) if p.stem else "image"
    ext = p.suffix.lower()
    if not re.match(r"\.[a-zA-Z0-9]{2,5}$", ext):
        ext = ""
    return folder / f"{stem}{ext}"


def resolve_filename(
    image_url: str, folder: Path, reserved: set[Path] | None = None
) -> Path:
    """
    Derive a local filename from the image URL.
    If a file with the same name already exists or is already reserved by a
    concurrent download, append a numeric suffix.
    """
    parsed = urlparse(image_url)
    raw_name = parsed.path.split("/")[-1] or "image"
    # Strip query string from name
    raw_name = raw_name.split("?")[0] or "image"

    # Sanitize stem and extension separately so the dot is preserved
    p = Path(raw_name)
    stem = sanitize(p.stem, max_len=195) if p.stem else "image"
    ext = p.suffix.lower()  # e.g. ".jpg"
    if not re.match(r"\.[a-zA-Z0-9]{2,5}$", ext):
        ext = ""

    base_stem = stem
    counter = 0
    while True:
        name = f"{base_stem}_{counter}{ext}" if counter else f"{base_stem}{ext}"
        candidate = folder / name
        if not candidate.exists() and (reserved is None or candidate not in reserved):
            return candidate
        counter += 1
