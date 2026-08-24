"""Andele Mandele scraper - integrates with existing matchers."""
import time
import logging
import re
import subprocess
import base64
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.parsers.andele_parser import AndeleParser, AndeleListingData
from src.models.schemas import Listing, ScrapeRun
from src.database.connection import get_session
from src.database.repository import ListingRepository, ScrapeRunRepository
from src.utils.logger import get_logger

# Import existing matchers
from src.scraper.matcher import GPUMatcher
from src.scraper.cpu_matcher import CPUMatcher
from src.scraper.ssd_matcher import SSDMatcher
from src.scraper.ram_matcher import RAMMatcher
from src.scraper.psu_matcher import PSUMatcher
from src.scraper.monitor_scraper import MonitorMatcher
from src.scraper.motherboard_matcher import MotherboardMatcher

logger = get_logger("andele_scraper")


def get_chrome_version():
    """Get installed Chrome version for undetected-chromedriver."""
    try:
        result = subprocess.run(
            ['reg', 'query', r'HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon', '/v', 'version'],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            match = re.search(r'version\s+REG_SZ\s+([\d\.]+)', result.stdout)
            if match:
                return int(match.group(1).split('.')[0])
    except:
        pass
    
    try:
        paths = [
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        ]
        import os
        paths.append(os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'))
        for path in paths:
            if os.path.exists(path):
                result = subprocess.run([path, '--version'], capture_output=True, text=True)
                if result.returncode == 0:
                    match = re.search(r'(\d+)', result.stdout)
                    if match:
                        return int(match.group(1))
    except:
        pass
    
    return None


class AndeleScrapeResult:
    """Result of a scrape operation."""
    
    def __init__(self):
        self.total: int = 0
        self.new: int = 0
        self.updated: int = 0
        self.failed: int = 0
        self.skipped: int = 0
        self.errors: List[str] = []
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total': self.total,
            'new': self.new,
            'updated': self.updated,
            'failed': self.failed,
            'skipped': self.skipped,
            'errors': self.errors,
        }


class AndeleScraper:
    """Scraper for Andele Mandele marketplace."""
    
    BASE_URL = "https://www.andelemandele.lv"
    REQUEST_DELAY = 1.5  # Seconds between requests
    MAX_RETRIES = 3
    
    # Category to URL mapping
    CATEGORY_URLS = {
        'gpu': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:409',
        'cpu': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:405',
        'ssd': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:404',
        'ram': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:406',
        'psu': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:415',
        'computer': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:413',
        'monitor': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:578',
        'motherboard': 'https://www.andelemandele.lv/perles/tehnika/datori/#order:actual/attributes:403',
    }

    # Andele attribute IDs per category (used for direct API filtering).
    # The Vue.js shop uses hash-fragment filters client-side; the actual data
    # fetch goes to /product-data/?filter=<base64 json>. We use this for
    # reliable, server-side filtering.
    CATEGORY_ATTRIBUTE_IDS = {
        'gpu':        409,
        'cpu':        405,
        'ssd':        404,
        'ram':        406,
        'psu':        415,
        'computer':   413,
        'monitor':    578,
        'motherboard':403,
    }

    # Parent category ID for "Datori" (Computers) — the umbrella category
    # that all the computer-component filters live under.
    PARENT_CATEGORY_ID = 368

    # URL of the SPA's product data endpoint.
    PRODUCT_DATA_URL = "https://www.andelemandele.lv/product-data/"

    # Headers needed so the /product-data/ endpoint accepts our request.
    # Without Origin + Referer the response is 403.
    API_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'lv,en-US;q=0.7,en;q=0.3',
        'Origin': 'https://www.andelemandele.lv',
        'Referer': 'https://www.andelemandele.lv/perles/tehnika/datori/',
    }
    
    def __init__(self, db_session: Optional[Session] = None, dry_run: bool = False):
        """Initialize scraper.
        
        Args:
            db_session: Database session (creates new if None)
            dry_run: If True, don't save to database
        """
        self.parser = AndeleParser()
        self.dry_run = dry_run
        self.result = AndeleScrapeResult()
        
        # Initialize matchers
        self.matchers = {}
        self._init_matchers()
        
        # Request headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'lv,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        
    def _init_matchers(self):
        """Initialize all component matchers with reference data."""
        from src.database.repository import (
            GPUReferenceRepository, CPUReferenceRepository, 
            SSDReferenceRepository, RAMReferenceRepository
        )
        from src.database.connection import get_session, init_database
        from src.utils.config import AppConfig
        
        # Initialize database if not already done
        try:
            config = AppConfig.from_yaml()
            init_database(config.database)
            logger.info("Database initialized for matchers")
        except Exception as e:
            logger.warning(f"Database already initialized or error: {e}")
        
        try:
            with get_session() as session:
                # GPU matcher
                try:
                    gpus = GPUReferenceRepository.get_all(session)
                    self.matchers['gpu'] = GPUMatcher(gpus)
                    logger.info(f"Initialized GPU matcher with {len(gpus)} GPUs")
                except Exception as e:
                    logger.warning(f"Could not initialize GPU matcher: {e}")
                
                # CPU matcher
                try:
                    cpus = CPUReferenceRepository.get_all(session)
                    self.matchers['cpu'] = CPUMatcher(cpus)
                    logger.info(f"Initialized CPU matcher with {len(cpus)} CPUs")
                except Exception as e:
                    logger.warning(f"Could not initialize CPU matcher: {e}")
                
                # SSD matcher
                try:
                    ssds = SSDReferenceRepository.get_all(session)
                    self.matchers['ssd'] = SSDMatcher(ssds)
                    logger.info(f"Initialized SSD matcher with {len(ssds)} SSDs")
                except Exception as e:
                    logger.warning(f"Could not initialize SSD matcher: {e}")
                
                # RAM matcher
                try:
                    rams = RAMReferenceRepository.get_all(session)
                    self.matchers['ram'] = RAMMatcher(rams)
                    logger.info(f"Initialized RAM matcher with {len(rams)} RAMs")
                except Exception as e:
                    logger.warning(f"Could not initialize RAM matcher: {e}")
                
                # PSU matcher
                try:
                    from src.database.repository import PSURepository
                    psus = PSURepository.get_all(session)
                    self.matchers['psu'] = PSUMatcher(psus)
                    logger.info(f"Initialized PSU matcher with {len(psus)} PSUs")
                except Exception as e:
                    logger.warning(f"Could not initialize PSU matcher: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to initialize matchers: {e}")
            
        # Monitor matcher (doesn't need database)
        try:
            self.matchers['monitor'] = MonitorMatcher([])
            logger.info("Initialized Monitor matcher")
        except Exception as e:
            logger.warning(f"Could not initialize Monitor matcher: {e}")
            
        # Motherboard matcher (doesn't need database for now)
        try:
            from src.database.repository import MotherboardRepository
            with get_session() as session:
                motherboards = MotherboardRepository.get_all(session)
                self.matchers['motherboard'] = MotherboardMatcher(motherboards)
                logger.info(f"Initialized Motherboard matcher with {len(motherboards)} boards")
        except Exception as e:
            logger.warning(f"Could not initialize Motherboard matcher: {e}")
        
        # Computer matcher - loads all components
        try:
            from src.scraper.computer_matcher import ComputerMatcher
            from src.database.repository import (
                CPUReferenceRepository, GPUReferenceRepository,
                RAMReferenceRepository, SSDReferenceRepository,
                PSURepository, CaseRepository, MotherboardRepository
            )
            with get_session() as session:
                cpus = CPUReferenceRepository.get_all(session)
                gpus = GPUReferenceRepository.get_all(session)
                rams = RAMReferenceRepository.get_all(session)
                ssds = SSDReferenceRepository.get_all(session)
                psus = PSURepository.get_all(session)
                cases = CaseRepository.get_all(session)
                motherboards = MotherboardRepository.get_all(session)
                monitors = []  # Andele doesn't have monitors reference yet
                self.matchers['computer'] = ComputerMatcher(
                    cpus, gpus, rams, ssds, psus, cases, motherboards, monitors
                )
                logger.info(f"Initialized Computer matcher")
        except Exception as e:
            logger.warning(f"Could not initialize Computer matcher: {e}")
            
    def _fetch_page(self, url: str, retries: int = 0) -> Optional[str]:
        """Fetch page with retries and rate limiting."""
        if retries >= self.MAX_RETRIES:
            logger.error(f"Max retries exceeded for {url}")
            return None
            
        try:
            time.sleep(self.REQUEST_DELAY)
            
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            time.sleep(self.REQUEST_DELAY * (retries + 1))  # Exponential backoff
            return self._fetch_page(url, retries + 1)
    
    def _fetch_page_with_browser(self, url: str) -> Optional[str]:
        """Fetch page using browser automation to execute JavaScript.
        
        This loads the full Vue.js app and waits for all listings to appear.
        """
        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
        except ImportError:
            logger.warning("undetected-chromedriver not installed, falling back to requests")
            return self._fetch_page(url)
        
        driver = None
        try:
            logger.info(f"Starting browser for {url}")
            
            options = uc.ChromeOptions()
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--headless=new")  # Headless mode
            
            chrome_ver = get_chrome_version()
            if chrome_ver:
                logger.info(f"Detected Chrome version: {chrome_ver}")
                driver = uc.Chrome(options=options, version_main=chrome_ver)
            else:
                driver = uc.Chrome(options=options)
            
            driver.get(url)
            
            # Wait for Vue.js to load listings
            # Try multiple selectors
            selectors = [
                'a[href*="/perle/"]',
                '.product-list a',
                '.listing-grid a',
                '[class*="product"] a[href*="/perle/"]',
            ]
            
            # Wait up to 10 seconds for listings to appear
            wait = WebDriverWait(driver, 10)
            found = False
            for selector in selectors:
                try:
                    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                    logger.info(f"Listings found with selector: {selector}")
                    found = True
                    break
                except:
                    continue
            
            if not found:
                logger.warning("No listings found after wait, returning what we have")
            
            # Additional wait for any lazy-loaded content
            time.sleep(2)
            
            # Scroll down to load more listings (if infinite scroll or lazy loading)
            logger.info("Scrolling to load more content...")
            for scroll_attempt in range(5):
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1.5)

                # Check if more listings appeared
                new_height = driver.execute_script("return document.body.scrollHeight")

                # Try clicking "Load More" or "Show More" buttons. Use
                # proper XPath/text matching (`:contains(...)` is jQuery, not
                # valid CSS — it was throwing "invalid selector" before).
                try:
                    load_more_buttons = driver.find_elements(
                        By.XPATH,
                        '//button[contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "vairāk") '
                        'or contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "more") '
                        'or contains(translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "vēl")]'
                    )
                    for btn in load_more_buttons:
                        try:
                            if btn.is_displayed():
                                btn.click()
                                logger.info("Clicked load more button")
                                time.sleep(2)
                        except Exception:
                            pass
                except Exception:
                    pass

                # Also try common class-based load-more buttons
                for selector in ('.load-more', '.show-more', '[data-action="load-more"]'):
                    try:
                        for btn in driver.find_elements(By.CSS_SELECTOR, selector):
                            try:
                                if btn.is_displayed():
                                    btn.click()
                                    logger.info(f"Clicked {selector} button")
                                    time.sleep(2)
                            except Exception:
                                pass
                    except Exception:
                        pass
            
            # Get the fully rendered HTML
            html = driver.page_source
            
            logger.info(f"Browser loaded {url}, HTML length: {len(html)}")
            return html
            
        except Exception as e:
            logger.error(f"Browser fetch failed for {url}: {e}")
            # Fall back to regular requests
            return self._fetch_page(url)
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
    # ============================================================
    # New: direct product-data API approach (reliable filter)
    # ============================================================
    #
    # The /perles/tehnika/datori/ page is a Vue.js SPA. The hash-fragment
    # filter (`#order:actual/attributes:409`) is applied client-side AFTER
    # the page loads, so any naive scrape of the HTML picks up the spotlight
    # ad carousel at the top instead of the real GPU/CPU/etc. results.
    #
    # The actual data fetch that powers the SPA is:
    #   GET /product-data/?filter=<base64 of {category, order, attributes}>
    # That endpoint returns {html: <article cards>, count: N} and is
    # filter-correct. We use it as the source of truth for listing URLs.
    #
    # Each listing's full page is then fetched separately for title/desc.

    def _build_product_data_filter(self, category: str) -> str:
        """Build the base64 filter payload for /product-data/.

        The format mirrors what the Vue.js SPA sends:
        {"category":{"id":368},"order":"actual","attributes":["<id>"]}
        """
        attr_id = self.CATEGORY_ATTRIBUTE_IDS.get(category)
        if attr_id is None:
            raise ValueError(f"Unknown category for product-data filter: {category}")
        payload = {
            "category": {"id": self.PARENT_CATEGORY_ID},
            "order": "actual",
            "attributes": [str(attr_id)],
        }
        return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")

    def _fetch_product_data(self, category: str) -> Tuple[List[Dict[str, Any]], int]:
        """Call /product-data/ directly to get the truly-filtered listings.

        Returns:
            (listings, total_count) where each listing dict has:
                - id: str (Andele product id)
                - url: str (full listing URL)
                - slug: str (last URL segment without id)
                - price_eur: float or None
                - old_price_eur: float or None
                - image_url: str or None
                - image_urls: list[str] (all gallery images)
                - brand: str or None
        """
        filter_b64 = self._build_product_data_filter(category)
        api_url = f"{self.PRODUCT_DATA_URL}?filter={filter_b64}"
        logger.info(f"Calling product-data API for {category}: {api_url[:100]}…")

        try:
            r = requests.get(api_url, headers=self.API_HEADERS, timeout=30)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            logger.error(f"product-data API failed for {category}: {e}")
            return [], 0

        if not isinstance(data, dict):
            logger.error(f"Unexpected product-data response type: {type(data).__name__}")
            return [], 0

        html = data.get("html") or ""
        # `count` comes back as a localized string like "21 pērle" — extract
        # the leading integer.
        raw_count = data.get("count") or 0
        if isinstance(raw_count, str):
            m = re.search(r"\d+", raw_count)
            count = int(m.group(0)) if m else 0
        else:
            try:
                count = int(raw_count)
            except (TypeError, ValueError):
                count = 0
        logger.info(f"product-data returned count={count}, html_len={len(html)}")

        listings = self._parse_product_data_html(html)
        return listings, count

    def _parse_product_data_html(self, html: str) -> List[Dict[str, Any]]:
        """Parse the article cards returned by /product-data/.

        Each card looks like:
            <article data-role="product-card" data-id="16041869" ...>
              <figure>
                <a href="/perle/16041869/rtx-3060-12gb-dual-oc/"></a>
                <div data-role="thumbnail" style="background-image: url(...);"></div>
                <a data-role="gallery.pic" href="...large/...webp"></a>  (x N)
              </figure>
              <figcaption>
                <header>
                  <span class="product-card__price">300 €</span>
                  <span class="product-card__old-price">700 €</span>
                  ...
                </header>
                <ul class="product-card__attr">
                  <li><a href="/brand/asus/7320/">Asus</a></li>
                </ul>
              </figcaption>
            </article>

        Spotlight/recommended items also use /perle/ links but include
        ?utm_medium=spotlight in the href — we skip those here.
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        listings: List[Dict[str, Any]] = []
        seen_ids: set = set()

        for article in soup.find_all("article", attrs={"data-role": "product-card"}):
            pid = article.get("data-id", "").strip()
            if not pid or pid in seen_ids:
                continue

            link = article.find("a", href=re.compile(r"^/perle/\d+/"))
            if not link or not link.get("href"):
                continue
            href = link["href"]

            # Skip spotlight/recommended ads — they pollute the listing pool
            if "utm_medium=spotlight" in href or "utm_campaign" in href:
                continue

            full_url = urljoin(self.BASE_URL, href)
            slug = href.rstrip("/").split("/")[-1] if "/" in href else ""

            # Prices
            def _price(span_class: str) -> Optional[float]:
                el = article.find("span", class_=span_class)
                if not el:
                    return None
                txt = el.get_text(strip=True)
                m = re.search(r"(\d+(?:[.,]\d+)?)", txt)
                if not m:
                    return None
                try:
                    return float(m.group(1).replace(",", "."))
                except ValueError:
                    return None

            price = _price("product-card__price")
            old_price = _price("product-card__old-price")

            # Images — prefer explicit gallery; fall back to thumbnail
            image_urls: List[str] = []
            for a in article.find_all("a", attrs={"data-role": "gallery.pic"}):
                g = a.get("href", "").strip()
                if g and g.startswith("http") and g not in image_urls:
                    image_urls.append(g)
            thumb = article.find("div", attrs={"data-role": "thumbnail"})
            if thumb and thumb.get("style"):
                m = re.search(r"url\(([^)]+)\)", thumb["style"])
                if m:
                    raw = m.group(1).strip().strip("'\"")
                    if raw.startswith("http") and raw not in image_urls:
                        # Upgrade thumbnail → large
                        raw_large = raw.replace("/thumbnail/", "/large/")
                        image_urls.append(raw_large if raw_large != raw else raw)
            image_url = image_urls[0] if image_urls else None

            # Brand
            brand_el = article.find("ul", class_="product-card__attr")
            brand = None
            if brand_el:
                a = brand_el.find("a")
                if a:
                    brand = a.get_text(strip=True) or None

            listings.append({
                "id": pid,
                "url": full_url,
                "slug": slug,
                "price_eur": price,
                "old_price_eur": old_price,
                "image_url": image_url,
                "image_urls": image_urls,
                "brand": brand,
            })
            seen_ids.add(pid)

        return listings

    def scrape_category(self, category: str, max_pages: int = 0, limit: int = 0) -> AndeleScrapeResult:
        """Scrape a specific category.

        Strategy:
          1. Call /product-data/?filter=<base64> directly to get the truly
             filter-correct listing URLs (no spotlight ads, no JS hash
             filter race-conditions).
          2. For each listing, fetch the full product page to extract
             title/description/location/date, apply matchers, and save.

        Args:
            category: Category name (gpu, cpu, ssd, etc.)
            max_pages: Max pages to scrape (0 = unlimited, ignored by the
                       API approach because the API returns all results in
                       one call).
            limit: Max listings total (0 = unlimited).

        Returns:
            AndeleScrapeResult with statistics
        """
        if category not in self.CATEGORY_URLS:
            logger.error(f"Unknown category: {category}")
            self.result.errors.append(f"Unknown category: {category}")
            return self.result

        url = self.CATEGORY_URLS[category]
        logger.info(f"Starting scrape of {category} from {url}")

        # Try the direct /product-data/ API first.
        listings, total_count = self._fetch_product_data(category)

        if not listings:
            # Fall back to browser-based scraping (less reliable because the
            # hash filter is client-side and the spotlight carousel can leak
            # through, but it works as a last resort).
            logger.warning(
                f"product-data API returned no listings for {category}; "
                f"falling back to browser scrape"
            )
            return self._scrape_category_browser(category, max_pages, limit)

        logger.info(
            f"Got {len(listings)} real filtered listings for {category} "
            f"(API reported {total_count} total)"
        )

        processed = 0
        for entry in listings:
            if limit > 0 and processed >= limit:
                logger.info(f"Reached limit ({limit})")
                break
            self._process_listing(entry["url"], category, pre_data=entry)
            processed += 1

        logger.info(f"Completed {category}: {self.result.to_dict()}")
        return self.result

    def _scrape_category_browser(self, category: str, max_pages: int = 0,
                                  limit: int = 0) -> AndeleScrapeResult:
        """Browser-based fallback for category scraping.

        Used only if the /product-data/ API call returns nothing. Loads the
        SPA page in a real browser and waits for the actual filter results
        (skipping the spotlight ad carousel that the SPA renders at the top
        before the hash filter takes effect).
        """
        url = self.CATEGORY_URLS[category]
        pages_scraped = 0
        total_listings = 0

        while url:
            if max_pages > 0 and pages_scraped >= max_pages:
                logger.info(f"Reached max pages ({max_pages})")
                break

            logger.info(f"Scraping page {pages_scraped + 1}: {url}")
            html = self._fetch_page_with_browser(url)

            if not html:
                self.result.errors.append(f"Failed to fetch {url}")
                break

            listing_urls, next_url = self.parser.parse_category_page(html, url)
            # Strip spotlight/utm ad links even from the browser path
            listing_urls = [
                u for u in listing_urls
                if "utm_medium=spotlight" not in u and "utm_campaign" not in u
            ]
            logger.info(f"Found {len(listing_urls)} real listings on this page (after filtering ads)")

            for listing_url in listing_urls:
                if limit > 0 and total_listings >= limit:
                    logger.info(f"Reached limit ({limit})")
                    return self.result
                self._process_listing(listing_url, category)
                total_listings += 1

            pages_scraped += 1
            url = next_url

        logger.info(f"Completed {category} (browser): {self.result.to_dict()}")
        return self.result
        
    def scrape_listing(self, url: str, category_hint: Optional[str] = None) -> Optional[AndeleListingData]:
        """Scrape a single listing.
        
        Args:
            url: Listing URL
            category_hint: Optional category hint (for matching)
            
        Returns:
            AndeleListingData or None if failed
        """
        html = self._fetch_page(url)
        if not html:
            return None
            
        try:
            data = self.parser.parse_listing_page(html, url)
            
            # Detect category if not provided
            if not category_hint:
                category_hint = self.parser.detect_category_from_title(data.title)
                
            # Apply matchers
            self._apply_matchers(data, category_hint)
            
            return data
            
        except Exception as e:
            logger.error(f"Error scraping listing {url}: {e}")
            self.result.errors.append(f"Error scraping {url}: {e}")
            return None
            
    def _process_listing(self, url: str, category: str,
                         pre_data: Optional[Dict[str, Any]] = None):
        """Process a single listing - fetch, parse, match, save.

        Args:
            url: Listing URL.
            category: Category hint.
            pre_data: Optional pre-fetched data from the /product-data/ API
                (price, image URLs, brand). Used to avoid re-parsing things
                we already know. The full listing page is still fetched for
                title/description.
        """
        self.result.total += 1

        try:
            data = self.scrape_listing(url, category)
            if not data:
                self.result.failed += 1
                return

            # Backfill anything missing from the full page with pre_data.
            # Price is most likely to differ (andele shows current + old on
            # the card; the full page only shows current).
            if pre_data:
                if pre_data.get("price_eur") and not data.price_eur:
                    data.price_eur = pre_data["price_eur"]
                if pre_data.get("image_urls") and not data.image_urls:
                    data.image_urls = pre_data["image_urls"]
                # If the listing page parser couldn't find a title, fall
                # back to the URL slug (humanized).
                if not data.title and pre_data.get("slug"):
                    data.title = pre_data["slug"].replace("-", " ").strip()

            if self.dry_run:
                logger.info(f"[DRY RUN] Would save: {data.title[:50]}...")
                return

            # Convert to Listing model and save
            listing = self._convert_to_listing(data, category)
            
            # Log matched info
            if hasattr(data, '_matched_gpu_id') and data._matched_gpu_id:
                logger.info(f"✨ GPU Match: {data.title[:50]}... -> GPU ID {data._matched_gpu_id} ({data._confidence_score:.0%})")
            elif hasattr(data, '_matched_cpu_id') and data._matched_cpu_id:
                logger.info(f"✨ CPU Match: {data.title[:50]}... -> CPU ID {data._matched_cpu_id} ({data._cpu_confidence_score:.0%})")
            
            # Save via repository - use get_session context manager
            from src.database.connection import get_session
            with get_session() as session:
                saved_listing, action = ListingRepository.create_or_update(
                    session, listing, None  # run_id = None for now
                )
                session.commit()
                
            # Log image info for debugging
            logger.info(f"🖼️  Found {len(data.image_urls)} images for {listing.listing_id}: {data.title[:50]}...")
            if data.image_urls:
                for i, img_url in enumerate(data.image_urls[:3]):
                    logger.info(f"   Image {i+1}: {img_url[:80]}...")
            
            # Download images if any (always try, even for unchanged listings)
            if data.image_urls:
                from src.utils.image_downloader import ImageDownloader
                downloader = ImageDownloader(f"images/{category}")
                local_paths = downloader.download_images(data.image_urls, listing.listing_id)
                
                if local_paths:
                    # Update database with local image path (first image)
                    with get_session() as session:
                        ListingRepository.update_local_image_path(
                            session, listing.listing_id, local_paths[0]
                        )
                        session.commit()
                    logger.info(f"📸 Downloaded {len(local_paths)} images for {listing.listing_id}")
                else:
                    logger.warning(f"⚠️  Failed to download images for {listing.listing_id}")
            else:
                logger.info(f"📷 No images found for {listing.listing_id}")
            
            if action == 'new' or action == 'new_version':
                self.result.new += 1
            elif action == 'updated':
                self.result.updated += 1
            else:
                self.result.skipped += 1
                
        except Exception as e:
            logger.error(f"Error processing listing {url}: {e}")
            import traceback
            traceback.print_exc()
            self.result.failed += 1
            self.result.errors.append(f"Error processing {url}: {e}")
            
    def _apply_matchers(self, data: AndeleListingData, category: str):
        """Apply component matchers to listing data."""
        title_lower = data.title.lower()
        desc_lower = (data.description or "").lower()
        full_text = f"{title_lower} {desc_lower}"
        
        # Apply category-specific matcher
        if category in self.matchers and category in ['gpu', 'cpu', 'ssd', 'ram', 'psu', 'monitor', 'motherboard']:
            matcher = self.matchers[category]
            
            try:
                if category == 'gpu':
                    result = matcher.match(data.title, full_text)
                    if result and result.confidence >= 0.5:
                        data.category = 'gpu'
                        # Store match info in data for later conversion
                        data._matched_gpu_id = result.gpu.id if result.gpu else None
                        data._confidence_score = result.confidence
                        data._match_method = result.method
                        
                elif category == 'cpu':
                    # Pass full_text as secondary input — Andele's product-data
                    # API only returns the slug as title (e.g. "AMD Ryzen 9"),
                    # but the description has the full model number
                    # (e.g. "AMD Ryzen 9 7900 procesors"). Without the secondary
                    # input the matcher would pick the wrong model.
                    result = matcher.match(data.title, full_text)
                    if result and result.confidence >= 0.5:
                        data.category = 'cpu'
                        data._matched_cpu_id = result.cpu.id if result.cpu else None
                        data._cpu_confidence_score = result.confidence
                        data._cpu_match_method = result.method
                        
                elif category == 'ssd':
                    result = matcher.match(data.title, full_text)
                    if result and result.confidence >= 0.5:
                        data.category = 'ssd'
                        data._matched_ssd_id = result.ssd.id if result.ssd else None
                        data._ssd_confidence_score = result.confidence
                        data._ssd_match_method = result.method
                        data._capacity_gb = result.ssd.capacity_gb if result.ssd else None
                        
                elif category == 'ram':
                    # Same fix as cpu — Andele's product-data API doesn't
                    # include the full model number in the title; the
                    # description has it.
                    result = matcher.match(data.title, full_text)
                    if result and result.confidence >= 0.5:
                        data.category = 'ram'
                        data._matched_ram_id = result.ram.id if hasattr(result, 'ram') and result.ram else None
                        data._ram_confidence_score = result.confidence
                        data._ram_match_method = result.method
                        
                elif category == 'psu':
                    result = matcher.match(data.title, full_text)
                    if result and result.confidence >= 0.5:
                        data.category = 'psu'
                        data._matched_psu_id = result.psu.id if result.psu else None
                        data._psu_confidence_score = result.confidence
                        data._psu_match_method = result.method
                        
                elif category == 'monitor':
                    result = matcher.match(data.title, full_text)
                    if result and result.confidence >= 0.5:
                        data.category = 'monitor'
                        data._matched_monitor_id = result.monitor.id if result.monitor else None
                        data._monitor_confidence_score = result.confidence
                        data._monitor_match_method = result.method
                        
                elif category == 'motherboard':
                    result = matcher.match(data.title, full_text)
                    if result and result.confidence >= 0.5:
                        data.category = 'motherboard'
                        data._matched_motherboard_id = result.motherboard.id if result.motherboard else None
                        data._motherboard_confidence_score = result.confidence
                        data._motherboard_match_method = result.method
                        
                elif category == 'computer':
                    # For computers, we match all components from the full text
                    result = matcher.match(data.title, data.description or "")
                    if result:
                        data.category = 'computer'
                        data._computer_match_result = result
                        # Extract component IDs
                        if hasattr(result, 'cpu') and result.cpu:
                            data._matched_cpu_id = result.cpu.id
                        if hasattr(result, 'gpu') and result.gpu:
                            data._matched_gpu_id = result.gpu.id
                        if hasattr(result, 'ram') and result.ram:
                            data._matched_ram_id = result.ram.id
                        if hasattr(result, 'ssd') and result.ssd:
                            data._matched_ssd_id = result.ssd.id
                        if hasattr(result, 'psu') and result.psu:
                            data._matched_psu_id = result.psu.id
                        if hasattr(result, 'case') and result.case:
                            data._matched_case_id = result.case.id
                        if hasattr(result, 'motherboard') and result.motherboard:
                            data._matched_motherboard_id = result.motherboard.id
                        if hasattr(result, 'monitor') and result.monitor:
                            data._monitor_model_id = result.monitor.id
                        
            except Exception as e:
                logger.warning(f"Matcher error for {category}: {e}")
                
    def _convert_to_listing(self, data: AndeleListingData, category: str) -> Listing:
        """Convert AndeleListingData to Listing model."""
        listing = Listing(
            listing_id=data.listing_id or f"andele_{int(time.time())}",
            title=data.title,
            description=data.description,
            price_eur=data.price_eur or 0.0,
            seller_location=data.seller_location or 'X',  # Default to X if location not extracted
            listing_url=data.listing_url,
            image_url=data.image_urls[0] if data.image_urls else None,
            date_posted=data.date_posted or datetime.now(),
            category=data.category if hasattr(data, 'category') else category,
            source='andelemandele',  # Key: mark as Andele source
            is_active=True,
        )
        
        # Add matcher results if available
        if hasattr(data, '_matched_gpu_id'):
            listing.matched_gpu_id = data._matched_gpu_id
            listing.confidence_score = getattr(data, '_confidence_score', None)
            listing.match_method = getattr(data, '_match_method', None)
            
        if hasattr(data, '_matched_cpu_id'):
            listing.matched_cpu_id = data._matched_cpu_id
            listing.cpu_confidence_score = getattr(data, '_cpu_confidence_score', None)
            listing.cpu_match_method = getattr(data, '_cpu_match_method', None)
            
        if hasattr(data, '_matched_ssd_id'):
            listing.matched_ssd_id = data._matched_ssd_id
            listing.ssd_confidence_score = getattr(data, '_ssd_confidence_score', None)
            listing.ssd_match_method = getattr(data, '_ssd_match_method', None)
            listing.capacity_gb = getattr(data, '_capacity_gb', None)
            
        if hasattr(data, '_matched_ram_id'):
            listing.matched_ram_id = data._matched_ram_id
            listing.ram_confidence_score = getattr(data, '_ram_confidence_score', None)
            listing.ram_match_method = getattr(data, '_ram_match_method', None)
            
        if hasattr(data, '_matched_psu_id'):
            # PSU fields might need custom handling
            pass
            
        if hasattr(data, '_matched_monitor_id'):
            listing.monitor_model_id = data._matched_monitor_id
            listing.monitor_confidence_score = getattr(data, '_monitor_confidence_score', None)
            listing.monitor_match_method = getattr(data, '_monitor_match_method', None)
            
        if hasattr(data, '_matched_motherboard_id'):
            listing.motherboard_model_id = data._matched_motherboard_id
            listing.motherboard_confidence_score = getattr(data, '_motherboard_confidence_score', None)
            listing.motherboard_match_method = getattr(data, '_motherboard_match_method', None)
            
        return listing
        
    def test_url(self, url: str, category: str = 'general') -> Optional[Dict[str, Any]]:
        """Test parsing a single URL and return detailed info.
        
        Used for CLI test-url command.
        """
        logger.info(f"Testing URL: {url}")
        
        html = self._fetch_page(url)
        if not html:
            return {'error': 'Failed to fetch page'}
            
        try:
            data = self.parser.parse_listing_page(html, url)
            
            # Apply matchers
            self._apply_matchers(data, category)
            
            # Save if not in dry_run mode
            if not self.dry_run:
                from src.database.connection import get_session
                from src.database.repository import ListingRepository
                
                listing = self._convert_to_listing(data, category)
                with get_session() as session:
                    # Use run_id=None for test-url (no scrape run tracking needed)
                    saved, action = ListingRepository.create_or_update(session, listing, None)
                    session.commit()
                    logger.info(f"Saved listing {saved.listing_id} to database (action: {action})")
            
            # Build result
            result = {
                'success': True,
                'listing_id': data.listing_id,
                'title': data.title,
                'price_eur': data.price_eur,
                'description_preview': data.description[:200] if data.description else None,
                'seller_location': data.seller_location,
                'date_posted': str(data.date_posted) if data.date_posted else None,
                'image_count': len(data.image_urls),
                'category': data.category if hasattr(data, 'category') else category,
                'match': {},
                'saved': not self.dry_run,
            }
            
            # Add match info
            if hasattr(data, '_matched_gpu_id') and data._matched_gpu_id:
                result['match']['gpu'] = {
                    'id': data._matched_gpu_id,
                    'confidence': data._confidence_score,
                    'method': data._match_method,
                }
            elif hasattr(data, '_matched_cpu_id') and data._matched_cpu_id:
                result['match']['cpu'] = {
                    'id': data._matched_cpu_id,
                    'confidence': data._cpu_confidence_score,
                    'method': data._cpu_match_method,
                }
            elif hasattr(data, '_matched_ssd_id') and data._matched_ssd_id:
                result['match']['ssd'] = {
                    'id': data._matched_ssd_id,
                    'confidence': data._ssd_confidence_score,
                    'method': data._ssd_match_method,
                    'capacity_gb': getattr(data, '_capacity_gb', None),
                }
                
            return result
            
        except Exception as e:
            logger.error(f"Error testing URL: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}


# For CLI testing
if __name__ == '__main__':
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) < 2:
        print("Usage: python andele_scraper.py <url> [category]")
        sys.exit(1)
        
    url = sys.argv[1]
    category = sys.argv[2] if len(sys.argv) > 2 else 'general'
    
    scraper = AndeleScraper(dry_run=True)
    result = scraper.test_url(url, category)
    
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
