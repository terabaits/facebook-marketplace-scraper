"""Andele Mandele computer scraper - saves to computer_listings table."""
import time
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import text

from src.parsers.andele_parser import AndeleParser, AndeleListingData
from src.scraper.andele_scraper import AndeleScraper
from src.database.connection import get_session
from src.utils.logger import get_logger
from src.utils.image_downloader import ImageDownloader

logger = get_logger("andele_computer_scraper")


class AndeleComputerScraper(AndeleScraper):
    """Extended Andele scraper that saves computers to computer_listings table."""
    
    def scrape_computers(self, max_pages: int = 0, limit: int = 0):
        """Scrape computer category and save to computer_listings table.
        
        Args:
            max_pages: Max pages to scrape (0 = unlimited)
            limit: Max listings total (0 = unlimited)
        """
        category = 'computer'
        if category not in self.CATEGORY_URLS:
            logger.error(f"Computer category not in URL mapping")
            return self.result
            
        url = self.CATEGORY_URLS[category]
        logger.info(f"Starting COMPUTER scrape from {url}")
        
        pages_scraped = 0
        total_listings = 0
        
        while url:
            if max_pages > 0 and pages_scraped >= max_pages:
                logger.info(f"Reached max pages ({max_pages})")
                break
                
            logger.info(f"Scraping page {pages_scraped + 1}: {url}")
            
            # Use browser for JavaScript-loaded listings
            html = self._fetch_page_with_browser(url)
            if not html:
                self.result.errors.append(f"Failed to fetch {url}")
                break
                
            # Parse category page
            listing_urls, next_url = self.parser.parse_category_page(html, url)
            logger.info(f"Found {len(listing_urls)} computer listings on this page")
            
            # Process each listing
            for listing_url in listing_urls:
                if limit > 0 and total_listings >= limit:
                    logger.info(f"Reached limit ({limit})")
                    return self.result
                    
                self._process_computer_listing(listing_url)
                total_listings += 1
                
            pages_scraped += 1
            url = next_url
            
        logger.info(f"Completed computers: {self.result.to_dict()}")
        return self.result
    
    def _process_computer_listing(self, url: str):
        """Process a computer listing and save to computer_listings table."""
        self.result.total += 1
        
        try:
            data = self.scrape_listing(url, 'computer')
            if not data:
                self.result.failed += 1
                return
                
            if self.dry_run:
                logger.info(f"[DRY RUN] Would save computer: {data.title[:50]}...")
                return
            
            # Save to computer_listings table
            self._save_computer_listing(data, url)
                
        except Exception as e:
            logger.error(f"Error processing computer {url}: {e}")
            import traceback
            traceback.print_exc()
            self.result.failed += 1
            self.result.errors.append(f"Error processing {url}: {e}")
    
    def _save_computer_listing(self, data: AndeleListingData, url: str):
        """Save computer listing to computer_listings table with component matches."""
        from src.models.computer_schemas import ComputerListing
        
        # Get match result
        match_result = getattr(data, '_computer_match_result', None)
        
        # Create computer listing
        computer = ComputerListing(
            listing_id=data.listing_id or f"andele_comp_{int(time.time())}",
            title=data.title,
            description=data.description,
            price_eur=data.price_eur or 0.0,
            seller_location=data.seller_location or 'X',
            listing_url=data.listing_url,
            image_url=data.image_urls[0] if data.image_urls else None,
            date_posted=data.date_posted or datetime.now(),
            matched_cpu_id=getattr(data, '_matched_cpu_id', None),
            matched_gpu_id=getattr(data, '_matched_gpu_id', None),
            matched_ram_id=getattr(data, '_matched_ram_id', None),
            matched_ssd_id=getattr(data, '_matched_ssd_id', None),
            matched_psu_id=getattr(data, '_matched_psu_id', None),
            matched_case_id=getattr(data, '_matched_case_id', None),
            matched_motherboard_id=getattr(data, '_matched_motherboard_id', None),
            matched_monitor_id=getattr(data, '_monitor_model_id', None),
        )
        
        # Extract confidence scores from match result
        cpu_conf = gpu_conf = ram_conf = ssd_conf = psu_conf = case_conf = None
        cpu_method = gpu_method = ram_method = ssd_method = psu_method = case_method = None
        
        if match_result:
            cpu_conf = getattr(match_result, 'cpu_confidence', None)
            gpu_conf = getattr(match_result, 'gpu_confidence', None)
            ram_conf = getattr(match_result, 'ram_confidence', None)
            ssd_conf = getattr(match_result, 'ssd_confidence', None)
            psu_conf = getattr(match_result, 'psu_confidence', None)
            case_conf = getattr(match_result, 'case_confidence', None)
            cpu_method = getattr(match_result, 'cpu_match_method', None)
            gpu_method = getattr(match_result, 'gpu_match_method', None)
            ram_method = getattr(match_result, 'ram_match_method', None)
            ssd_method = getattr(match_result, 'ssd_match_method', None)
            psu_method = getattr(match_result, 'psu_match_method', None)
            case_method = getattr(match_result, 'case_match_method', None)
        
        # Save to database
        with get_session() as session:
            # Check if listing exists
            existing = session.execute(
                text("""SELECT listing_id FROM computer_listings 
                       WHERE listing_id = :id ORDER BY version_number DESC LIMIT 1"""),
                {"id": computer.listing_id}
            ).fetchone()
            
            action = 'new'
            if existing:
                action = 'updated'
            
            # Insert/Update the computer listing
            session.execute(
                text("""
                INSERT INTO computer_listings (
                    listing_id, version_number, title, description, price_eur,
                    seller_location, listing_url, image_url, date_posted,
                    matched_cpu_id, matched_gpu_id, matched_ram_id, matched_ssd_id,
                    matched_ssd2_id, matched_ssd3_id, matched_psu_id, matched_case_id,
                    matched_motherboard_id, matched_monitor_id,
                    fallback_psu_wattage, fallback_case_price,
                    fallback_motherboard_price, fallback_monitor_price,
                    cpu_confidence, gpu_confidence, ram_confidence, ssd_confidence,
                    ssd2_confidence, ssd3_confidence, psu_confidence, case_confidence,
                    motherboard_confidence, monitor_confidence,
                    cpu_match_method, gpu_match_method, ram_match_method, ssd_match_method,
                    ssd2_match_method, ssd3_match_method, psu_match_method, case_match_method,
                    motherboard_match_method, monitor_match_method,
                    first_seen_at, last_seen_at, is_active
                ) VALUES (
                    :listing_id, 1, :title, :description, :price_eur,
                    :seller_location, :listing_url, :image_url, :date_posted,
                    :matched_cpu_id, :matched_gpu_id, :matched_ram_id, :matched_ssd_id,
                    NULL, NULL, :matched_psu_id, :matched_case_id,
                    :matched_motherboard_id, :matched_monitor_id,
                    NULL, 15.0, NULL, 100.0,
                    :cpu_confidence, :gpu_confidence, :ram_confidence, :ssd_confidence,
                    NULL, NULL, :psu_confidence, :case_confidence,
                    NULL, NULL,
                    :cpu_match_method, :gpu_match_method, :ram_match_method, :ssd_match_method,
                    NULL, NULL, :psu_match_method, :case_match_method,
                    NULL, NULL,
                    NOW(), NOW(), true
                )
                ON CONFLICT (listing_id, version_number) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    price_eur = EXCLUDED.price_eur,
                    seller_location = EXCLUDED.seller_location,
                    last_seen_at = NOW(),
                    is_active = true,
                    cpu_confidence = EXCLUDED.cpu_confidence,
                    gpu_confidence = EXCLUDED.gpu_confidence,
                    ram_confidence = EXCLUDED.ram_confidence,
                    ssd_confidence = EXCLUDED.ssd_confidence,
                    psu_confidence = EXCLUDED.psu_confidence,
                    case_confidence = EXCLUDED.case_confidence
                """),
                {
                    "listing_id": computer.listing_id,
                    "title": computer.title,
                    "description": computer.description,
                    "price_eur": computer.price_eur,
                    "seller_location": computer.seller_location,
                    "listing_url": computer.listing_url,
                    "image_url": computer.image_url,
                    "date_posted": computer.date_posted,
                    "matched_cpu_id": computer.matched_cpu_id,
                    "matched_gpu_id": computer.matched_gpu_id,
                    "matched_ram_id": computer.matched_ram_id,
                    "matched_ssd_id": computer.matched_ssd_id,
                    "matched_psu_id": computer.matched_psu_id,
                    "matched_case_id": computer.matched_case_id,
                    "matched_motherboard_id": computer.matched_motherboard_id,
                    "matched_monitor_id": computer.matched_monitor_id,
                    "cpu_confidence": cpu_conf,
                    "gpu_confidence": gpu_conf,
                    "ram_confidence": ram_conf,
                    "ssd_confidence": ssd_conf,
                    "psu_confidence": psu_conf,
                    "case_confidence": case_conf,
                    "cpu_match_method": cpu_method,
                    "gpu_match_method": gpu_method,
                    "ram_match_method": ram_method,
                    "ssd_match_method": ssd_method,
                    "psu_match_method": psu_method,
                    "case_match_method": case_method,
                }
            )
            session.commit()
            
            logger.info(f"💻 Computer saved ({action}): {computer.listing_id}")
            if match_result:
                logger.info(f"   Components: CPU={computer.matched_cpu_id}, GPU={computer.matched_gpu_id}, "
                          f"RAM={computer.matched_ram_id}, SSD={computer.matched_ssd_id}")
            
            if action == 'new':
                self.result.new += 1
            else:
                self.result.updated += 1
        
        # Download images
        if data.image_urls:
            downloader = ImageDownloader("images/computers")
            local_paths = downloader.download_images(data.image_urls, computer.listing_id)
            if local_paths:
                with get_session() as session:
                    session.execute(
                        text("""UPDATE computer_listings SET local_image_path = :path 
                                WHERE listing_id = :id"""),
                        {"path": local_paths[0], "id": computer.listing_id}
                    )
                    session.commit()
                logger.info(f"📸 Downloaded {len(local_paths)} computer images")
