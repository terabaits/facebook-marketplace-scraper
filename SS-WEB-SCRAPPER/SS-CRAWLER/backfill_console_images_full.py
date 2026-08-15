"""Backfill/repair console listing images.

Fixes the double-dot bug in existing image_url values and downloads the
full-size .800.jpg gallery images for any console_listings rows that are
missing local_image_path.
"""
import os
import re
import hashlib
import logging
import psycopg2
from pathlib import Path
from urllib.parse import urlparse
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_PORT = 5433
DB_NAME = 'ss_market'
DB_USER = 'crawler'
DB_PASSWORD = 'crawler_pass'

IMAGE_DIR = Path('G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/consoles')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.ss.com/',
}


def normalize_image_url(url: str | None) -> str | None:
    if not url:
        return None
    url = url.strip()
    if url.startswith('/'):
        url = f"https://i.ss.com{url}"

    # Fix the double-dot bug produced by the old _extract_image() slicing logic
    url = re.sub(r'\.\.800\.jpg$', '.800.jpg', url)

    # Convert thumbnail suffixes to full size .800.jpg
    url = url.replace('.thumb.', '.').replace('.th.', '.')
    url = re.sub(r'\.t\.jpg$', '.800.jpg', url)
    url = re.sub(r'\.th2\.jpg$', '.800.jpg', url)
    return url


def download_image(image_url: str, listing_id: str) -> str | None:
    """Download image and return local path relative to SS-CRAWLER root, or None."""
    if not image_url:
        return None

    base_listing_id = listing_id
    if "_v" in listing_id:
        parts = listing_id.rsplit("_v", 1)
        if len(parts) == 2 and parts[1].isdigit():
            base_listing_id = parts[0]

    parsed = urlparse(image_url)
    ext = Path(parsed.path).suffix.lower()
    if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        ext = '.jpg'

    url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
    filename = f"{base_listing_id}_{url_hash}{ext}"
    local_path = IMAGE_DIR / filename

    if local_path.exists():
        logger.info(f"Image already exists for {listing_id}: {filename}")
        return str(local_path.relative_to(IMAGE_DIR.parent.parent))

    try:
        resp = requests.get(image_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        content = resp.content

        # ss.com sometimes returns a tiny placeholder for invalid URLs
        if len(content) < 100:
            logger.warning(f"Image too small for {listing_id} ({len(content)} bytes): {image_url}")
            return None

        local_path.write_bytes(content)
        logger.info(f"Downloaded image for {listing_id}: {filename} ({len(content)} bytes)")
        return str(local_path.relative_to(IMAGE_DIR.parent.parent))
    except Exception as e:
        logger.warning(f"Failed to download image for {listing_id}: {e}")
        return None


def main():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password='crawler_pass'
    )
    cur = conn.cursor()

    cur.execute("SELECT listing_id, image_url FROM console_listings WHERE local_image_path IS NULL")
    rows = cur.fetchall()
    logger.info(f"Found {len(rows)} console listings without local_image_path")

    updated = 0
    for listing_id, image_url in rows:
        fixed_url = normalize_image_url(image_url)
        if not fixed_url:
            logger.info(f"Skipping {listing_id}: no image_url")
            continue

        local_path = download_image(fixed_url, listing_id)
        if local_path:
            cur.execute(
                "UPDATE console_listings SET image_url = %s, local_image_path = %s WHERE listing_id = %s",
                (fixed_url, local_path, listing_id)
            )
            updated += 1
        else:
            # If we at least corrected the URL, save it so the next scraper pass can retry
            if fixed_url != image_url:
                cur.execute(
                    "UPDATE console_listings SET image_url = %s WHERE listing_id = %s",
                    (fixed_url, listing_id)
                )

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"Updated {updated} console listings with local images")


if __name__ == '__main__':
    main()
