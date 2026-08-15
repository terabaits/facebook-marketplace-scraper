"""Case matching engine using rapidfuzz."""
import re
from typing import Optional, List, Tuple, Dict
from rapidfuzz import fuzz

from src.models.schemas import CaseReference, CaseMatchResult
from src.utils.text import normalize_text
from src.utils.logger import get_logger

logger = get_logger("case_matcher")


class CaseMatcher:
    """Matches scraped case listings to case reference database."""
    
    def __init__(self, case_list: List[CaseReference]):
        """Initialize with case reference list."""
        self.cases = case_list
        self._build_index()
        logger.info(f"CaseMatcher initialized with {len(case_list)} case references")
    
    def _build_index(self):
        """Build search index from case references."""
        self.searchable_names = []
        self.name_to_cases: Dict[str, List[CaseReference]] = {}
        self.brand_to_cases: Dict[str, List[CaseReference]] = {}
        
        for case in self.cases:
            # Primary name
            norm = normalize_text(case.name)
            self.searchable_names.append(norm)
            if norm not in self.name_to_cases:
                self.name_to_cases[norm] = []
            self.name_to_cases[norm].append(case)
            
            # Brand index
            brand_key = normalize_text(case.name.split()[0]) if case.name else ""
            if brand_key:
                if brand_key not in self.brand_to_cases:
                    self.brand_to_cases[brand_key] = []
                self.brand_to_cases[brand_key].append(case)
            
            # All keyword variants
            for kw in case.search_keywords:
                if kw:
                    norm_kw = normalize_text(kw)
                    self.searchable_names.append(norm_kw)
                    if norm_kw not in self.name_to_cases:
                        self.name_to_cases[norm_kw] = []
                    self.name_to_cases[norm_kw].append(case)
    
    def match_listing(self, title: str, price: Optional[float] = None) -> CaseMatchResult:
        """Match a listing to a case reference."""
        if not title or len(title.strip()) < 3:
            return CaseMatchResult()
        
        normalized = normalize_text(title)
        
        # Skip if this looks like a PSU mention (common brand + model number pattern)
        # e.g., "corsair cx600" should match PSU, not case
        psu_patterns = [
            r'corsair\s+cx\d+',
            r'corsair\s+rm\d+',
            r'corsair\s+tx\d+',
            r'corsair\s+vs\d+',
            r'corsair\s+sf\d+',
            r'evga\s+\d{3,4}',
            r'cooler\s*master\s+\w+\d+',
            r'be\s*quiet\s+\w+\s*\d+',
            r'seasonic\s+\w+\s*\d+',
        ]
        for pattern in psu_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                return CaseMatchResult()
        
        # Skip if no case-related keywords in text
        # Be strict - require 'korpuss', 'case', 'chassis', 'tower' - NOT just 'mini'
        case_keywords = ['case', 'korpuss', 'chassis', 'tower']
        has_case_mention = any(kw in normalized for kw in case_keywords)
        if not has_case_mention:
            return CaseMatchResult()
        
        # Extract brand
        brand_tokens = self._extract_case_tokens(title)
        brands_in_title = set()
        for token in brand_tokens:
            if token.lower() in self.brand_to_cases:
                brands_in_title.add(token.lower())
        
        # Get candidates
        candidates = []
        if brands_in_title:
            for brand in brands_in_title:
                candidates.extend(self.brand_to_cases[brand])
        else:
            candidates = self.cases
        
        # Score all candidates
        best_case = None
        best_score = -float('inf')
        best_method = ""
        
        for case in candidates:
            score, method = self._score_case_match(case, normalized, price)
            if score > best_score:
                best_score = score
                best_case = case
                best_method = method
        
        if best_case and best_score >= 50:
            confidence = min(best_score / 100.0, 1.0)
            return CaseMatchResult(
                case=best_case,
                confidence=confidence,
                method=best_method
            )
        
        return CaseMatchResult()
    
    def _score_case_match(self, case: CaseReference, normalized_title: str,
                          price: Optional[float]) -> Tuple[float, str]:
        """Score how well a case matches the listing."""
        score = 0.0
        method = ""
        
        # Exact name match
        case_name = normalize_text(case.name)
        if case_name in normalized_title:
            score = 100.0
            method = "exact"
        else:
            score = fuzz.token_set_ratio(normalized_title, case_name)
            method = "fuzzy"
        
        # Model part matching
        model_parts = case_name.split()
        for part in model_parts:
            if len(part) >= 3 and part in normalized_title:
                score += 10
                method += "+model_part"
                break
        
        # Penalize trailing version/revision tokens (e.g., "v1", "v2") that are not in the title.
        # This lets "Aerocool Viewport Mini korpuss" prefer V1 over V2 when no revision is mentioned.
        version_match = re.search(r'\b(v|rev|version|mk|edition\s+)?(\d+(?:\.\d+)?)\s*$', case_name, re.IGNORECASE)
        if version_match:
            version_token = version_match.group(0).strip()
            if version_token not in normalized_title:
                try:
                    version_num = float(version_match.group(2))
                    score -= 2.0 * version_num  # V1 -> -2, V2 -> -4, etc.
                    method += "+missing_version_penalty"
                except ValueError:
                    pass
        
        return score, method
    
    def _extract_case_tokens(self, title: str) -> List[str]:
        """Extract case-specific tokens."""
        tokens = set()
        normalized = normalize_text(title)
        
        # Common case brands
        brand_patterns = [
            r'\bcorsair\b', r'\bnzxt\b', r'\bphanteks\b', r'\bfractal\b',
            r'\bcooler\s*master\b', r'\bbe\s*quiet\b', r'\bthermaltake\b',
            r'\bdeepcool\b', r'\bli\s*an\s*li\b', r'\blian\s*li\b',
            r'\bmontech\b', r'\bhyte\b', r'\bmusetex\b', r'\bendorfy\b',
            r'\bantec\b',
        ]
        
        for pattern in brand_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            tokens.update(matches)
        
        return list(tokens)
