#!/usr/bin/env python3
"""
Download missing images for active Andele Mandele listings.

Mirrors the pattern used by src/utils/download_missing_matched_images.py (T077)
for ss.com listings, but targets source='andelemandele' instead. It selects active
listings that have an image_url but no local_image_path, downloads each image via
ImageDownloader, and writes the relative local path back to the database.

Usage:
    cd SS-CRAWLER
    python -m src.utils.download_missing_andele_images
    python -m src.utils.download_missing_andele_images --dry-run --limit 5

Optional environment variables (fallback to project config defaults):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import text

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from src.utils.image_downloader import ImageDownloader
from src.utils.logger import get_logger

logger = get_logger("download_missing_andele_images")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _env_or_default(key: str, default):
    """Read an environment variable or return the provided default."""
    value = os.environ.get(key)
    if value is None:
        return default
    if isinstance(default, int):
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Invalid integer for {key}={value!r}, using default {default}")
            return default
    return value


def _load_config() -> AppConfig:
    """Load config.yaml if present, otherwise use defaults."""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml")
    if os.path.exists(config_path):
        return AppConfig.from_yaml(config_path)
    return AppConfig()


def _apply_env_overrides(config: AppConfig) -> AppConfig:
    """Apply DB credentials from environment variables over config defaults."""
    config.database.host = _env_or_default("DB_HOST", config.database.host)
    config.database.port = _env_or_default("DB_PORT", config.database.port)
    config.database.name = _env_or_default("DB_NAME", config.database.name)
    config.database.user = _env_or_default("DB_USER", config.database.user)
    config.database.password = _env_or_default("DB_PASSWORD", config.database.password)
    return config


# ---------------------------------------------------------------------------
# Database queries
# ---------------------------------------------------------------------------

COUNT_MISSING_SQL = text("""
    SELECT COUNT(*)
    FROM listings l
    WHERE l.is_active = TRUE
      AND l.local_image_path IS NULL
      AND l.image_url IS NOT NULL
      AND l.source = 'andelemandele'
""")

SELECT_MISSING_SQL = text("""
    SELECT
        l.listing_id,
        l.category,
        l.image_url
    FROM listings l
    WHERE l.is_active = TRUE
      AND l.local_image_path IS NULL
      AND l.image_url IS NOT NULL
      AND l.source = 'andelemandele'
    ORDER BY l.last_seen_at DESC NULLS LAST
""")

UPDATE_LOCAL_IMAGE_SQL = text("""
    UPDATE listings
    SET local_image_path = :path,
        updated_at = NOW()
    WHERE listing_id = :listing_id
""")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _category_to_folder(category: str) -> str:
    """Map a listing category to the existing image sub-folder name."""
    mapping = {
        "gpu": "gpus",
        "cpu": "cpus",
        "ssd": "ssds",
        "ram": "rams",
        "cases": "cases",
        "case": "cases",
        "psu": "psus",
        "monitor": "monitors",
        "motherboard": "motherboards",
        "camera": "cameras",
        "lens": "lenses",
        "console": "consoles",
        "computer": "computers",
    }
    return mapping.get((category or "").lower(), "misc")


def count_missing_andele_images(session) -> int:
    """Return the number of active Andele listings with image_url but no local path."""
    result = session.execute(COUNT_MISSING_SQL)
    return result.scalar() or 0


def fetch_missing_andele_listings(session) -> List[Tuple[str, str, str]]:
    """Fetch (listing_id, category, image_url) rows that need image downloads."""
    result = session.execute(SELECT_MISSING_SQL)
    return [(row.listing_id, row.category, row.image_url) for row in result.mappings().all()]


def update_local_image_path(session, listing_id: str, local_path: str) -> bool:
    """Persist the relative local image path on the listing row."""
    try:
        session.execute(UPDATE_LOCAL_IMAGE_SQL, {"listing_id": listing_id, "path": local_path})
        return True
    except Exception as exc:
        logger.error(f"Failed to update local_image_path for {listing_id}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Main worker
# ---------------------------------------------------------------------------

def download_missing_andele_images(dry_run: bool = False, limit: Optional[int] = None) -> dict:
    """
    Find active Andele listings without images and download their images.

    Args:
        dry_run: If True, report what would be downloaded without saving files or DB updates.
        limit: Optional cap on how many images to download in this run (0/unset = all).

    Returns:
        Statistics dict with counts for reporting.
    """
    config = _apply_env_overrides(_load_config())
    init_database(config.database)

    stats = {
        "missing_total": 0,
        "processed": 0,
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "dry_run": dry_run,
    }

    with get_session() as session:
        stats["missing_total"] = count_missing_andele_images(session)
        rows = fetch_missing_andele_listings(session)

        if limit:
            rows = rows[:limit]

        if not rows:
            logger.info("No active Andele listings missing images.")
            return stats

        logger.info(
            f"Found {stats['missing_total']} active Andele listings without images; "
            f"processing {len(rows)} in this run."
        )

        # Group rows by category so each group reuses one ImageDownloader instance.
        downloader_by_category: dict[str, ImageDownloader] = {}

        for listing_id, category, image_url in rows:
            stats["processed"] += 1

            folder = _category_to_folder(category)
            downloader = downloader_by_category.setdefault(
                folder, ImageDownloader(base_dir=f"images/{folder}")
            )

            if dry_run:
                logger.info(f"[DRY-RUN] Would download image for {listing_id} ({category}): {image_url}")
                stats["skipped"] += 1
                continue

            local_path = downloader.download_image(image_url, listing_id)

            if local_path:
                update_local_image_path(session, listing_id, local_path)
                stats["downloaded"] += 1
                logger.info(f"Downloaded image for {listing_id} -> {local_path}")
            else:
                stats["failed"] += 1
                logger.warning(f"Failed to download image for {listing_id}: {image_url}")

    logger.info(
        f"Run complete: processed={stats['processed']}, downloaded={stats['downloaded']}, "
        f"failed={stats['failed']}"
    )
    return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entry point with optional --dry-run and --limit flags."""
    parser = argparse.ArgumentParser(
        description="Download missing images for active Andele Mandele listings."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be downloaded without changing files or the database.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of images to download this run (0 = all).",
    )
    args = parser.parse_args()

    try:
        stats = download_missing_andele_images(dry_run=args.dry_run, limit=args.limit or None)
    except Exception as exc:
        logger.exception("download_missing_andele_images failed")
        return 1

    print("\n--- Summary ---")
    print(f"Missing Andele listings : {stats['missing_total']}")
    print(f"Processed in this run     : {stats['processed']}")
    print(f"Downloaded                : {stats['downloaded']}")
    print(f"Failed                    : {stats['failed']}")
    if stats["dry_run"]:
        print("Mode                      : DRY-RUN (no changes made)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
