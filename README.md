# image-crawler

A CLI tool that crawls pages from a URL list file and downloads images via CSS selector. Supports headless browser mode for cookie banners and lazy-loaded content, and resumable downloads.

---

## Installation

```bash
# 1. Create virtual environment (one time)
python3 -m venv .venv

# 2. Activate it
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browser (only needed for --trigger-selector)
playwright install chromium
```

> **Note:** You must activate the virtual environment (`source .venv/bin/activate`) each time you open a new terminal session before running `python main.py`.

---

## Basic Usage

```bash
python main.py --urls-file <FILE> --selector <CSS_SELECTOR> --title-selector <TITLE_SELECTOR> [OPTIONS]
```

`--urls-file`, `--selector`, and `--title-selector` are required. Everything else is optional.

---

## URL List File

Create a plain text file with one URL per line. Blank lines and lines starting with `#` are ignored.

```
# my urls
https://example.com/shop/products/item-1
https://example.com/shop/products/item-2
```

```bash
python main.py \
  --urls-file ./urls.txt \
  --selector "article img" \
  --title-selector "h1"
```

---

## Headless Browser Mode

When a page hides images behind a cookie consent banner or requires a button click to reveal content, use `--trigger-selector` to click that element before extracting images. This mode uses Playwright (Chromium) instead of plain HTTP requests.

```bash
python main.py \
  --urls-file ./urls.txt \
  --selector "figure img" \
  --trigger-selector "#cookie-accept" \
  --trigger-delay 2.0 \
  --title-selector "h1"
```

- If the trigger element is not found on a given page, the crawler continues gracefully without error.
- `--trigger-delay` controls how long to wait after the click (default: 2 seconds). Increase it if content loads slowly.
- Without `--trigger-selector`, Playwright is never launched and the lightweight `aiohttp` path is used.

---

## Dry Run

Preview what would be downloaded without writing any files to disk:

```bash
python main.py \
  --urls-file ./urls.txt \
  --selector "article img" \
  --title-selector "h1" \
  --dry-run
```

---

## All Options

| Option | Default | Description |
|---|---|---|
| `--urls-file` | *(required)* | Path to a text file containing page URLs, one per line |
| `--selector` | *(required)* | CSS selector matching image elements on each page |
| `--title-selector` | *(required)* | CSS selector to extract the folder name from each page; page is skipped if not found |
| `--output` | `./downloads` | Directory where images are saved |
| `--concurrency` | `5` | Max simultaneous image downloads per page (1–50) |
| `--delay` | `1.0` | Seconds to wait between page requests |
| `--timeout` | `30` | HTTP/browser request timeout in seconds |
| `--user-agent` | `image-crawler/1.0` | `User-Agent` header sent with requests |
| `--trigger-selector` | *(none)* | CSS selector of element to click before scraping (enables Playwright) |
| `--trigger-delay` | `2.0` | Seconds to wait after the click before extracting images |
| `--limit` | *(none)* | Max number of pages to crawl |
| `--url-filter` | *(none)* | Word or substring; only pages whose URL contains it are crawled |
| `--redownload` | `false` | Re-download images already downloaded in a previous run |
| `--image-quality` | `85` | Lossy re-compression quality for JPEG/WebP after download (1–95); other formats are unchanged |
| `--dry-run` | `false` | Preview image URLs without downloading |
| `--no-progress` | `false` | Suppress progress bars |
| `--log-level` | `INFO` | Verbosity: `DEBUG` `INFO` `WARNING` `ERROR` |

---

## Output Structure

Images are saved under `--output`, organised into per-page sub-folders named after the page title (falling back to the URL path segment):

```
downloads/
  My_Article_Title/
    hero_image.jpg
    figure_01.png
  another_page_slug/
    photo.jpg
```

A `.state.json` file is kept in the output directory to track already-downloaded URLs. Re-running the crawler skips files that were downloaded in a previous run.

---

## Resuming an Interrupted Crawl

Just run the same command again. The state file ensures already-downloaded images are skipped automatically.

To force all images to be fetched again regardless of the state file, add `--redownload`:

```bash
python main.py \
  --urls-file ./urls.txt \
  --selector "article img" \
  --title-selector "h1" \
  --redownload
```

---

## Common Recipes

```bash
# High-throughput crawl (20 concurrent downloads, no delay)
python main.py \
  --urls-file ./urls.txt \
  --selector "img" \
  --title-selector "h1" \
  --concurrency 20 \
  --delay 0

# Slow/polite crawl with verbose logging
python main.py \
  --urls-file ./urls.txt \
  --selector "article img" \
  --title-selector "h1" \
  --delay 3.0 \
  --log-level DEBUG

# Save to a custom folder, suppress progress bars (good for scripts/CI)
python main.py \
  --urls-file ./urls.txt \
  --selector ".gallery img" \
  --title-selector "h1" \
  --output /data/images \
  --no-progress

# Click cookie banner then wait 3 s before extracting images
python main.py \
  --urls-file ./urls.txt \
  --selector "figure img" \
  --title-selector "h1" \
  --trigger-selector "#cookie-accept" \
  --trigger-delay 3.0
```
