from __future__ import annotations

import asyncio
import logging
import sys
import aiohttp

from crawler.cli import parse_and_validate
from crawler.config import Config
from crawler.downloader import ImageDownloader
from crawler.fs import folder_for_page
from crawler.page import PageScraper
from crawler.progress import CrawlProgress
from crawler.report import write_report
from crawler.sitemap import read_urls
from crawler.state import StateManager

try:
    from playwright.async_api import async_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def run(config: Config) -> None:
    config.output.mkdir(parents=True, exist_ok=True)

    state = StateManager(config.output)
    state.load()

    headers = {"User-Agent": config.user_agent}
    connector = aiohttp.TCPConnector(limit=config.concurrency + 10)

    playwright_instance = None
    browser = None

    if config.trigger_selector:
        if not _PLAYWRIGHT_AVAILABLE:
            logging.getLogger(__name__).error(
                "--trigger-selector requires Playwright. Install it with: "
                "pip install playwright && playwright install chromium"
            )
            sys.exit(1)
        playwright_instance = await async_playwright().start()
        browser = await playwright_instance.chromium.launch(headless=True)

    log = logging.getLogger(__name__)
    log.info("Reading URLs from: %s", config.urls_file)
    try:
        page_urls = read_urls(config.urls_file)
    except OSError as exc:
        log.error("Failed to read URLs file: %s", exc)
        sys.exit(1)

    if not page_urls:
        log.warning("No page URLs found in file.")
        return

    async with aiohttp.ClientSession(headers=headers, connector=connector) as session:

        if config.url_filter:
            log.debug("Sample URLs from file: %s", page_urls[:5])
            before = len(page_urls)
            page_urls = [u for u in page_urls if config.url_filter in u]
            log.info("url-filter %r: %d → %d pages", config.url_filter, before, len(page_urls))
            if not page_urls:
                log.warning(
                    "url-filter %r matched 0 URLs. Re-run with --log-level DEBUG to see sample URLs.",
                    config.url_filter,
                )

        if config.limit is not None:
            page_urls = page_urls[:config.limit]
            logging.getLogger(__name__).info("--limit %d: crawling first %d page(s).", config.limit, len(page_urls))

        log.info("Found %d page(s) to crawl.", len(page_urls))

        progress = CrawlProgress(
            total_pages=len(page_urls),
            no_progress=config.no_progress,
        )
        scraper = PageScraper(session, config)
        if browser:
            scraper.attach_browser(browser)
        downloader = ImageDownloader(
            session=session,
            state=state,
            concurrency=config.concurrency,
            timeout=config.timeout,
            dry_run=config.dry_run,
            progress=progress,
            redownload=config.redownload,
            image_quality=config.image_quality,
        )

        report_rows: list[tuple[str, str]] = []

        try:
            for i, page_url in enumerate(page_urls):
                progress.start_page(page_url)
                log.debug("Scraping page: %s", page_url)

                result = await scraper.scrape(page_url)

                if result.warning is not None:
                    report_rows.append((page_url, result.warning))
                    progress.finish_page(0)
                    if i < len(page_urls) - 1 and config.delay > 0:
                        await asyncio.sleep(config.delay)
                    continue

                folder = folder_for_page(result.title, result.url, config.output)
                log.debug(
                    "Page '%s': %d image(s) -> %s",
                    result.title or page_url,
                    len(result.image_urls),
                    folder,
                )

                if result.image_urls:
                    await downloader.download_batch(result.image_urls, folder)
                    report_rows.append((page_url, ""))
                else:
                    report_rows.append((page_url, "No downloadable images found"))

                progress.finish_page(len(result.image_urls))
                state.save()

                if i < len(page_urls) - 1 and config.delay > 0:
                    await asyncio.sleep(config.delay)

        except KeyboardInterrupt:
            log.info("Interrupted — saving state.")
        finally:
            state.save()
            progress.close()
            report_path = config.output / "report.xlsx"
            write_report(report_rows, report_path)
            log.info("Report written to %s", report_path)
            if browser:
                await browser.close()
            if playwright_instance:
                await playwright_instance.stop()


def main() -> None:
    args = parse_and_validate()
    config = Config.from_args(args)
    setup_logging(config.log_level)
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
