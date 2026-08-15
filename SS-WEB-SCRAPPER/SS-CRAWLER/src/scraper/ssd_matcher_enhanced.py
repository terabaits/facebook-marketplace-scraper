"""Enhanced SSD matching engine that can match multiple SSDs from a listing."""
import re
from typing import Optional, List, Tuple, Dict
from rapidfuzz import fuzz, process

from src.models.schemas import SSDReference, SSDMatchResult
from src.utils.text import normalize_text
from src.utils.logger import get_logger

logger = get_logger("ssd_matcher")


class SSDMatcher:
    """
    Matches scraped SSD listing titles to SSD reference database.
    Supports matching multiple SSDs from a single listing.
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
        self.name_to_ssds: Dict[str, List[SSDReference]] = {}  # name -> list of SSDs (different capacities)
        self.searchable_names = []
        self.brand_to_ssds: Dict[str, List[SSDReference]] = {}  # Group SSDs by brand
        
        for ssd in self.ssds:
            # Primary name: Brand + Model
            norm = normalize_text(f"{ssd.brand} {ssd.model}")
            self.searchable_names.append(norm)
            if norm not in self.name_to_ssds:
                self.name_to_ssds[norm] = []
            self.name_to_ssds[norm].append(ssd)
            
            # Group by brand
            brand_key = normalize_text(ssd.brand)
            if brand_key not in self.brand_to_ssds:
                self.brand_to_ssds[brand_key] = []
            self.brand_to_ssds[brand_key].append(ssd)
            
            # All keyword variants
            for kw in ssd.search_keywords:
                if kw:
                    norm_kw = normalize_text(kw)
                    self.searchable_names.append(norm_kw)
                    if norm_kw not in self.name_to_ssds:
                        self.name_to_ssds[norm_kw] = []
                    self.name_to_ssds[norm_kw].append(ssd)
            
            # Also add model-only index for partial matches
            norm_model = normalize_text(ssd.model)
            if norm_model not in self.name_to_ssds:
                self.name_to_ssds[norm_model] = []
            self.name_to_ssds[norm_model].append(ssd)
            
            # Handle model variants with slashes (e.g., "SU650/SU655")
            if '/' in ssd.model:
                for variant in ssd.model.split('/'):
                    norm_variant = normalize_text(variant.strip())
                    if norm_variant:
                        if norm_variant not in self.name_to_ssds:
                            self.name_to_ssds[norm_variant] = []
                        self.name_to_ssds[norm_variant].append(ssd)
    
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
            r'\bsu\d+\b',  # ADATA SU series (SU650, SU655, etc)
            r'\ba\d+\b',   # Generic model numbers like A400
        ]
        
        for pattern in series_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            tokens.update(matches)
        
        return list(tokens)
    
    def _score_ssd_match(self, ssd: SSDReference, normalized_title: str, extracted_capacity: Optional[int]) -> Tuple[float, str]:
        """
        Score how well an SSD matches the listing.
        Returns (score, method).
        """
        score = 0.0
        method = ""
        
        # Build reference name
        ssd_name = normalize_text(f"{ssd.brand} {ssd.model}")
        
        # Check for exact name match
        if ssd_name in normalized_title:
            score = 100.0
            method = "exact"
        else:
            # Fuzzy match
            score = fuzz.token_set_ratio(normalized_title, ssd_name)
            method = "fuzzy"
        
        # Check for model-only match (higher weight)
        ssd_model_only = normalize_text(ssd.model)
        model_parts = ssd_model_only.split()
        for part in model_parts:
            if len(part) >= 3 and part in normalized_title:
                score += 20  # Boost for partial model match
                method += "+model_part"
                break
        
        # Handle slash variants (e.g., SU650/SU655)
        if '/' in ssd.model:
            for variant in ssd.model.split('/'):
                norm_variant = normalize_text(variant.strip())
                if len(norm_variant) >= 3 and norm_variant in normalized_title:
                    score += 30  # Higher boost for exact variant match
                    method += "+variant_exact"
                    break
        
        # Capacity matching bonus/penalty
        if extracted_capacity and ssd.capacity_gb:
            capacity_diff = abs(extracted_capacity - ssd.capacity_gb)
            if capacity_diff == 0:
                # Perfect capacity match
                score += 50
                method += "+capacity_exact"
            else:
                # Calculate tolerance
                tolerance = min(max(extracted_capacity * 0.1, 20), 100)
                if capacity_diff <= tolerance:
                    # Within tolerance
                    score += 30 * (1 - capacity_diff / tolerance)
                    method += "+capacity_close"
                else:
                    # Outside tolerance - significant penalty
                    score -= 100
                    method += "+capacity_mismatch"
        
        return score, method
    
    def match_listing(self, title: str, extracted_capacity: Optional[int] = None) -> SSDMatchResult:
        """
        Match a listing title to a single SSD reference.
        
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
        
        # Get candidate SSDs by brand first
        candidates = []
        if brands_in_title:
            for brand in brands_in_title:
                if brand in self.brand_to_ssds:
                    candidates.extend(self.brand_to_ssds[brand])
        else:
            candidates = self.ssds
        
        # If we have capacity, filter candidates to those with matching capacity
        if extracted_capacity:
            capacity_candidates = []
            for ssd in candidates:
                if ssd.capacity_gb:
                    tolerance = min(max(extracted_capacity * 0.1, 20), 100)
                    if abs(extracted_capacity - ssd.capacity_gb) <= tolerance:
                        capacity_candidates.append(ssd)
            
            if capacity_candidates:
                candidates = capacity_candidates
        
        # Score all candidates
        best_ssd = None
        best_score = -float('inf')
        best_method = ""
        
        for ssd in candidates:
            score, method = self._score_ssd_match(ssd, normalized, extracted_capacity)
            
            if score > best_score:
                best_score = score
                best_ssd = ssd
                best_method = method
        
        # Require minimum score of 50 for a match
        if best_ssd and best_score >= 50:
            confidence = min(best_score / 100.0, 1.0)
            return SSDMatchResult(
                ssd=best_ssd,
                confidence=confidence,
                method=best_method
            )
        
        return SSDMatchResult()
    
    def match_all_in_text(self, text: str) -> List[SSDMatchResult]:
        """
        Find and match ALL SSDs mentioned in the text.
        
        This handles listings with multiple SSDs like:
        - "Samsung 870 EVO 250GB + Crucial T500 500GB"
        - "2x Samsung 870 EVO 500GB"
        
        Args:
            text: The full listing text
            
        Returns:
            List of SSDMatchResult for all matched SSDs
        """
        if not text or len(text.strip()) < 3:
            return []
        
        normalized = normalize_text(text)
        matches = []
        matched_regions = set()  # Track which text regions we've matched
        
        # First, try to find explicit SSD mentions with brand + model + capacity
        # Pattern: "Samsung 870 EVO 250GB" or "Crucial T500 500 GB"
        ssd_patterns = [
            # Brand + Model + Capacity
            r'(samsung|kingston|crucial|wd|western digital|seagate|sandisk|intel|adata|teamgroup|corsair|sabrent|silicon power|xpg|transcend|patriot|hp|acer|gigabyte|msi|asus|lexar)\s+(\w+[\s\w]*)\s+(\d+)\s*(?:gb|g)',
            # Brand + Model + Capacity with "SSD" keyword
            r'(samsung|kingston|crucial|wd|western digital|seagate|sandisk|intel|adata|teamgroup|corsair|sabrent|silicon power|xpg|transend|patriot|hp|acer|gigabyte|msi|asus|lexar)\s+(\w+[\s\w]*)\s+ssd\s+(\d+)\s*(?:gb|g)',
        ]
        
        for pattern in ssd_patterns:
            for match in re.finditer(pattern, normalized, re.IGNORECASE):
                start, end = match.span()
                # Skip if we already matched this region
                if any(start < e and end > s for s, e in matched_regions):
                    continue
                
                brand = match.group(1).strip()
                model = match.group(2).strip()
                capacity = int(match.group(3))
                
                # Find best matching SSD
                ssd_match = self._find_exact_match(brand, model, capacity)
                if ssd_match.ssd:
                    matches.append(ssd_match)
                    matched_regions.add((start, end))
        
        # If no explicit matches found, fall back to brand detection
        if not matches:
            # Check for each brand in the database
            for brand_key, brand_ssds in self.brand_to_ssds.items():
                # Find all occurrences of this brand in the text
                brand_pattern = r'\b' + re.escape(brand_key) + r'\b'
                for match in re.finditer(brand_pattern, normalized, re.IGNORECASE):
                    start = match.start()
                    
                    # Look at context around the brand mention
                    context_start = max(0, start - 50)
                    context_end = min(len(normalized), start + 100)
                    context = normalized[context_start:context_end]
                    
                    # Try to match an SSD from this brand
                    ssd_match = self._match_in_context(brand_key, context)
                    if ssd_match.ssd:
                        match_span = (start, start + len(brand_key))
                        # Avoid duplicates
                        if not any(match_span[0] < e and match_span[1] > s for s, e in matched_regions):
                            matches.append(ssd_match)
                            matched_regions.add(match_span)
        
        return matches
    
    def _find_exact_match(self, brand: str, model: str, capacity: int) -> SSDMatchResult:
        """Find exact match by brand, model, and capacity."""
        normalized_brand = normalize_text(brand)
        normalized_model = normalize_text(model)
        
        best_match = None
        best_score = 0
        
        for ssd in self.ssds:
            ssd_brand = normalize_text(ssd.brand)
            ssd_model = normalize_text(ssd.model)
            
            # Check brand match
            if ssd_brand != normalized_brand:
                continue
            
            # Check model match (fuzzy)
            model_score = fuzz.ratio(normalized_model, ssd_model)
            if model_score < 60:
                continue
            
            # Check capacity match
            if ssd.capacity_gb and abs(ssd.capacity_gb - capacity) <= capacity * 0.1:
                total_score = model_score + 100  # Bonus for capacity match
                if total_score > best_score:
                    best_score = total_score
                    best_match = ssd
        
        if best_match:
            return SSDMatchResult(
                ssd=best_match,
                confidence=min(best_score / 200.0, 1.0),
                method="exact_brand_model_capacity"
            )
        
        return SSDMatchResult()
    
    def _match_in_context(self, brand: str, context: str) -> SSDMatchResult:
        """Match an SSD within a text context."""
        # Filter SSDs by brand
        brand_ssds = self.brand_to_ssds.get(brand, [])
        if not brand_ssds:
            return SSDMatchResult()
        
        best_ssd = None
        best_score = 0
        best_method = ""
        
        # Extract capacity from context
        extracted_capacity = self._extract_capacity(context)
        
        for ssd in brand_ssds:
            score, method = self._score_ssd_match(ssd, context, extracted_capacity)
            if score > best_score and score >= 50:
                best_score = score
                best_ssd = ssd
                best_method = method
        
        if best_ssd:
            return SSDMatchResult(
                ssd=best_ssd,
                confidence=min(best_score / 100.0, 1.0),
                method=best_method
            )
        
        return SSDMatchResult()
    
    def get_ssd_by_id(self, ssd_id: int) -> Optional[SSDReference]:
        """Get an SSD by its ID."""
        for ssd in self.ssds:
            if ssd.id == ssd_id:
                return ssd
        return None
