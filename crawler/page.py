from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from crawler.config import Config

logger = logging.getLogger(__name__)


@dataclass
class PageResult:
    url: str
    title: Optional[str]
    image_urls: list[str] = field(default_factory=list)
    warning: Optional[str] = None  # set when page was skipped or had issues


class PageScraper:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        cfg: Config,
    ) -> None:
        self._session = session
        self._cfg = cfg
        self._timeout = aiohttp.ClientTimeout(total=cfg.timeout)
        self._browser = None  # set externally when Playwright is active

    def attach_browser(self, browser) -> None:
        self._browser = browser

    async def scrape(self, page_url: str) -> PageResult:
        """
        Fetch a page and extract image URLs via CSS selector.
        Uses Playwright when a trigger_selector is configured, otherwise aiohttp.
        Returns None if the page is unreachable or returns a non-2xx status.
        """
        if self._cfg.trigger_selector and self._browser:
            return await self._scrape_with_browser(page_url)
        return await self._scrape_with_aiohttp(page_url)

    async def _scrape_with_browser(self, page_url: str) -> PageResult:
        """Navigate with Playwright, click trigger, wait, then extract."""
        page = await self._browser.new_page()
        try:
            await page.goto(page_url, timeout=self._cfg.timeout * 1000)
            try:
                await page.click(self._cfg.trigger_selector, timeout=5_000)
            except Exception:
                pass  # element not found or not clickable; continue anyway
            if self._cfg.trigger_delay > 0:
                await page.wait_for_timeout(int(self._cfg.trigger_delay * 1000))
            html = await page.content()
        except Exception as exc:
            logger.warning("Browser failed to load %s: %s", page_url, exc)
            return PageResult(url=page_url, title=None, warning=f"Browser failed to load page: {exc}")
        finally:
            await page.close()
        return self._parse_html(page_url, html)

    async def _scrape_with_aiohttp(self, page_url: str) -> PageResult:
        try:
            async with self._session.get(page_url, timeout=self._timeout) as resp:
                if resp.status >= 400:
                    logger.error("HTTP %d fetching page %s", resp.status, page_url)
                    return PageResult(url=page_url, title=None, warning=f"HTTP {resp.status}")
                html = await resp.text()
        except Exception as exc:
            logger.error("Failed to fetch page %s: %s", page_url, exc)
            return PageResult(url=page_url, title=None, warning=f"Failed to fetch: {exc}")
        return self._parse_html(page_url, html)

    def _parse_html(self, page_url: str, html: str) -> PageResult:
        try:
            soup = BeautifulSoup(html, "lxml")
        except Exception as exc:
            logger.error("Failed to parse HTML for %s: %s", page_url, exc)
            return PageResult(url=page_url, title=None, warning=f"Failed to parse HTML: {exc}")

        if self._cfg.title_selector:
            title_el = soup.select_one(self._cfg.title_selector)
            if not title_el:
                logger.warning(
                    "Title selector %r not found on %s — skipping page",
                    self._cfg.title_selector,
                    page_url,
                )
                return PageResult(
                    url=page_url,
                    title=None,
                    warning=f"Title selector {self._cfg.title_selector!r} not found",
                )
            title = title_el.get_text(strip=True)
        else:
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else None

        elements = soup.select(self._cfg.selector)
        if not elements:
            logger.warning(
                "Selector %r not found on %s — skipping page",
                self._cfg.selector,
                page_url,
            )
            return PageResult(
                url=page_url,
                title=title,
                warning=f"Image selector {self._cfg.selector!r} not found",
            )

        image_urls: list[str] = []
        for el in elements:
            src = el.get("src") or el.get("data-src") or ""
            src = src.strip()
            if not src or src.startswith("data:"):
                continue
            abs_url = urljoin(page_url, src)
            image_urls.append(abs_url)

        # Deduplicate while preserving order (same URL can appear multiple times on a page)
        return PageResult(url=page_url, title=title, image_urls=list(dict.fromkeys(image_urls)))
