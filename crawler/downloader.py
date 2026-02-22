from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import aiofiles
import aiohttp
from PIL import Image

from .fs import resolve_filename, url_to_base_path
from .progress import CrawlProgress
from .state import StateManager

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 65_536  # 64 KiB


class DownloadStatus(str, Enum):
    DOWNLOADED = "downloaded"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    SKIPPED_DRY_RUN = "skipped_dry_run"
    FAILED = "failed"


@dataclass
class DownloadResult:
    url: str
    status: DownloadStatus
    local_path: Path | None = None


class ImageDownloader:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        state: StateManager,
        concurrency: int,
        timeout: int,
        dry_run: bool,
        progress: CrawlProgress,
        redownload: bool = False,
        image_quality: int = 85,
    ) -> None:
        self._session = session
        self._state = state
        self._semaphore = asyncio.Semaphore(concurrency)
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._dry_run = dry_run
        self._redownload = redownload
        self._progress = progress
        self._image_quality = image_quality
        self._reserved: set[Path] = set()  # filenames claimed by in-flight downloads

    async def download_batch(
        self, image_urls: list[str], folder: Path
    ) -> list[DownloadResult]:
        """Download all images concurrently (bounded by semaphore)."""
        self._progress.start_image_batch(len(image_urls))
        tasks = [self._download_one(url, folder) for url in image_urls]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return list(results)

    async def _download_one(self, url: str, folder: Path) -> DownloadResult:
        async with self._semaphore:
            if not self._redownload and self._state.is_downloaded(url):
                logger.debug("Skipping duplicate: %s", url)
                self._progress.record_download(skipped=True)
                return DownloadResult(url=url, status=DownloadStatus.SKIPPED_DUPLICATE)

            if self._dry_run:
                logger.info("[dry-run] Would download: %s", url)
                self._progress.record_download(skipped=True)
                return DownloadResult(url=url, status=DownloadStatus.SKIPPED_DRY_RUN)

            if not self._redownload and url_to_base_path(url, folder).exists():
                logger.debug("File already exists, skipping: %s", url)
                self._state.mark_downloaded(url)
                self._progress.record_download(skipped=True)
                return DownloadResult(url=url, status=DownloadStatus.SKIPPED_DUPLICATE)

            # If redownloading, remove the existing file so resolve_filename
            # returns the original name rather than a numbered variant.
            if self._redownload:
                base = url_to_base_path(url, folder)
                if base.exists():
                    base.unlink()

            # Claim a filename *before* the first await so no concurrent coroutine
            # can resolve to the same path while this download is in flight.
            local_path = resolve_filename(url, folder, self._reserved)
            self._reserved.add(local_path)

            try:
                result = await self._fetch_and_write(url, local_path)
            except Exception as exc:
                logger.error("Failed to download %s: %s", url, exc)
                self._progress.record_download(failed=True)
                self._reserved.discard(local_path)
                return DownloadResult(url=url, status=DownloadStatus.FAILED)

            self._reserved.discard(local_path)
            await asyncio.get_event_loop().run_in_executor(
                None, self._compress_image, result.local_path
            )
            self._state.mark_downloaded(url)
            self._progress.record_download()
            return result

    def _compress_image(self, path: Path) -> None:
        """Re-encode JPEG or WebP files at the configured quality. No-op for other formats."""
        ext = path.suffix.lower()
        if ext not in {".jpg", ".jpeg", ".webp"}:
            return
        try:
            with Image.open(path) as img:
                if ext in {".jpg", ".jpeg"}:
                    if img.mode in ("RGBA", "LA", "P"):
                        img = img.convert("RGB")
                    img.save(path, format="JPEG", quality=self._image_quality, optimize=True)
                else:  # .webp
                    img.save(path, format="WEBP", quality=self._image_quality, method=4)
        except Exception as exc:
            logger.warning("Compression skipped for %s: %s", path.name, exc)

    async def _fetch_and_write(self, url: str, local_path: Path) -> DownloadResult:
        async with self._session.get(url, timeout=self._timeout) as resp:
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status}")

            try:
                async with aiofiles.open(local_path, "wb") as fh:
                    async for chunk in resp.content.iter_chunked(_CHUNK_SIZE):
                        await fh.write(chunk)
            except OSError as exc:
                logger.critical("Disk write failure for %s: %s", local_path, exc)
                raise

        logger.debug("Downloaded %s -> %s", url, local_path)
        return DownloadResult(
            url=url, status=DownloadStatus.DOWNLOADED, local_path=local_path
        )
