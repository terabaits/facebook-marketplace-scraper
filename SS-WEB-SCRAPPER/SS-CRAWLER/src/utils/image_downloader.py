"""Image downloader for saving listing images locally with versioning support."""
import hashlib
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse
import requests
from src.utils.logger import get_logger

logger = get_logger("image_downloader")


class ImageDownloader:
    """Downloads and manages listing images locally.

    With listing versioning, images are stored using the BASE listing ID
    (without _v2, _v3 suffixes) so all versions share the same image storage.
    This prevents duplicate downloads and wasted space.

    Example:
        Listing ID: gexxm, gexxm_v2, gexxm_v3
        Image storage: images/computers/gexxm_abc123.jpg (shared)

    Each version still stores its own image_url in the database, but if the
    image is the same across versions, it's only stored once on disk.
    """

    MIN_IMAGE_BYTES = 100

    def __init__(self, base_dir: str = "images/computers"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_base_listing_id(self, listing_id: str) -> str:
        """
        Extract base listing ID without version suffix.

        Args:
            listing_id: May be 'gexxm' or 'gexxm_v2', 'gexxm_v3'

        Returns:
            Base ID without version (e.g., 'gexxm')
        """
        if "_v" in listing_id:
            parts = listing_id.rsplit("_v", 1)
            if len(parts) == 2 and parts[1].isdigit():
                return parts[0]
        return listing_id

    @staticmethod
    def _normalize_image_url(image_url: str) -> str:
        """Normalize an image URL to a known-good image format.

        Andele Mandele serves both `.webp` and `.jpg` from the same path
        (the server just sets a different Content-Type and ships different
        bytes). `.webp` is unusable for our downstream image pipeline
        (PIL/legacy browser support), so always swap to `.jpg` when the
        extension is `.webp`. Falls back to the original URL if there's
        no extension to swap.

        Verified (2026-08-20) on static*.andelemandele.lv:
            .../abc123.webp -> image/webp,  79378 bytes
            .../abc123.jpg  -> image/jpeg, 228771 bytes
        """
        if not image_url:
            return image_url
        # Only swap the last extension; leave the rest of the URL alone.
        if image_url.lower().endswith(".webp"):
            return image_url[:-5] + ".jpg"
        return image_url

    def _local_path(self, image_url: str, listing_id: str) -> Path:
        """Compute local file path for an image URL (without downloading)."""
        base_listing_id = self._get_base_listing_id(listing_id)
        # Normalize .webp -> .jpg so the saved file matches the actual
        # bytes we download (and so downstream consumers see `.jpg`).
        normalized_url = self._normalize_image_url(image_url)
        parsed = urlparse(normalized_url)
        path = parsed.path
        ext = Path(path).suffix.lower()
        if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            ext = '.jpg'
        # Hash the ORIGINAL url so re-normalizing doesn't change the
        # filename for a re-download (hash is stable for the same input).
        url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
        filename = f"{base_listing_id}_{url_hash}{ext}"
        return self.base_dir / filename

    def download_image(self, image_url: str, listing_id: str) -> Optional[str]:
        """
        Download image from URL and save locally.

        Args:
            image_url: Original image URL
            listing_id: Listing ID (may include version suffix like _v2)

        Returns:
            Local path relative to base_dir, or None if download failed
        """
        if not image_url:
            return None

        # Normalize .webp -> .jpg (Andele serves both from the same path;
        # .jpg is what downstream consumers expect).
        download_url = self._normalize_image_url(image_url)

        try:
            local_path = self._local_path(image_url, listing_id)

            # Skip if already exists AND is not a tiny placeholder
            if local_path.exists():
                existing_size = local_path.stat().st_size
                if existing_size >= self.MIN_IMAGE_BYTES:
                    logger.debug(f"Image already exists: {local_path.name}")
                    return str(local_path.relative_to(self.base_dir.parent))
                logger.info(f"Existing image is a placeholder ({existing_size} bytes), re-downloading: {local_path.name}")

            # Pick the right Referer per host. Andele's image CDN can be
            # picky about cross-origin requests, so use its own origin.
            if "andelemandele.lv" in download_url:
                referer = "https://www.andelemandele.lv/"
            else:
                referer = "https://www.ss.com/"

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': referer,
            }

            def _try_download(url: str) -> bytes:
                resp = requests.get(url, headers=headers, timeout=30)
                resp.raise_for_status()
                return resp.content

            content = _try_download(download_url)

            # If the download is tiny/placeholder, try known ss.com gallery fallbacks
            if len(content) < self.MIN_IMAGE_BYTES:
                fallback_urls = []
                if image_url.endswith('.jpg') and not image_url.endswith('.t.jpg') and not image_url.endswith('.800.jpg'):
                    fallback_urls.append(image_url[:-4] + '.t.jpg')
                    fallback_urls.append(image_url[:-4] + '.800.jpg')
                if image_url.endswith('.800.jpg'):
                    fallback_urls.append(image_url[:-8] + '.t.jpg')
                for fb in fallback_urls:
                    try:
                        logger.info(f"Trying fallback image URL for {listing_id}: {fb}")
                        content = _try_download(fb)
                        if len(content) >= self.MIN_IMAGE_BYTES:
                            image_url = fb
                            break
                    except Exception:
                        pass
                else:
                    if len(content) < self.MIN_IMAGE_BYTES:
                        logger.warning(f"Image too small for {listing_id} ({len(content)} bytes), skipping save")
                        return None

            # Recompute local_path in case fallback changed image_url
            local_path = self._local_path(image_url, listing_id)

            # Save image
            with open(local_path, 'wb') as f:
                f.write(content)

            logger.info(f"Downloaded image for {listing_id} (stored as {local_path.name}, {len(content)} bytes)")
            return str(local_path.relative_to(self.base_dir.parent))

        except Exception as e:
            logger.warning(f"Failed to download image for {listing_id}: {e}")
            return None

    def download_images(self, image_urls: List[str], listing_id: str) -> List[str]:
        """Download multiple images for a listing."""
        local_paths = []
        for url in image_urls:
            path = self.download_image(url, listing_id)
            if path:
                local_paths.append(path)
        return local_paths

    def get_local_url(self, relative_path: str) -> str:
        """Convert relative path to local file URL."""
        if not relative_path:
            return ""
        return f"/static/images/{relative_path}"
