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
        
        for ssd in self.ssds:
            # Primary name: Brand + Model
            norm = normalize_text(f"{ssd.brand} {ssd.model}")
            self.searchable_names.append(norm)
            self.name_to_ssd[norm] = ssd
            
            # All keyword variants
            for kw in ssd.search_keywords:
                if kw and kw not in self.name_to_ssd:
                    norm_kw = normalize_text(kw)
                    self.searchable_names.append(norm_kw)
                    self.name_to_ssd[norm_kw] = ssd
    
    def _extract_capacity(self, text: str) -> Optional[int]:
        """Extract capacity in GB from text."""
        # Common patterns: 1TB, 2 TB, 1000GB, 500 GB, etc.
        patterns = [
            r'(\d+)\s*TB',
            r'(\d+)\s*tb',
            r'(\d+)\s*GB',
            r'(\d+)\s*gb',
            r'(\d+)\s*Gb',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    val = int(match)
                    # If TB, convert to GB
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
        
        # SSD brand patterns
        brand_patterns = [
            r'\bsamsung\b',
            r'\bkingston\b',
            r'\bcrucial\b',
            r'\bwd\b',
            r'\bwestern digital\b',
            r'\bseagate\b',
            r'\bsandisk\b',
            r'\bintel\b',
            r'\badata\b',
            r'\bteamgroup\b',
            r'\bcorsair\b',
            r'\bsabrent\b',
            r'\bsilicon power\b',
            r'\bxpg\b',
            r'\btranscend\b',
            r'\bpatriot\b',
            r'\bhp\b',
            r'\bacer\b',
            r'\bgigabyte\b',
            r'\bmsi\b',
            r'\basus\b',
            r'\blexar\b',
        ]
        
        for pattern in brand_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            tokens.update(matches)
        
        # Model series patterns
        series_patterns = [
            r'\b870\s*qvo\b',
            r'\b870\s*evo\b',
            r'\b870\s*pro\b',
            r'\b980\s*pro\b',
            r'\b990\s*pro\b',
            r'\bnv\d+\b',
            r'\bsnm\d+\b',
            r'\bmx\d+\b',
            r'\bx\d+\b',
            r'\bpcie\s*\d+\.?\d*\b',
            r'\bm\.2\b',
            r'\bsata\b',
            r'\bnvme\b',
        ]
        
        for pattern in series_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            tokens.update(matches)
        
        return list(tokens)
    
    def match_listing(self, title: str, extracted_capacity: Optional[int] = None) -> SSDMatchResult:
        """
        Match a listing title to an SSD reference.
        
        Args:
            title: The listing title
            extracted_capacity: Capacity extracted from specs (if available)
            
        Returns:
            SSDMatchResult with matched SSD and confidence
        """
        if not title or len(title.strip()) < 3:
            return SSDMatchResult()
        
        normalized = normalize_text(title)
        
        # Extract tokens from title
        tokens = self._extract_ssd_tokens(title)
        
        # Try direct substring match first
        for norm_name, ssd in self.name_to_ssd.items():
            if norm_name in normalized:
                confidence = 0.95
                method = "exact"
                
                # If we have capacity info, verify it
                if extracted_capacity and ssd.capacity_gb:
                    if abs(extracted_capacity - ssd.capacity_gb) <= 100:
                        confidence = 1.0
                        method = "exact+capacity_verified"
                
                return SSDMatchResult(
                    ssd=ssd,
                    confidence=confidence,
                    method=method
                )
        
        # Try fuzzy matching
        if tokens:
            # Find SSDs that share tokens
            candidates = []
            for token in tokens:
                for norm_name, ssd in self.name_to_ssd.items():
                    if token in norm_name or token in ssd.brand.lower():
                        candidates.append(ssd)
            
            if candidates:
                # Remove duplicates while preserving order
                seen = set()
                unique_candidates = []
                for ssd in candidates:
                    if ssd.id not in seen:
                        seen.add(ssd.id)
                        unique_candidates.append(ssd)
                
                # Score each candidate
                best_match = None
                best_score = 0
                
                for ssd in unique_candidates[:10]:  # Check top 10
                    ssd_name = normalize_text(f"{ssd.brand} {ssd.model}")
                    score = fuzz.token_set_ratio(normalized, ssd_name)
                    
                    # Boost for capacity match
                    if extracted_capacity and ssd.capacity_gb:
                        if abs(extracted_capacity - ssd.capacity_gb) <= 100:
                            score += 15
                    
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
