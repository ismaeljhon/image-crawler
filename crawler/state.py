from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_VERSION = 1
_STATE_FILENAME = ".state.json"
_STATE_TMP_FILENAME = ".state.json.tmp"


class StateManager:
    def __init__(self, output_dir: Path) -> None:
        self._path = output_dir / _STATE_FILENAME
        self._tmp_path = output_dir / _STATE_TMP_FILENAME
        self._downloaded: set[str] = set()

    def load(self) -> None:
        """Load state from disk. On missing or corrupt file, start fresh."""
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != _STATE_VERSION:
                raise ValueError("Unexpected state format")
            urls = data.get("downloaded", [])
            if not isinstance(urls, list):
                raise ValueError("'downloaded' must be a list")
            self._downloaded = set(urls)
            logger.debug("Loaded %d URLs from state.", len(self._downloaded))
        except Exception as exc:
            logger.warning("State file corrupt or unreadable (%s). Starting fresh.", exc)
            self._downloaded = set()

    def save(self) -> None:
        """Atomically write state to disk."""
        data = {
            "version": _STATE_VERSION,
            "downloaded": sorted(self._downloaded),
        }
        self._tmp_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(self._tmp_path, self._path)
        logger.debug("State saved (%d URLs).", len(self._downloaded))

    def is_downloaded(self, url: str) -> bool:
        return url in self._downloaded

    def mark_downloaded(self, url: str) -> None:
        self._downloaded.add(url)
