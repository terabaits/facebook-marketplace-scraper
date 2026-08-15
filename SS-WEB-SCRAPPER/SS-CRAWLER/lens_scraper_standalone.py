#!/usr/bin/env python3
"""
Standalone Lens Scraper for SS.COM
Scrapes camera lens listings and saves to CSV.
"""

import re
import csv
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("lens_scraper")


@dataclass
class LensListing:
    """Represents a lens listing."""
    listing_id: str
    title: str
    price_raw: str
    price_eur: float
    price_usd: float
    currency: str
    location: str
    url: str
    posted_date: str
    description: str
    seller_name: str = ""
    phone: str = ""
    matched_lens_id: str = ""
    confidence_score: float = 0.0
    match_method: str = "none"


class LensScraper:
    """Scraper for camera lens listings from ss.com"""
    
    BASE_URL = "https://www.ss.com"
    CATEGORY_URL = "/lv/electronics/photo-optics/objectives/"
    
    # Filter patterns
    FILTER_BRANDS = ['nikon']
    FILTER_STORES = ['internetveikals']
    FILTER_CONDITION = ['jauns']
    
    # USD to EUR conversion rate
    USD_TO_EUR = 0.92
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.lens_references = []
        self.stats = {
            'processed': 0,
            'filtered': 0,
            'matched': 0,
            'failed': 0
        }
    
    def _load_lens_references(self, csv_path: str = "lenses.csv"):
        """Load lens reference data from CSV."""
        ref_path = Path(csv_path)
        if ref_path.exists():
            with open(ref_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.lens_references = list(reader)
            logger.info(f"Loaded {len(self.lens_references)} lens references from {csv_path}")
        else:
            logger.warning(f"Lens references file not found: {csv_path}")
    
    def _fetch(self, url: str) -> Optional[str]:
        """Fetch URL and return HTML content."""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def _extract_price(self, text: str) -> Tuple[float, str, str]:
        """Extract price from text. Returns (eur_value, raw_text, currency)."""
        # Look for patterns like "120 €", "1,200 €", "120.50 €"
        price_match = re.search(r'([\d\s.,]+)\s*€', text)
        if price_match:
            raw_price = price_match.group(1).replace(' ', '').replace(',', '.')
            try:
                eur_value = float(raw_price)
                usd_value = eur_value / self.USD_TO_EUR
                return eur_value, price_match.group(0), 'EUR'
            except ValueError:
                pass
        
        # Check for "$" prices
        usd_match = re.search(r'\$([\d\s.,]+)', text)
        if usd_match:
            raw_price = usd_match.group(1).replace(' ', '').replace(',', '.')
            try:
                usd_value = float(raw_price)
                eur_value = usd_value * self.USD_TO_EUR
                return eur_value, usd_match.group(0), 'USD'
            except ValueError:
                pass
        
        return 0.0, "", ""
    
    def _extract_location(self, html: str) -> str:
        """Extract seller location from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try ads_contacts class
        contacts = soup.find('td', class_='ads_contacts')
        if contacts:
            return contacts.get_text(strip=True)
        
        # Try td_address class
        address = soup.find('td', class_='td_address')
        if address:
            return address.get_text(strip=True)
        
        # Try to find location in page text
        loc_match = re.search(r'(?:Vieta|Atrašanās vieta|Location)[\s:]*([^<\n]+)', html, re.IGNORECASE)
        if loc_match:
            return loc_match.group(1).strip()
        
        return ""
    
    def _extract_description(self, html: str) -> str:
        """Extract listing description."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try to find main content
        content_div = soup.find('div', id='msg_div_msg')
        if content_div:
            return content_div.get_text(separator=' ', strip=True)
        
        # Try finding description in meta or other areas
        desc = soup.find('meta', {'name': 'description'})
        if desc:
            return desc.get('content', '')
        
        return ""
    
    def _extract_date(self, html: str) -> str:
        """Extract posting date from HTML."""
        # Look for date patterns
        date_match = re.search(r'(\d{1,2}\.\d{1,2}\.\d{4})', html)
        if date_match:
            return date_match.group(1)
        
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', html)
        if date_match:
            return date_match.group(1)
        
        return datetime.now().strftime('%Y-%m-%d')
    
    def _should_filter(self, title: str, description: str = "") -> Tuple[bool, str]:
        """Check if listing should be filtered out."""
        full_text = f"{title} {description}".lower()
        
        if 'nikon' in full_text:
            return True, "filtered_nikon"
        
        if 'internetveikals' in full_text:
            return True, "filtered_internetveikals"
        
        if 'jauns' in full_text:
            return True, "filtered_jauns"
        
        return False, ""
    
    def _match_lens(self, title: str, description: str = "") -> Tuple[str, float, str]:
        """Match lens to reference database."""
        full_text = f"{title} {description}".lower()
        
        best_match = None
        best_score = 0.0
        best_method = "none"
        
        for lens in self.lens_references:
            score = 0.0
            matches = 0
            
            # Brand match
            brand = lens.get('Brand', '').lower()
            if brand and brand in full_text:
                score += 0.25
                matches += 1
            
            # Lens model match
            lens_name = lens.get('Lens', '').lower()
            if lens_name:
                if lens_name in full_text:
                    score += 0.5
                    matches += 1
                    best_method = "exact_name"
                else:
                    # Partial word matching
                    lens_words = [w for w in lens_name.split() if len(w) > 2]
                    matched_words = sum(1 for word in lens_words if word in full_text)
                    if matched_words >= 2:
                        score += 0.3
                        matches += 1
                        best_method = "partial_name"
            
            # Focal length match
            focal = lens.get('FL (mm)', '')
            if focal:
                focal_patterns = [
                    f"{focal}mm",
                    f"{focal} mm",
                    f"{focal}f",
                    f"{focal} f"
                ]
                if any(p in full_text for p in focal_patterns):
                    score += 0.25
                    matches += 1
            
            if score > best_score:
                best_score = score
                best_match = lens
        
        if best_match and best_score >= 0.5:
            lens_id = f"{best_match.get('Brand', '')}_{best_match.get('Lens', '')}".replace(' ', '_').replace('/', '_')
            return lens_id, min(best_score, 1.0), best_method
        
        return "", 0.0, "none"
    
    def scrape_listing(self, listing_id: str, url: str) -> Optional[LensListing]:
        """Scrape a single listing."""
        html = self._fetch(url)
        if not html:
            self.stats['failed'] += 1
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title_tag = soup.find('h1')
        title = title_tag.get_text(strip=True) if title_tag else ""
        
        if not title:
            # Try other selectors
            title_match = re.search(r'<title>([^<]+)</title>', html)
            if title_match:
                title = title_match.group(1).strip()
        
        # Extract description
        description = self._extract_description(html)
        
        # Check filters
        should_filter, filter_reason = self._should_filter(title, description)
        if should_filter:
            logger.info(f"Filtered [{listing_id}]: {filter_reason} - {title[:60]}")
            self.stats['filtered'] += 1
            return None
        
        # Extract price
        price_eur, price_raw, currency = self._extract_price(html)
        if price_eur == 0:
            # Try to find price in the title or text
            price_eur, price_raw, currency = self._extract_price(title)
        
        price_usd = price_eur / self.USD_TO_EUR if price_eur > 0 else 0
        
        # Extract location
        location = self._extract_location(html)
        
        # Extract date
        posted_date = self._extract_date(html)
        
        # Match to lens reference
        matched_id, confidence, method = self._match_lens(title, description)
        if matched_id:
            self.stats['matched'] += 1
        
        self.stats['processed'] += 1
        
        return LensListing(
            listing_id=listing_id,
            title=title,
            price_raw=price_raw,
            price_eur=round(price_eur, 2),
            price_usd=round(price_usd, 2),
            currency=currency or 'EUR',
            location=location,
            url=url,
            posted_date=posted_date,
            description=description[:500],  # Limit description length
            matched_lens_id=matched_id,
            confidence_score=confidence,
            match_method=method
        )
    
    def parse_listings_page(self, html: str) -> List[Tuple[str, str]]:
        """Parse listing IDs and URLs from category page."""
        listings = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all listing links
        for link in soup.find_all('a', href=re.compile(r'/msg/lv/electronics/photo-optics/objectives/[a-z0-9]+\.html')):
            href = link.get('href', '')
            if href:
                # Extract listing ID from URL
                match = re.search(r'/([a-z0-9]+)\.html$', href)
                if match:
                    listing_id = match.group(1)
                    full_url = href if href.startswith('http') else f"{self.BASE_URL}{href}"
                    listings.append((listing_id, full_url))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_listings = []
        for listing_id, url in listings:
            if listing_id not in seen:
                seen.add(listing_id)
                unique_listings.append((listing_id, url))
        
        return unique_listings
    
    def get_next_page(self, html: str) -> Optional[str]:
        """Find next page URL."""
        # Look for "Nākošie" (Next) link
        next_match = re.search(
            r'<a[^>]*href="([^"]*(?:page\d+\.html|page=\d+)[^"]*)"[^>]*>\s*Nākošie\s*</a>',
            html,
            re.IGNORECASE
        )
        if next_match:
            next_url = next_match.group(1)
            if next_url.startswith('http'):
                return next_url
            return f"{self.BASE_URL}{next_url}"
        
        return None
    
    def scrape_category(self, max_pages: int = 0, limit: int = 0) -> List[LensListing]:
        """Scrape all lens listings from category."""
        logger.info(f"Starting lens scraper (max_pages={max_pages}, limit={limit})")
        
        # Load lens references
        self._load_lens_references()
        
        listings = []
        current_url = f"{self.BASE_URL}{self.CATEGORY_URL}"
        page_count = 0
        
        while current_url:
            if max_pages > 0 and page_count >= max_pages:
                logger.info(f"Reached max pages: {max_pages}")
                break
            
            logger.info(f"Fetching page {page_count + 1}: {current_url}")
            html = self._fetch(current_url)
            
            if not html:
                logger.error(f"Failed to fetch page: {current_url}")
                break
            
            page_listings = self.parse_listings_page(html)
            logger.info(f"Found {len(page_listings)} listings on page {page_count + 1}")
            
            for listing_id, url in page_listings:
                if limit > 0 and len(listings) >= limit:
                    logger.info(f"Reached limit: {limit}")
                    return listings
                
                listing = self.scrape_listing(listing_id, url)
                if listing:
                    listings.append(listing)
                    logger.info(f"Scraped [{listing_id}]: {listing.title[:60]}... (€{listing.price_eur})")
            
            # Get next page
            current_url = self.get_next_page(html)
            page_count += 1
            
            if not current_url:
                logger.info("No more pages")
                break
        
        logger.info(f"Scraping complete: {len(listings)} listings from {page_count} pages")
        logger.info(f"Stats: {self.stats}")
        
        return listings
    
    def export_to_csv(self, listings: List[LensListing], filepath: str):
        """Export listings to CSV."""
        if not listings:
            logger.warning("No listings to export")
            return
        
        fieldnames = [
            'listing_id', 'title', 'price_raw', 'price_eur', 'price_usd',
            'currency', 'location', 'url', 'posted_date', 'description',
            'seller_name', 'phone', 'matched_lens_id', 'confidence_score', 'match_method'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for listing in listings:
                writer.writerow(asdict(listing))
        
        logger.info(f"Exported {len(listings)} listings to {filepath}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='SS.COM Lens Scraper')
    parser.add_argument('--max-pages', type=int, default=0, help='Max pages to scrape (0 = unlimited)')
    parser.add_argument('--limit', type=int, default=0, help='Max listings to scrape (0 = unlimited)')
    parser.add_argument('--output', type=str, default='lens_listings.csv', help='Output CSV file')
    parser.add_argument('--ref-csv', type=str, default='lenses.csv', help='Lens reference CSV')
    
    args = parser.parse_args()
    
    scraper = LensScraper()
    
    # Load references if provided
    if args.ref_csv:
        scraper._load_lens_references(args.ref_csv)
    
    # Scrape
    listings = scraper.scrape_category(max_pages=args.max_pages, limit=args.limit)
    
    # Export
    scraper.export_to_csv(listings, args.output)
    
    print(f"\n{'='*60}")
    print(f"SCRAPING COMPLETE")
    print(f"{'='*60}")
    print(f"Total listings scraped: {len(listings)}")
    print(f"Filtered out: {scraper.stats['filtered']}")
    print(f"Matched to lens DB: {scraper.stats['matched']}")
    print(f"Failed: {scraper.stats['failed']}")
    print(f"Output file: {args.output}")


if __name__ == "__main__":
    main()
