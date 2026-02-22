from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from tqdm import tqdm

logger = logging.getLogger(__name__)


@dataclass
class CrawlStats:
    pages_total: int = 0
    pages_processed: int = 0
    images_found: int = 0
    images_downloaded: int = 0
    images_skipped: int = 0
    images_failed: int = 0


class CrawlProgress:
    def __init__(self, total_pages: int, no_progress: bool = False) -> None:
        self.stats = CrawlStats(pages_total=total_pages)
        self._no_progress = no_progress
        self._page_bar: Optional[tqdm] = None
        self._image_bar: Optional[tqdm] = None

        if not no_progress:
            self._page_bar = tqdm(
                total=total_pages,
                desc="Pages",
                unit="page",
                position=0,
                leave=True,
            )

    def start_page(self, url: str) -> None:
        if self._page_bar:
            self._page_bar.set_postfix_str(url[-60:], refresh=False)

    def finish_page(self, image_count: int) -> None:
        self.stats.pages_processed += 1
        self.stats.images_found += image_count
        if self._page_bar:
            self._page_bar.update(1)

    def start_image_batch(self, count: int) -> None:
        if not self._no_progress and count > 0:
            if self._image_bar:
                self._image_bar.close()
            self._image_bar = tqdm(
                total=count,
                desc="  Images",
                unit="img",
                position=1,
                leave=False,
            )

    def record_download(self, skipped: bool = False, failed: bool = False) -> None:
        if failed:
            self.stats.images_failed += 1
        elif skipped:
            self.stats.images_skipped += 1
        else:
            self.stats.images_downloaded += 1
        if self._image_bar:
            self._image_bar.update(1)

    def close(self) -> None:
        if self._image_bar:
            self._image_bar.close()
        if self._page_bar:
            self._page_bar.close()
        self._print_summary()

    def _print_summary(self) -> None:
        s = self.stats
        print(
            f"\n--- Crawl summary ---\n"
            f"  Pages processed : {s.pages_processed}/{s.pages_total}\n"
            f"  Images found    : {s.images_found}\n"
            f"  Downloaded      : {s.images_downloaded}\n"
            f"  Skipped (dup)   : {s.images_skipped}\n"
            f"  Failed          : {s.images_failed}\n"
        )
