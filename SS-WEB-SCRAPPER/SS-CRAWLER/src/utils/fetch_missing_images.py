#!/usr/bin/env python3
"""
Fetch missing image URLs from ss.com listing pages and download the images.

This script fixes listings where image_url is NULL or where only a thumbnail
was stored. It re-fetches the listing page from ss.com, extracts the main
image(s), upgrades thumbnail URLs to full-size URLs, stores the URL in the
database, and downloads the image to the project's image folders.

Usage:
    cd SS-CRAWLER
    python -m src.utils.fetch_missing_images --dry-run --limit 5
    python -m src.utils.fetch_missing_images --limit 100 --categories ssd ram
    python -m src.utils.fetch_missing_images                      # all categories
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.image_downloader import ImageDownloader
from src.utils.logger import get_logger

logger = get_logger("fetch_missing_images")

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
}

IMAGE_SELECTOR = "img.pic_thumbnail"

# Map DB category values to existing image folder names.
CATEGORY_TO_FOLDER = {
    "gpu": "gpus",
    "cpu": "cpus",
    "ssd": "ssds",
    "ram": "rams",
    "case": "cases",
    "cases": "cases",
    "psu": "psus",
    "monitor": "monitors",
    "monitors": "monitors",
    "motherboard": "motherboards",
    "motherboards": "motherboards",
    "camera": "cameras",
    "lens": "lenses",
    "console": "consoles",
    "computer": "computers",
    "computers": "computers",
}


def _load_config() -> AppConfig:
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml")
    if os.path.exists(config_path):
        return AppConfig.from_yaml(config_path)
    return AppConfig()


def _env_or_default(key: str, default):
    value = os.environ.get(key)
    if value is None:
        return default
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            return default
    return value


def _apply_env_overrides(config: AppConfig) -> AppConfig:
    config.database.host = _env_or_default("DB_HOST", config.database.host)
    config.database.port = _env_or_default("DB_PORT", config.database.port)
    config.database.name = _env_or_default("DB_NAME", config.database.name)
    config.database.user = _env_or_default("DB_USER", config.database.user)
    config.database.password = _env_or_default("DB_PASSWORD", config.database.password)
    return config


def _category_to_folder(category: str) -> str:
    return CATEGORY_TO_FOLDER.get(category.lower(), "misc")


def _make_absolute_url(src: str) -> str:
    if src.startswith("//"):
        return f"https:{src}"
    if src.startswith("/"):
        return f"https://www.ss.com{src}"
    if src.startswith("http"):
        return src
    return f"https://www.ss.com/{src.lstrip('/')}"


def _is_thumbnail_url(url: str) -> bool:
    return bool(url) and (url.endswith(".t.jpg") or ".thumb." in url or ".th." in url)


def _upgrade_to_full_url(url: str) -> str:
    """Convert ss.com thumbnail URLs to the largest available image URL."""
    if url.endswith(".t.jpg"):
        return f"{url[:-6]}.800.jpg"
    if ".thumb." in url:
        return url.replace(".thumb.", ".")
    if ".th." in url:
        return url.replace(".th.", ".")
    return url


def _extract_image_urls(html: str, url: str) -> List[str]:
    """Return largest available image URLs for the listing page."""
    soup = BeautifulSoup(html, "html.parser")
    imgs = soup.select(IMAGE_SELECTOR)
    if not imgs:
        return []

    urls = []
    for img in imgs:
        src = img.get("src") or img.get("data-src")
        if not src:
            continue

        src = _make_absolute_url(src)

        # ss.com thumbnails use .t.jpg. The larger versions are .800.jpg.
        if src.endswith(".t.jpg"):
            base = src[:-6]  # strip .t.jpg
            urls.append(f"{base}.800.jpg")
        elif ".thumb." in src:
            urls.append(src.replace(".thumb.", "."))
        elif ".th." in src:
            urls.append(src.replace(".th.", "."))
        else:
            urls.append(src)

    return urls


def _fetch_listing_page(url: str) -> Optional[str]:
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        logger.warning(f"Failed to fetch {url}: {exc}")
        return None


def fetch_missing_images(
    dry_run: bool = False,
    limit: Optional[int] = None,
    categories: Optional[List[str]] = None,
    delay_seconds: float = 0.5,
    upgrade_existing_thumbnails: bool = True,
) -> dict:
    config = _apply_env_overrides(_load_config())
    init_database(config.database)

    stats = {
        "missing_total": 0,
        "thumbnail_total": 0,
        "processed": 0,
        "image_url_found": 0,
        "upgraded": 0,
        "image_url_not_found": 0,
        "downloaded": 0,
        "failed": 0,
        "dry_run": dry_run,
    }

    # Build category filter.
    category_clause = ""
    params = {}
    if categories:
        normalized = [c.strip().lower() for c in categories]
        category_clause = "AND LOWER(l.category) = ANY(:categories)"
        params["categories"] = normalized

    missing_count_sql = text(f"""
        SELECT COUNT(*)
        FROM listings l
        WHERE l.is_active = TRUE
          AND l.image_url IS NULL
          AND (l.source = 'ss.com' OR l.listing_url LIKE 'https://www.ss.com%%')
          {category_clause}
    """)

    thumb_count_sql = text(f"""
        SELECT COUNT(*)
        FROM listings l
        WHERE l.is_active = TRUE
          AND l.image_url IS NOT NULL
          AND (l.image_url LIKE '%%.t.jpg' OR l.image_url LIKE '%%.thumb.%%' OR l.image_url LIKE '%%.th.%%')
          AND (l.source = 'ss.com' OR l.listing_url LIKE 'https://www.ss.com%%')
          {category_clause}
    """)

    select_missing_sql = text(f"""
        SELECT l.listing_id, l.category, l.listing_url, NULL AS image_url
        FROM listings l
        WHERE l.is_active = TRUE
          AND l.image_url IS NULL
          AND (l.source = 'ss.com' OR l.listing_url LIKE 'https://www.ss.com%%')
          {category_clause}
        ORDER BY l.last_seen_at DESC NULLS LAST
    """)

    select_thumbnails_sql = text(f"""
        SELECT l.listing_id, l.category, l.listing_url, l.image_url
        FROM listings l
        WHERE l.is_active = TRUE
          AND l.image_url IS NOT NULL
          AND (l.image_url LIKE '%%.t.jpg' OR l.image_url LIKE '%%.thumb.%%' OR l.image_url LIKE '%%.th.%%')
          AND (l.source = 'ss.com' OR l.listing_url LIKE 'https://www.ss.com%%')
          {category_clause}
        ORDER BY l.last_seen_at DESC NULLS LAST
    """)

    update_image_url_sql = text("""
        UPDATE listings
        SET image_url = :image_url,
            updated_at = NOW()
        WHERE listing_id = :listing_id
    """)

    update_local_path_sql = text("""
        UPDATE listings
        SET local_image_path = :path,
            updated_at = NOW()
        WHERE listing_id = :listing_id
    """)

    downloader_by_folder: dict[str, ImageDownloader] = {}

    def _process_one(session, listing_id: str, category: str, url: str, existing_image_url: Optional[str] = None):
        """Fetch page, extract/upgrade image URL, download, and persist."""
        if not url or not url.startswith("http"):
            logger.warning(f"Skipping {listing_id}: invalid URL {url}")
            stats["image_url_not_found"] += 1
            return

        html = _fetch_listing_page(url)
        if html is None:
            stats["image_url_not_found"] += 1
            return

        image_urls = _extract_image_urls(html, url)
        if not image_urls:
            logger.info(f"No image found on page for {listing_id} ({url})")
            stats["image_url_not_found"] += 1
            return

        primary_url = image_urls[0]

        # If we already have a thumbnail URL for this listing, upgrade it.
        if existing_image_url and _is_thumbnail_url(existing_image_url):
            upgraded = _upgrade_to_full_url(existing_image_url)
            if upgraded != existing_image_url:
                primary_url = upgraded
                stats["upgraded"] += 1
                logger.info(f"Upgrading thumbnail for {listing_id}: {existing_image_url} -> {primary_url}")
            else:
                logger.info(f"Image URL already full-size for {listing_id}: {primary_url}")
        else:
            stats["image_url_found"] += 1
            logger.info(f"Found image for {listing_id}: {primary_url}")

        if dry_run:
            return

        # Persist image_url.
        session.execute(
            update_image_url_sql,
            {"listing_id": listing_id, "image_url": primary_url},
        )

        # Download image.
        folder = _category_to_folder(category)
        downloader = downloader_by_folder.setdefault(
            folder, ImageDownloader(base_dir=f"images/{folder}")
        )
        local_path = downloader.download_image(primary_url, listing_id)

        if local_path:
            session.execute(
                update_local_path_sql,
                {"listing_id": listing_id, "path": local_path},
            )
            stats["downloaded"] += 1
            logger.info(f"Downloaded image for {listing_id} -> {local_path}")
        else:
            stats["failed"] += 1
            logger.warning(f"Failed to download image for {listing_id}: {primary_url}")

        if delay_seconds:
            sleep(delay_seconds)

    with get_session() as session:
        stats["missing_total"] = session.execute(missing_count_sql, params).scalar() or 0
        stats["thumbnail_total"] = (
            session.execute(thumb_count_sql, params).scalar() or 0
            if upgrade_existing_thumbnails else 0
        )

        rows = list(session.execute(select_missing_sql, params).mappings().all())
        if upgrade_existing_thumbnails:
            rows.extend(list(session.execute(select_thumbnails_sql, params).mappings().all()))

        if limit:
            rows = rows[:limit]

        if not rows:
            logger.info("No listings need image fetching/upgrading.")
            return stats

        logger.info(
            f"Found {stats['missing_total']} listings without image_url and "
            f"{stats['thumbnail_total']} thumbnail URLs to upgrade; "
            f"processing {len(rows)} in this run."
        )

        for row in rows:
            stats["processed"] += 1
            listing_id = row["listing_id"]
            category = row["category"]
            url = row["listing_url"]
            existing_image_url = row.get("image_url")
            _process_one(session, listing_id, category, url, existing_image_url)

    logger.info(
        f"Run complete: processed={stats['processed']}, "
        f"image_url_found={stats['image_url_found']}, "
        f"upgraded={stats['upgraded']}, "
        f"downloaded={stats['downloaded']}, failed={stats['failed']}"
    )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch missing image URLs from ss.com listing pages and download images."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be fetched without changing the database or downloading files.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of listings to process this run (0 = all).",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default="",
        help="Comma-separated list of categories to process (e.g., ssd,ram,monitor).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds to wait between requests to ss.com (default 0.5).",
    )
    parser.add_argument(
        "--skip-thumbnail-upgrade",
        action="store_true",
        help="Do not re-process existing thumbnail URLs (only fetch missing ones).",
    )
    args = parser.parse_args()

    categories = [c.strip() for c in args.categories.split(",") if c.strip()] or None

    try:
        stats = fetch_missing_images(
            dry_run=args.dry_run,
            limit=args.limit or None,
            categories=categories,
            delay_seconds=args.delay,
            upgrade_existing_thumbnails=not args.skip_thumbnail_upgrade,
        )
    except Exception:
        logger.exception("fetch_missing_images failed")
        return 1

    print("\n--- Summary ---")
    print(f"Missing image_url total    : {stats['missing_total']}")
    print(f"Thumbnail URLs to upgrade  : {stats['thumbnail_total']}")
    print(f"Processed in this run      : {stats['processed']}")
    print(f"Image URL found            : {stats['image_url_found']}")
    print(f"Upgraded thumbnails        : {stats['upgraded']}")
    print(f"No image URL on page       : {stats['image_url_not_found']}")
    print(f"Downloaded                 : {stats['downloaded']}")
    print(f"Failed downloads           : {stats['failed']}")
    if stats["dry_run"]:
        print("Mode                       : DRY-RUN")

    return 0


if __name__ == "__main__":
    sys.exit(main())
