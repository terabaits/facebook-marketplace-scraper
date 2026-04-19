"""SSD matching engine using rapidfuzz."""
import re
from typing import Optional, List, Tuple
from rapidfuzz import fuzz, process

from src.models.schemas import SSDReference, SSDMatchResult
from src.utils.text import normalize_text
from src.utils.logger import get_logger

logger = get_logger("ssd_matcher")


class SSDMatcher:
    """
    Matches scraped SSD listing titles to SSD reference database.
    """
    
    def __init__(self, ssd_list: List[SSDReference]):
        """
        Initialize with SSD reference list.
        
        Args:
            ssd_list: List of SSDReference loaded from database
        """
        self.ssds = ssd_list
        self._build_index()
        logger.info(f"SSDMatcher initialized with {len(ssd_list)} SSDs")
    
    def _build_index(self):
        """Build search index from SSD references."""
        self.name_to_ssd = {}
        self.searchable_names = []
        self.brand_to_ssds = {}  # Group SSDs by brand
        
        for ssd in self.ssds:
            # Primary name: Brand + Model
            norm = normalize_text(f"{ssd.brand} {ssd.model}")
            self.searchable_names.append(norm)
            self.name_to_ssd[norm] = ssd
            
            # Group by brand
            brand_key = normalize_text(ssd.brand)
            if brand_key not in self.brand_to_ssds:
                self.brand_to_ssds[brand_key] = []
            self.brand_to_ssds[brand_key].append(ssd)
            
            # All keyword variants
            for kw in ssd.search_keywords:
                if kw and kw not in self.name_to_ssd:
                    norm_kw = normalize_text(kw)
                    self.searchable_names.append(norm_kw)
                    self.name_to_ssd[norm_kw] = ssd
    
    def _extract_capacity(self, text: str) -> Optional[int]:
        """Extract capacity in GB from text."""
        patterns = [
            r'(\d+)\s*TB\b',
            r'(\d+)\s*GB\b',
            r'(\d+)\s*T\b',
            r'(\d+)\s*G\b',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    val = int(match)
                    if 'tb' in pattern.lower():
                        val = val * 1000
                    return val
                except ValueError:
                    continue
        return None
    
    def _extract_ssd_tokens(self, title: str) -> List[str]:
        """Extract SSD-specific tokens from title."""
        tokens = set()
        normalized = normalize_text(title)
        
        brand_patterns = [
            r'\bsamsung\b', r'\bkingston\b', r'\bcrucial\b', r'\bwd\b',
            r'\bwestern digital\b', r'\bseagate\b', r'\bsandisk\b', r'\bintel\b',
            r'\badata\b', r'\bteamgroup\b', r'\bcorsair\b', r'\bsabrent\b',
            r'\bsilicon power\b', r'\bxpg\b', r'\btranscend\b', r'\bpatriot\b',
            r'\bhp\b', r'\bacer\b', r'\bgigabyte\b', r'\bmsi\b', r'\basus\b',
            r'\blexar\b',
        ]
        
        for pattern in brand_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            tokens.update(matches)
        
        series_patterns = [
            r'\b870\s*qvo\b', r'\b870\s*evo\b', r'\b870\s*pro\b',
            r'\b860\s*qvo\b', r'\b860\s*evo\b', r'\b860\s*pro\b',
            r'\b850\s*evo\b', r'\b850\s*pro\b',
            r'\b980\s*pro\b', r'\b990\s*pro\b',
            r'\bnv\d+\b', r'\bsnm\d+\b', r'\bmx\d+\b', r'\bx\d+\b',
            r'\bpcie\s*\d+\.?\d*\b', r'\bm\.2\b', r'\bsata\b', r'\bnvme\b',
            r'\bqvo\b', r'\bevo\b', r'\bpro\b', r'\bgm\d+\b',
        ]
        
        for pattern in series_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            tokens.update(matches)
        
        return list(tokens)
    
    def match_listing(self, title: str, extracted_capacity: Optional[int] = None) -> SSDMatchResult:
        """
        Match a listing title to an SSD reference.
        
        STRICT RULE: If extracted_capacity is provided, the matched SSD MUST have
        matching capacity (within tolerance). Otherwise, return no match.
        
        Args:
            title: The listing title
            extracted_capacity: Capacity extracted from specs (if available)
            
        Returns:
            SSDMatchResult with matched SSD and confidence
        """
        if not title or len(title.strip()) < 3:
            return SSDMatchResult()
        
        normalized = normalize_text(title)
        
        # Extract brand from title
        brand_tokens = self._extract_ssd_tokens(title)
        brands_in_title = set()
        for token in brand_tokens:
            if token.lower() in ['samsung', 'kingston', 'crucial', 'wd', 'western digital', 
                                 'seagate', 'sandisk', 'intel', 'adata', 'teamgroup', 
                                 'corsair', 'sabrent', 'silicon power', 'xpg', 'transcend',
                                 'patriot', 'hp', 'acer', 'gigabyte', 'msi', 'asus', 'lexar']:
                brands_in_title.add(token.lower())
        
        # Get candidates by brand
        candidates = []
        if brands_in_title:
            for brand in brands_in_title:
                if brand in self.brand_to_ssds:
                    candidates.extend(self.brand_to_ssds[brand])
        
        if not candidates:
            candidates = self.ssds
        
        # FILTER: If we have extracted capacity, only consider SSDs with matching capacity
        # Use strict tolerance: 10% or 20GB max (whichever is smaller)
        if extracted_capacity:
            capacity_candidates = []
            for ssd in candidates:
                if ssd.capacity_gb:
                    # Calculate tolerance: max(10% of capacity, 20GB) but cap at 100GB
                    tolerance = min(max(extracted_capacity * 0.1, 20), 100)
                    if abs(extracted_capacity - ssd.capacity_gb) <= tolerance:
                        capacity_candidates.append(ssd)
            
            # If no SSDs match the capacity, return no match
            if not capacity_candidates:
                logger.info(f"No SSD with capacity {extracted_capacity}GB found in database")
                return SSDMatchResult()
            
            # Use only capacity-matched candidates
            candidates = capacity_candidates
        
        # Step 1: Try exact substring match
        best_exact_match = None
        best_exact_score = 0
        
        for ssd in candidates:
            norm_name = normalize_text(f"{ssd.brand} {ssd.model}")
            
            if norm_name in normalized:
                score = len(norm_name)
                if score > best_exact_score:
                    best_exact_score = score
                    best_exact_match = ssd
            
            norm_model = normalize_text(ssd.model)
            if norm_model in normalized:
                score = len(norm_model)
                if score > best_exact_score:
                    best_exact_score = score
                    best_exact_match = ssd
        
        if best_exact_match:
            confidence = 0.95
            method = "exact"
            
            # If we have capacity info, verify it with strict tolerance
            if extracted_capacity and best_exact_match.capacity_gb:
                tolerance = min(max(extracted_capacity * 0.1, 20), 100)
                if abs(extracted_capacity - best_exact_match.capacity_gb) <= tolerance:
                    confidence = 1.0
                    method = "exact+capacity_verified"
                else:
                    # Capacity doesn't match - reject this match
                    logger.info(f"Rejecting match: capacity mismatch ({extracted_capacity}GB vs {best_exact_match.capacity_gb}GB)")
                    return SSDMatchResult()
            
            return SSDMatchResult(
                ssd=best_exact_match,
                confidence=confidence,
                method=method
            )
        
        # Step 2: Try fuzzy matching (only on capacity-matched candidates)
        tokens = self._extract_ssd_tokens(title)
        
        if tokens:
            fuzzy_candidates = []
            for token in tokens:
                for ssd in candidates:
                    norm_name = normalize_text(f"{ssd.brand} {ssd.model}")
                    if token in norm_name or token in normalize_text(ssd.model):
                        fuzzy_candidates.append(ssd)
            
            if fuzzy_candidates:
                seen = set()
                unique_candidates = []
                for ssd in fuzzy_candidates:
                    if ssd.id not in seen:
                        seen.add(ssd.id)
                        unique_candidates.append(ssd)
                
                best_match = None
                best_score = 0
                
                for ssd in unique_candidates[:20]:
                    ssd_name = normalize_text(f"{ssd.brand} {ssd.model}")
                    score = fuzz.token_set_ratio(normalized, ssd_name)
                    
                    if score > best_score:
                        best_score = score
                        best_match = ssd
                
                if best_match and best_score >= 70:
                    return SSDMatchResult(
                        ssd=best_match,
                        confidence=min(best_score / 100.0, 0.95),
                        method="fuzzy"
                    )
        
        return SSDMatchResult()
    
    def get_ssd_by_id(self, ssd_id: int) -> Optional[SSDReference]:
        """Get an SSD by its ID."""
        for ssd in self.ssds:
            if ssd.id == ssd_id:
                return ssd
        return None
