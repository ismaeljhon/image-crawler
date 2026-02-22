# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Only needed when using --trigger-selector (Playwright-based scraping)
playwright install chromium
```

## Running the crawler

```bash
python main.py \
  --urls-file urls.txt \
  --selector "article img" \
  --title-selector "h1.entry-title" \
  --output ./downloads
```

Common flags:
- `--dry-run` — list images without downloading
- `--redownload` — re-fetch images already in state
- `--limit N` — cap pages crawled (useful for testing)
- `--url-filter PATTERN` — only crawl URLs containing PATTERN
- `--trigger-selector SELECTOR` — click an element before scraping (requires Playwright)
- `--log-level DEBUG` — verbose output

## Architecture

The entry point is `main.py`, which wires together all components and drives the async crawl loop. All configuration is passed through a `Config` dataclass (`crawler/config.py`), built once from CLI args and threaded through the system.

**Data flow per page:**
1. `sitemap.read_urls()` reads the plain-text URL list file
2. `PageScraper.scrape()` fetches each page (via aiohttp or Playwright) and parses HTML with BeautifulSoup/lxml, extracting image `src`/`data-src` attributes matching the CSS selector and the page title via `--title-selector`
3. `fs.folder_for_page()` derives a sanitized output folder name from the page title (or URL slug as fallback)
4. `ImageDownloader.download_batch()` downloads images concurrently, bounded by a semaphore; uses `resolve_filename()` to handle collisions atomically with an in-flight `reserved` set
5. After each image download, `_compress_image()` re-encodes JPEG/WebP at `--image-quality` using Pillow
6. `StateManager` persists a `.state.json` in the output directory (atomic write via temp file + `os.replace`) to enable resumable runs and duplicate skipping
7. After all pages, `report.write_report()` generates a `report.xlsx` with per-page status and any warnings

**Playwright path:** activated when `--trigger-selector` is set. `PageScraper.attach_browser()` receives a Playwright browser instance; `_scrape_with_browser()` navigates, clicks the trigger element, waits `--trigger-delay` seconds, then extracts HTML for the same BeautifulSoup parsing pipeline.

**Duplicate detection:** two layers — `StateManager.is_downloaded(url)` (URL-based, across runs) and `url_to_base_path()` existence check (file-based, catches manual additions).

## Key files

| File | Role |
|---|---|
| `main.py` | Entry point; async orchestration loop |
| `crawler/cli.py` | Argument parsing and validation |
| `crawler/config.py` | `Config` dataclass |
| `crawler/page.py` | `PageScraper` — HTTP fetch + HTML parse |
| `crawler/downloader.py` | `ImageDownloader` — async download + compression |
| `crawler/state.py` | `StateManager` — persistent `.state.json` |
| `crawler/fs.py` | Filename/path sanitization utilities |
| `crawler/sitemap.py` | URL list file reader |
| `crawler/progress.py` | tqdm progress bars + crawl stats |
| `crawler/report.py` | xlsx report generation |
