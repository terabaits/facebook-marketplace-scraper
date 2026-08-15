"""Computer scraper for ss.com - scrapes full PC listings."""
import sys
import io
from datetime import datetime
from typing import Iterator, Tuple, Optional, Dict, List
from pathlib import Path

from sqlalchemy import text

from src.database.connection import init_database, get_session
from src.database.repository import (
    CPUReferenceRepository, GPUReferenceRepository, RAMReferenceRepository,
    SSDReferenceRepository, PSURepository, CaseRepository, ScrapeRunRepository,
    MotherboardRepository, MonitorRepository
)
from src.models.computer_schemas import ComputerListing, ComputerMatchResult
from src.scraper.crawler import Crawler, ErrorType
from src.scraper.computer_parser import ComputerListingParser
from src.scraper.computer_matcher import ComputerMatcher
from src.utils.config import AppConfig
from src.utils.logger import get_logger
from src.utils.text import compute_content_hash
from src.utils.listing_versioning import (
    ListingVersionManager, compute_content_fingerprint, get_versioned_listing_id
)
from src.utils.image_downloader import ImageDownloader
from src.utils.price_estimator import PriceEstimator

# Force UTF-8 for Windows console
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logger = get_logger("computer_scraper")


class ComputerScraper:

    def _classify_build_type(self, title, description):
        """Classify listing as prebuilt or custom based on title/description."""
        import re
        text = (title or "") + " " + (description or "")
        text_lower = text.lower()

        # Buying ads are not prebuilt PCs for sale
        if re.search(r'pērk|покупаю|kuplyu|perku|buying', text_lower):
            return 'custom'

        # Component-only / part-out markers — must be specific enough that a full PC listing
        # saying "only the GPU/HDD is used" is not caught.
        component_only_markers = [
            'viena detaļa', 'viena dala', ' одна деталь',
            'cpu only', 'gpu only', 'ram only', 'ssd only', 'hdd only', 'motherboard only',
            'procesors tikai', 'videokarte tikai', 'ram tikai', 'ssd tikai', 'hdd tikai',
            'pārdodu atsevišķi', 'pārdodu atseviski', 'продаю отдельно',
            'pārdod atsevišķi', 'pārdod atseviski',
            'rezerves daļām', 'rezerves dalam', 'на запчасти', 'for parts'
        ]
        if any(marker in text_lower for marker in component_only_markers):
            return 'custom'

        prebuilt_keywords = [
            'gatavs dators', 'gatavs pc', 'gatava stacija', 'gatavs komplekts',
            'ready pc', 'prebuilt', 'complete pc', 'gaming pc', 'gaming computer',
            'darba stacija', 'ofisa dators', 'mājas dators', 'spēļu dators',
            'gatavs', 'izgatavots', 'komplekts', 'sistēmas bloks', 'sistemas bloks',
            'sistēma', 'system unit', 'desktop pc', 'tower pc',
            'dators komplekts', 'datoru komplekts', 'pc komplekts', 'gaming datoru', 'gaming dators',
            # Russian
            'готовый пк', 'готовый компьютер', 'игровой пк', 'игровой компьютер',
            'системный блок', 'комплект', 'готовый', 'рабочая станция',
            'офисный компьютер', 'домашний компьютер', 'продаю компьютер', 'продается компьютер'
        ]
        component_keywords = [
            'procesors', 'cpu', 'matere', 'motherboard', 'videokarte', 'gpu',
            'operatīvā', 'ram', 'ssd', 'hdd', 'barošanas bloks', 'psu',
            'korpuss', 'case', 'dzesētājs', 'cooler',
            # Russian
            'процессор', 'материнская', 'видеокарта', 'оперативная', 'блок питания', 'корпус'
        ]

        # Strong intent signals — these override component counting because the seller explicitly
        # frames the listing as a complete, ready-to-use PC.
        strong_prebuilt_markers = [
            'gatavs dators', 'gatavs pc', 'gatava stacija', 'gatavs komplekts',
            'pilnībā gatavs', 'pilniba gatavs', 'pilnīgi gatavs', 'pilnigi gatavs',
            'izgatavots dators', 'izgatavots pc',
            'ready pc', 'prebuilt', 'complete pc', 'gaming pc', 'gaming computer',
            'darba stacija', 'ofisa dators', 'mājas dators', 'majas dators', 'spēļu dators', 'speļu dators',
            'sistēmas bloks', 'sistemas bloks', 'sistēma', 'system unit',
            'desktop pc', 'tower pc', 'pc tower', 'full pc',
            # Russian
            'готовый пк', 'готовый компьютер', 'игровой пк', 'игровой компьютер',
            'системный блок', 'рабочая станция', 'офисный компьютер', 'домашний компьютер'
        ]
        if any(marker in text_lower for marker in strong_prebuilt_markers):
            return 'prebuilt'

        # Count distinct core components. A listing that mentions most of a complete PC
        # is almost always a full system, even if the title is generic.
        cpu = bool(re.search(r'(procesors?|cpu|процессор|core\s+i|ryzen|xeon|athlon|pentium)', text_lower))
        gpu = bool(re.search(r'(videokarte?|gpu|video|видеокарта|rx\s*\d|gtx\s*\d|rtx\s*\d|quadro)', text_lower))
        ram = bool(re.search(r'(operatīv|operativa|ram|ddr\d?|оператив)', text_lower))
        storage = bool(re.search(r'(ssd|hdd|m\.\s*2|накопитель)', text_lower))
        motherboard = bool(re.search(r'(pamat plate|motherboard|mobo|материнская|matere)', text_lower))
        psu = bool(re.search(r'(barošanas|barosanas|psu|power\s*supply|блок\s*питания|watt)', text_lower))
        case = bool(re.search(r'(korpuss?|case\b|tower|корпус)', text_lower))

        core_components = sum([cpu, gpu, ram, storage, motherboard, psu, case])
        # Require a near-complete system (5+ components) before assuming prebuilt.
        if core_components >= 5:
            return 'prebuilt'
        # 3-4 components is ambiguous — only mark prebuilt if a strong marker exists.
        if core_components >= 3:
            weak_prebuilt_markers = [
                'gatav', 'komplekt', 'izgatavots', 'system unit', 'sistēmas bloks', 'sistemas bloks',
                # Russian
                'комплект', 'системный блок'
            ]
            if any(marker in text_lower for marker in weak_prebuilt_markers):
                return 'prebuilt'

        # Very few components described and no prebuilt cues -> treat as custom/part-out.
        return 'custom'

    """Scraper for full computer listings on ss.com."""
    
    COMPUTER_CATEGORY_PATH = "/lv/electronics/computers/pc/"
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.crawler = Crawler(config.scraper)
        self.matcher: Optional[ComputerMatcher] = None
        self.image_downloader: Optional[ImageDownloader] = None
        self.price_estimator: Optional[PriceEstimator] = None
        
        self.stats = {
            'total': 0,
            'new': 0,
            'new_version': 0,
            'updated': 0,
            'unchanged': 0,
            'failed': 0,
            'skipped': 0,
            'matched': 0,
            'images_downloaded': 0,
        }
    
    def initialize(self):
        """Initialize database and load reference data."""
        logger.info("Initializing computer scraper...")
        
        init_database(self.config.database)
        logger.info(f"Database: {self.config.database.connection_string}")
        
        # Load all component references
        with get_session() as session:
            cpus = CPUReferenceRepository.get_all(session)
            gpus = GPUReferenceRepository.get_all(session)
            rams = RAMReferenceRepository.get_all(session)
            ssds = SSDReferenceRepository.get_all(session)
            psus = PSURepository.get_all(session)
            cases = CaseRepository.get_all(session)
            motherboards = MotherboardRepository.get_all(session)
            monitors = MonitorRepository.get_all(session)
        
        self.matcher = ComputerMatcher(cpus, gpus, rams, ssds, psus, cases, motherboards, monitors)
        
        # Initialize image downloader
        self.image_downloader = ImageDownloader(base_dir="images/computers")
        self.price_estimator = PriceEstimator()
        
        logger.info(f"Loaded references: {len(cpus)} CPUs, {len(gpus)} GPUs, "
                   f"{len(rams)} RAMs, {len(ssds)} SSDs, {len(psus)} PSUs, {len(cases)} Cases, "
                   f"{len(motherboards)} Motherboards, {len(monitors)} Monitors")
        
        if self.config.scraper.save_html_samples:
            Path(self.config.scraper.html_samples_dir).mkdir(parents=True, exist_ok=True)
    
    def _save_computer_listing(self, session, listing: ComputerListing, action: str) -> Tuple[str, str]:
        """Save or update computer listing in database with versioning support."""
        # Compute content fingerprint for versioning
        fingerprint = compute_content_fingerprint(
            listing.title, listing.description, listing.price_eur, listing.seller_location
        )
        listing.content_hash = fingerprint
        
        # Check versioning using the version manager
        version_mgr = ListingVersionManager(session)
        effective_id, version, action_type, _ = version_mgr.check_and_prepare(
            listing.listing_id, listing.title, listing.description,
            listing.price_eur, listing.seller_location, "computer_listings"
        )
        
        # Update listing with effective ID and version
        original_id = listing.listing_id
        listing.listing_id = effective_id
        listing.version_number = version
        
        # Check if this exact version exists
        existing = session.execute(
            text("SELECT * FROM computer_listings WHERE listing_id = :id AND version_number = :version"),
            {"id": effective_id, "version": version}
        ).fetchone()
        
        if existing:
            # Check for changes
            old = session.execute(
                text("""SELECT title, description, price_eur, matched_cpu_id, matched_gpu_id
                   FROM computer_listings WHERE listing_id = :id AND version_number = :version"""),
                {"id": effective_id, "version": version}
            ).fetchone()
            
            has_changes = (
                old[0] != listing.title or
                old[1] != (listing.description or "") or
                old[2] != listing.price_eur or
                old[3] != listing.matched_cpu_id or
                old[4] != listing.matched_gpu_id
            )
            
            if has_changes:
                # Save version history BEFORE updating
                version_mgr.save_version_history(original_id, version, "computer_listings")
                
                # Update listing
                session.execute(
                    text("""UPDATE computer_listings SET
                        title = :title,
                        description = :description,
                        price_eur = :price,
                        seller_location = :location,
                        image_url = :image_url,
                        last_seen_at = NOW(),
                        is_active = true,
                        matched_cpu_id = :cpu_id,
                        matched_gpu_id = :gpu_id,
                        matched_ram_id = :ram_id,
                        matched_ssd_id = :ssd_id,
                        matched_ssd2_id = :ssd2_id,
                        matched_ssd3_id = :ssd3_id,
                        matched_psu_id = :psu_id,
                        matched_case_id = :case_id,
                        matched_motherboard_id = :mb_id,
                        matched_monitor_id = :monitor_id,
                        cpu_confidence = :cpu_conf,
                        gpu_confidence = :gpu_conf,
                        ram_confidence = :ram_conf,
                        ssd_confidence = :ssd_conf,
                        ssd2_confidence = :ssd2_conf,
                        ssd3_confidence = :ssd3_conf,
                        psu_confidence = :psu_conf,
                        case_confidence = :case_conf,
                        motherboard_confidence = :mb_conf,
                        monitor_confidence = :monitor_conf,
                        cpu_match_method = :cpu_method,
                        gpu_match_method = :gpu_method,
                        ram_match_method = :ram_method,
                        ssd_match_method = :ssd_method,
                        ssd2_match_method = :ssd2_method,
                        ssd3_match_method = :ssd3_method,
                        psu_match_method = :psu_method,
                        case_match_method = :case_method,
                        motherboard_match_method = :mb_method,
                        monitor_match_method = :monitor_method,
                        fallback_psu_wattage = :psu_wattage,
                        fallback_case_price = :case_price,
                        fallback_motherboard_price = :mb_price,
                        monitor_included = :monitor_included,
                        components_total_eur = :components_total,
                        price_difference_eur = :price_diff,
                        build_type = :build_type,
                        is_prebuilt = :is_prebuilt
                    WHERE listing_id = :id AND version_number = :version"""),
                    {
                        "id": effective_id,
                        "version": version,
                        "title": listing.title,
                        "description": listing.description,
                        "price": listing.price_eur,
                        "location": listing.seller_location,
                        "image_url": listing.image_url,
                        "cpu_id": listing.matched_cpu_id,
                        "gpu_id": listing.matched_gpu_id,
                        "ram_id": listing.matched_ram_id,
                        "ssd_id": listing.matched_ssd_id,
                        "ssd2_id": listing.matched_ssd2_id,
                        "ssd3_id": listing.matched_ssd3_id,
                        "psu_id": listing.matched_psu_id,
                        "case_id": listing.matched_case_id,
                        "mb_id": listing.matched_motherboard_id,
                        "monitor_id": listing.matched_monitor_id,
                        "cpu_conf": listing.cpu_confidence,
                        "gpu_conf": listing.gpu_confidence,
                        "ram_conf": listing.ram_confidence,
                        "ssd_conf": listing.ssd_confidence,
                        "ssd2_conf": listing.ssd2_confidence,
                        "ssd3_conf": listing.ssd3_confidence,
                        "psu_conf": listing.psu_confidence,
                        "case_conf": listing.case_confidence,
                        "mb_conf": listing.motherboard_confidence,
                        "monitor_conf": listing.monitor_confidence,
                        "cpu_method": (listing.cpu_match_method or "")[:50],
                        "gpu_method": (listing.gpu_match_method or "")[:50],
                        "ram_method": (listing.ram_match_method or "")[:50],
                        "ssd_method": (listing.ssd_match_method or "")[:50],
                        "ssd2_method": (listing.ssd2_match_method or "")[:50],
                        "ssd3_method": (listing.ssd3_match_method or "")[:50],
                        "psu_method": (listing.psu_match_method or "")[:50],
                        "case_method": (listing.case_match_method or "")[:50],
                        "mb_method": (listing.motherboard_match_method or "")[:50],
                        "monitor_method": (listing.monitor_match_method or "")[:50],
                        "psu_wattage": listing.fallback_psu_wattage,
                        "case_price": listing.fallback_case_price,
                        "mb_price": listing.fallback_motherboard_price,
                        "monitor_included": listing.monitor_included,
                        "components_total": listing.components_total_eur,
                        "price_diff": listing.price_difference_eur,
                        "build_type": listing.build_type,
                        "is_prebuilt": listing.is_prebuilt,
                    }
                )
                return "updated", f"Updated: {listing.title[:50]}..."
            else:
                # Just update last_seen
                session.execute(
                    text("UPDATE computer_listings SET last_seen_at = NOW(), is_active = true WHERE listing_id = :id AND version_number = :version"),
                    {"id": effective_id, "version": version}
                )
                return "unchanged", f"Unchanged: {listing.title[:50]}..."
        else:
            # Insert new listing (could be v1 or v2, v3, etc.)
            is_new_version = version > 1
            
            session.execute(
                text("""INSERT INTO computer_listings (
                    listing_id, version_number, title, description, price_eur, seller_location,
                    listing_url, image_url, date_posted, content_hash,
                    matched_cpu_id, matched_gpu_id, matched_ram_id,
                    matched_ssd_id, matched_ssd2_id, matched_ssd3_id, matched_psu_id, matched_case_id, matched_motherboard_id, matched_monitor_id,
                    cpu_confidence, gpu_confidence, ram_confidence,
                    ssd_confidence, ssd2_confidence, ssd3_confidence, psu_confidence, case_confidence, motherboard_confidence, monitor_confidence,
                    cpu_match_method, gpu_match_method, ram_match_method,
                    ssd_match_method, ssd2_match_method, ssd3_match_method, psu_match_method, case_match_method, motherboard_match_method, monitor_match_method,
                    fallback_psu_wattage, fallback_case_price, fallback_motherboard_price, monitor_included,
                    components_total_eur, price_difference_eur,
                    build_type, is_prebuilt
                ) VALUES (
                    :id, :version, :title, :description, :price, :location, :url, :image_url,
                    :date_posted, :content_hash,
                    :cpu_id, :gpu_id, :ram_id, :ssd_id, :ssd2_id, :ssd3_id, :psu_id, :case_id, :mb_id, :monitor_id,
                    :cpu_conf, :gpu_conf, :ram_conf, :ssd_conf, :ssd2_conf, :ssd3_conf, :psu_conf, :case_conf, :mb_conf, :monitor_conf,
                    :cpu_method, :gpu_method, :ram_method, :ssd_method, :ssd2_method, :ssd3_method, :psu_method, :case_method, :mb_method, :monitor_method,
                    :psu_wattage, :case_price, :mb_price, :monitor_included, :components_total, :price_diff,
                    :build_type, :is_prebuilt
                )"""),
                {
                    "id": effective_id,
                    "version": version,
                    "title": listing.title,
                    "description": listing.description,
                    "price": listing.price_eur,
                    "location": listing.seller_location,
                    "url": listing.listing_url,
                    "image_url": listing.image_url,
                    "date_posted": listing.date_posted,
                    "content_hash": listing.content_hash,
                    "cpu_id": listing.matched_cpu_id,
                    "gpu_id": listing.matched_gpu_id,
                    "ram_id": listing.matched_ram_id,
                    "ssd_id": listing.matched_ssd_id,
                    "ssd2_id": listing.matched_ssd2_id,
                    "ssd3_id": listing.matched_ssd3_id,
                    "psu_id": listing.matched_psu_id,
                    "case_id": listing.matched_case_id,
                    "mb_id": listing.matched_motherboard_id,
                    "monitor_id": listing.matched_monitor_id,
                    "cpu_conf": listing.cpu_confidence,
                    "gpu_conf": listing.gpu_confidence,
                    "ram_conf": listing.ram_confidence,
                    "ssd_conf": listing.ssd_confidence,
                    "ssd2_conf": listing.ssd2_confidence,
                    "ssd3_conf": listing.ssd3_confidence,
                    "psu_conf": listing.psu_confidence,
                    "case_conf": listing.case_confidence,
                    "mb_conf": listing.motherboard_confidence,
                    "monitor_conf": listing.monitor_confidence,
                    "cpu_method": (listing.cpu_match_method or "")[:50],
                    "gpu_method": (listing.gpu_match_method or "")[:50],
                    "ram_method": (listing.ram_match_method or "")[:50],
                    "ssd_method": (listing.ssd_match_method or "")[:50],
                    "ssd2_method": (listing.ssd2_match_method or "")[:50],
                    "ssd3_method": (listing.ssd3_match_method or "")[:50],
                    "psu_method": (listing.psu_match_method or "")[:50],
                    "case_method": (listing.case_match_method or "")[:50],
                    "mb_method": (listing.motherboard_match_method or "")[:50],
                    "monitor_method": (listing.monitor_match_method or "")[:50],
                    "psu_wattage": listing.fallback_psu_wattage,
                    "case_price": listing.fallback_case_price,
                    "mb_price": listing.fallback_motherboard_price,
                    "monitor_included": listing.monitor_included,
                    "components_total": listing.components_total_eur,
                    "price_diff": listing.price_difference_eur,
                    "build_type": listing.build_type,
                    "is_prebuilt": listing.is_prebuilt,
                }
            )
            
            if is_new_version:
                return "new_version", f"New version ({version}): {listing.title[:50]}..."
            return "new", f"New: {listing.title[:50]}..."
    
    def _process_listing(self, html: str, url: str) -> Tuple[Optional[ComputerListing], str, str]:
        """Parse and process a single computer listing."""
        parser = ComputerListingParser(html, url)
        base_listing = parser.parse()
        
        if not base_listing:
            return None, "skipped", "Filtered by skip patterns"
        
        # Match components
        full_text = f"{base_listing.title} {base_listing.description or ''}"
        match_result = self.matcher.match(
            base_listing.title,
            base_listing.description or "",
            base_listing.price_eur
        )
        
        # Calculate component totals
        components_total = 0.0
        
        # Get component prices (from reference data averages or fallbacks)
        cpu_price = 0.0
        gpu_price = 0.0
        ram_price = 0.0
        ssd_price = 0.0
        psu_price = 0.0
        case_price = 0.0
        mb_price = 0.0
        
        # Store generic component data for display
        generic_components = {}
        
        if match_result.cpu:
            cpu_price = self.price_estimator.get_cpu_price(match_result.cpu.get('id'))
            if cpu_price is None:
                cpu_price = 150.0
        
        if match_result.gpu:
            gpu_price = self.price_estimator.get_gpu_price(match_result.gpu.get('id'))
            if gpu_price is None:
                gpu_price = self.price_estimator.get_gpu_fallback_price(match_result.gpu.get('id')) or 200.0
        
        if match_result.ram:
            ram_id = match_result.ram.get('id') if isinstance(match_result.ram, dict) else None
            ram_price = self.price_estimator.get_ram_price(ram_id) if ram_id else None
            if ram_price is None:
                ram_price = self.price_estimator.get_generic_ram_price(
                    match_result.ram.get('capacity_gb') or self.matcher._extract_ram_capacity(full_text),
                    match_result.ram.get('type', 'DDR4')
                )
        
        if match_result.ssd:
            ssd_id = match_result.ssd.get('id') if isinstance(match_result.ssd, dict) else None
            if ssd_id is not None and ssd_id >= 0:
                ssd_price = self.price_estimator.get_ssd_price(ssd_id)
            else:
                ssd_price = None
            if ssd_price is None:
                ssd_price = self.price_estimator.get_generic_ssd_price(
                    match_result.ssd.get('capacity_gb') or self.matcher._extract_ssd_capacity(full_text)
                )
        
        if match_result.psu:
            psu_data = match_result.psu
            if isinstance(psu_data, dict):
                psu_price = psu_data.get('price') or 55.0
            else:
                psu_price = 55.0
        else:
            psu_price = 55.0
        
        if match_result.case:
            case_data = match_result.case
            if isinstance(case_data, dict):
                case_price = case_data.get('price') or 15.0
            else:
                case_price = 15.0
        else:
            case_price = 15.0
        
        # Motherboard price based on CPU socket
        mb_price = self.matcher.get_motherboard_price(match_result.cpu) or 75.0
        
        # Calculate component totals
        cpu_price = cpu_price or 0.0
        gpu_price = gpu_price or 0.0
        ram_price = ram_price or 0.0
        ssd_price = ssd_price or 0.0
        psu_price = psu_price or 0.0
        case_price = case_price or 0.0
        mb_price = mb_price or 75.0
        
        components_total = cpu_price + gpu_price + ram_price + ssd_price + psu_price + case_price + mb_price
        price_diff = base_listing.price_eur - components_total
        
        # Classify build type
        build_type = self._classify_build_type(base_listing.title, base_listing.description)
        is_prebuilt = build_type == 'prebuilt'

        # Get fallback values
        fallback_psu_wattage = 650 if match_result.gpu else 400
        
        # Create ComputerListing
        computer_listing = ComputerListing(
            build_type=build_type,
            is_prebuilt=is_prebuilt,
            listing_id=base_listing.listing_id,
            title=base_listing.title,
            description=base_listing.description,
            price_eur=base_listing.price_eur,
            seller_location=base_listing.seller_location,
            listing_url=base_listing.listing_url,
            image_url=base_listing.image_url,
            date_posted=base_listing.date_posted,
            content_hash=base_listing.content_hash,
            matched_cpu_id=match_result.cpu.get('id') if match_result.cpu else None,
            matched_gpu_id=match_result.gpu.get('id') if match_result.gpu else None,
            matched_ram_id=match_result.ram.get('id') if match_result.ram else None,
            matched_ssd_id=(match_result.ssd.id if match_result.ssd and hasattr(match_result.ssd, 'id') and match_result.ssd.id >= 0 else (match_result.ssd.get('id') if match_result.ssd and match_result.ssd.get('id', -1) >= 0 else None)),
            matched_ssd2_id=match_result.additional_ssds[0].get('id') if match_result.additional_ssds and len(match_result.additional_ssds) >= 1 else None,
            matched_ssd3_id=match_result.additional_ssds[1].get('id') if match_result.additional_ssds and len(match_result.additional_ssds) >= 2 else None,
            matched_psu_id=match_result.psu.get('id') if match_result.psu and isinstance(match_result.psu, dict) and 'id' in match_result.psu else None,
            matched_case_id=match_result.case.get('id') if match_result.case and isinstance(match_result.case, dict) and 'id' in match_result.case else None,
            matched_motherboard_id=match_result.motherboard.get('id') if match_result.motherboard and isinstance(match_result.motherboard, dict) and 'id' in match_result.motherboard else None,
            matched_monitor_id=match_result.monitor.get('id') if match_result.monitor and isinstance(match_result.monitor, dict) and 'id' in match_result.monitor else None,
            cpu_confidence=match_result.cpu_confidence,
            gpu_confidence=match_result.gpu_confidence,
            ram_confidence=match_result.ram_confidence,
            ssd_confidence=match_result.ssd_confidence,
            ssd2_confidence=0.5 if match_result.additional_ssds and len(match_result.additional_ssds) >= 1 else None,
            ssd3_confidence=0.5 if match_result.additional_ssds and len(match_result.additional_ssds) >= 2 else None,
            psu_confidence=match_result.psu_confidence,
            case_confidence=match_result.case_confidence,
            motherboard_confidence=match_result.motherboard_confidence,
            monitor_confidence=match_result.monitor_confidence,
            cpu_match_method=match_result.cpu_method,
            gpu_match_method=match_result.gpu_method,
            ram_match_method=match_result.ram_method,
            ssd_match_method=match_result.ssd_method,
            ssd2_match_method=(f"additional_ssd_{match_result.additional_ssds[0]['capacity_gb']}gb" if match_result.additional_ssds and len(match_result.additional_ssds) >= 1 and isinstance(match_result.additional_ssds[0], dict) else None),
            ssd3_match_method=(f"additional_ssd_{match_result.additional_ssds[1]['capacity_gb']}gb" if match_result.additional_ssds and len(match_result.additional_ssds) >= 2 and isinstance(match_result.additional_ssds[1], dict) else None),
            psu_match_method=match_result.psu_method,
            case_match_method=match_result.case_method,
            motherboard_match_method=match_result.motherboard_method,
            monitor_match_method=match_result.monitor_method,
            fallback_psu_wattage=fallback_psu_wattage,
            fallback_case_price=15.0,
            fallback_motherboard_price=mb_price,
            monitor_included=match_result.monitor_included,
            components_total_eur=components_total,
            price_difference_eur=price_diff,
        )
        
        # Save to database
        with get_session() as session:
            action, message = self._save_computer_listing(session, computer_listing, "new")
            if action in ["new", "updated"]:
                session.commit()
                
                # Download image if available
                if base_listing.image_url and self.image_downloader:
                    local_image_path = self.image_downloader.download_image(
                        base_listing.image_url, 
                        computer_listing.listing_id
                    )
                    if local_image_path:
                        self.stats['images_downloaded'] += 1
                        logger.info(f"Image saved locally: {local_image_path}")
        
        return computer_listing, action, message
    
    def _scrape_category_page(self, page_url: str) -> Iterator[Tuple[str, str, str]]:
        """Scrape listings from a category page."""
        logger.info(f"Fetching computer category: {page_url}")
        
        result = self.crawler.fetch(page_url, "Computer category page")
        
        if result.error_type != ErrorType.SUCCESS:
            logger.error(f"Failed to fetch category: {result.error_msg}")
            return
        
        parser = ComputerListingParser(result.html, page_url)
        links = parser.get_category_links()
        
        if self.config.scraper.test_mode and self.config.scraper.max_listings > 0:
            links = links[:self.config.scraper.max_listings]
            logger.info(f"Test mode: limiting to {len(links)} listings")
        
        logger.info(f"Found {len(links)} computer listings to process")
        
        for idx, link in enumerate(links, 1):
            self.stats['total'] += 1
            
            listing_result = self.crawler.fetch(link, f"Computer listing {idx}/{len(links)}")
            
            if listing_result.error_type != ErrorType.SUCCESS:
                self.stats['failed'] += 1
                yield link, 'failed', f"Fetch failed: {listing_result.error_msg}"
                continue
            
            listing, action, message = self._process_listing(listing_result.html, link)
            self.stats[action] += 1
            
            if action in ['new', 'new_version', 'updated', 'matched']:
                self.stats['matched'] += 1
            
            yield link, action, message
    
    def scrape_category(self, max_pages: int = 5, limit: int = 0) -> List[ComputerListing]:
        """Scrape computer category."""
        self.initialize()
        
        processed = []
        base = f"{self.config.scraper.base_url}{self.COMPUTER_CATEGORY_PATH}"
        page_num = 1
        has_more = True
        
        while has_more:
            page_url = base if page_num == 1 else f"{base}page{page_num}.html"
            
            for link, action, message in self._scrape_category_page(page_url):
                logger.info(f"[{action.upper()}] {message}")
            
            page_num += 1
            
            if limit > 0 and self.stats['total'] >= limit:
                logger.info(f"Limit reached: {self.stats['total']} listings")
                has_more = False
            
            if max_pages > 0 and page_num > max_pages:
                logger.info(f"Page limit reached ({max_pages})")
                has_more = False
            
            # Check if there are more pages
            result = self.crawler.fetch(page_url, "Check pagination")
            if result.error_type == ErrorType.SUCCESS:
                parser = ComputerListingParser(result.html, page_url)
                next_page = parser.has_next_page()
                if not next_page:
                    has_more = False
            else:
                has_more = False
        
        logger.info("Computer scraping completed")
        return processed
    
    def run(self) -> Dict:
        """Run the computer scraping process."""
        self.initialize()
        
        with get_session() as session:
            run_id = ScrapeRunRepository.create(
                session,
                category='computer',
                config={
                    'test_mode': self.config.scraper.test_mode,
                    'max_listings': self.config.scraper.max_listings,
                }
            )
        
        logger.info(f"Computer scrape run started: ID {run_id}")
        
        try:
            base = f"{self.config.scraper.base_url}{self.COMPUTER_CATEGORY_PATH}"
            page_num = 1
            has_more = True
            
            while has_more:
                page_url = base if page_num == 1 else f"{base}page{page_num}.html"
                
                for link, action, message in self._scrape_category_page(page_url):
                    logger.info(f"{action.upper()}: {message}")
                
                page_num += 1
                
                if self.config.scraper.max_listings > 0:
                    if self.stats['total'] >= self.config.scraper.max_listings:
                        logger.info(f"Listing limit reached: {self.stats['total']} listings")
                        has_more = False
                
                if self.config.scraper.max_pages > 0:
                    if page_num > self.config.scraper.max_pages:
                        logger.info(f"Page limit reached ({self.config.scraper.max_pages})")
                        has_more = False
            
            with get_session() as session:
                ScrapeRunRepository.complete(session, run_id, {
                    'status': 'completed',
                    'total': self.stats['total'],
                    'new': self.stats['new'],
                    'updated': self.stats['updated'],
                    'skipped': self.stats['unchanged'],
                    'failed': self.stats['failed']
                })
            
            logger.info("Computer scraping completed successfully")
            
        except Exception as e:
            logger.critical(f"Computer scraping failed: {e}")
            import traceback
            traceback.print_exc()
            
            with get_session() as session:
                ScrapeRunRepository.complete(session, run_id, {
                    'status': 'failed',
                    'error': str(e),
                    **self.stats
                })
            raise
        
        return self.stats
    
    def get_stats(self) -> Dict:
        """Get current scraping stats."""
        return self.stats.copy()
    
    def scrape_single(self, url: str) -> Tuple[Optional[ComputerListing], Optional[ComputerMatchResult]]:
        """Scrape a single computer URL (for testing)."""
        self.initialize()
        
        result = self.crawler.fetch(url, "single computer listing")
        
        if result.error_type != ErrorType.SUCCESS:
            logger.error(f"Fetch failed: {result.error_msg}")
            return None, None
        
        listing, action, message = self._process_listing(result.html, url)
        logger.info(f"Single scrape result: {action} - {message}")
        
        if listing is None:
            return None, None
        
        # Re-run match to get full result
        full_text = f"{listing.title} {listing.description or ''}"
        match_result = self.matcher.match(
            listing.title,
            listing.description or "",
            listing.price_eur
        )
        
        return listing, match_result