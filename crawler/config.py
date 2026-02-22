from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    urls_file: str
    selector: str
    output: Path
    concurrency: int
    delay: float
    timeout: int
    user_agent: str
    redownload: bool
    dry_run: bool
    no_progress: bool
    log_level: str
    title_selector: str
    trigger_selector: str | None = None
    trigger_delay: float = 2.0
    url_filter: str | None = None
    limit: int | None = None
    image_quality: int = 85

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "Config":
        return cls(
            urls_file=args.urls_file,
            selector=args.selector,
            output=Path(args.output),
            concurrency=args.concurrency,
            delay=args.delay,
            timeout=args.timeout,
            user_agent=args.user_agent,
            redownload=args.redownload,
            dry_run=args.dry_run,
            no_progress=args.no_progress,
            log_level=args.log_level,
            trigger_selector=args.trigger_selector,
            trigger_delay=args.trigger_delay,
            url_filter=args.url_filter,
            title_selector=args.title_selector,
            limit=args.limit,
            image_quality=args.image_quality,
        )
