from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _validate_urls_file(value: str) -> str:
    p = Path(value)
    if p.is_file():
        return str(p.resolve())
    raise argparse.ArgumentTypeError(
        f"--urls-file must be an existing file path, got: {value!r}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="image-crawler",
        description="Crawl pages from a URL list file and download images via CSS selector.",
    )
    parser.add_argument(
        "--urls-file",
        required=True,
        type=_validate_urls_file,
        help="Path to a text file containing page URLs, one per line",
    )
    parser.add_argument(
        "--selector",
        required=True,
        help='CSS selector to match image elements (e.g. "article img")',
    )
    parser.add_argument(
        "--output",
        default="./downloads",
        help="Directory to save downloaded images (default: ./downloads)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent image downloads per page (default: 5, range: 1-50)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Seconds to wait between page requests (default: 1.0)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "--user-agent",
        default="image-crawler/1.0",
        help='User-Agent header (default: "image-crawler/1.0")',
    )
    parser.add_argument(
        "--redownload",
        action="store_true",
        help="Re-download images that were already downloaded in a previous run",
    )
    parser.add_argument(
        "--image-quality",
        type=int,
        default=85,
        metavar="N",
        help="Lossy compression quality for JPEG and WebP images (1-95, default: 85). "
             "Has no effect on PNG, GIF, or other formats.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List images without downloading them",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Suppress tqdm progress bars",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    parser.add_argument(
        "--trigger-selector",
        default=None,
        metavar="SELECTOR",
        help="CSS selector of element to click on each page before extracting images (requires Playwright)",
    )
    parser.add_argument(
        "--trigger-delay",
        type=float,
        default=2.0,
        metavar="SECONDS",
        help="Seconds to wait after triggering before extracting images (default: 2.0)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Max number of pages to crawl (default: no limit)",
    )
    parser.add_argument(
        "--url-filter",
        metavar="PATTERN",
        default=None,
        help="Only crawl pages whose URL contains this word or substring (e.g. 'articles')",
    )
    parser.add_argument(
        "--title-selector",
        required=True,
        metavar="SELECTOR",
        help="CSS selector to extract the folder title from each page; page is skipped if not found",
    )
    return parser


def parse_and_validate(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not (1 <= args.concurrency <= 50):
        parser.error("--concurrency must be between 1 and 50")

    if not (1 <= args.image_quality <= 95):
        parser.error("--image-quality must be between 1 and 95")

    if args.delay < 0:
        parser.error("--delay must be >= 0")

    if args.timeout < 1:
        parser.error("--timeout must be >= 1")

    return args
