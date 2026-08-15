"""Fast image backfill for console listings by re-parsing search pages.

This avoids the slow per-listing detail-page fetch in the normal scraper.
It only updates image_url and local_image_path for rows that are missing them.
"""
import os
import re
import hashlib
import logging
import psycopg2
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

DB_HOST = 'localhost'
DB_PORT = 5433
DB_NAME = 'ss_market'
DB_USER = 'crawler'
DB_PASSWORD = 'crawler_pass'

IMAGE_DIR = Path('G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/consoles')
BASE_URL = 'https://www.ss.com/lv/electronics/computers/game-consoles/'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def normalize_image_url(src: str | None) -> str | None:
    if not src:
        return None
    if src.startswith('/'):
        src = f"https://i.ss.com{src}"
    src = src.replace('.thumb.', '.').replace('.th.', '.')
    src = re.sub(r'\.t\.jpg$', '.800.jpg', src)
    src = re.sub(r'\.th2\.jpg$', '.800.jpg', src)
    # Defensive: fix any double-dot before .800.jpg produced by old bugs
    src = re.sub(r'\.\.800\.jpg$', '.800.jpg', src)
    return src


def listing_id_from_url(url: str) -> str:
    m = re.search(r'/([a-z0-9]+)\.html$', url)
    if m:
        return f"ss_{hashlib.md5(url.encode()).hexdigest()[:12]}"
    return f"ss_{hashlib.md5(url.encode()).hexdigest()[:12]}"


def download_image(image_url: str, listing_id: str) -> str | None:
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
        return str(local_path.relative_to(IMAGE_DIR.parent.parent))

    try:
        resp = requests.get(image_url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        content = resp.content
        if len(content) < 100:
            logger.warning(f"Image too small for {listing_id}: {len(content)} bytes")
            return None
        local_path.write_bytes(content)
        logger.info(f"Downloaded image for {listing_id}: {filename} ({len(content)} bytes)")
        return str(local_path.relative_to(IMAGE_DIR.parent.parent))
    except Exception as e:
        logger.warning(f"Failed to download image for {listing_id}: {e}")
        return None


def fetch_search_page(page_num: int) -> BeautifulSoup:
    url = BASE_URL if page_num == 1 else f"{BASE_URL}page{page_num}.html"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, 'html.parser')


def extract_listings(soup: BeautifulSoup) -> dict[str, str]:
    """Return mapping listing_id -> normalized image_url."""
    result = {}
    rows = soup.find_all('tr', id=re.compile(r'^tr_\d+$'))
    for row in rows:
        link = row.find('a', href=re.compile(r'/msg/.*\.html$'))
        if not link:
            continue
        full_url = link['href']
        if full_url.startswith('/'):
            full_url = f"https://www.ss.com{full_url}"
        listing_id = listing_id_from_url(full_url)

        img = row.find('img', src=re.compile(r'gallery|i\.ss\.com'))
        if not img:
            continue
        image_url = normalize_image_url(img.get('src'))
        if image_url:
            result[listing_id] = image_url
    return result


def main():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD
    )
    cur = conn.cursor()

    # Get listing IDs that need images
    cur.execute("SELECT listing_id FROM console_listings WHERE local_image_path IS NULL")
    needed = {row[0] for row in cur.fetchall()}
    logger.info(f"{len(needed)} console listings need images")

    found = {}
    for page in range(1, 6):
        try:
            soup = fetch_search_page(page)
            page_found = extract_listings(soup)
            found.update(page_found)
            logger.info(f"Page {page}: parsed {len(page_found)} listings (total unique {len(found)})")
            if not needed.difference(found):
                logger.info("All needed listings found; stopping early")
                break
        except Exception as e:
            logger.error(f"Failed to fetch page {page}: {e}")

    updated = 0
    for listing_id in needed:
        image_url = found.get(listing_id)
        if not image_url:
            logger.info(f"No image URL found on search pages for {listing_id}")
            continue
        local_path = download_image(image_url, listing_id)
        if local_path:
            cur.execute(
                "UPDATE console_listings SET image_url = %s, local_image_path = %s WHERE listing_id = %s",
                (image_url, local_path, listing_id)
            )
            updated += 1
        else:
            cur.execute(
                "UPDATE console_listings SET image_url = %s WHERE listing_id = %s",
                (image_url, listing_id)
            )

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Updated {updated} console listings with local images")


if __name__ == '__main__':
    main()
