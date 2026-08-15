"""SSD matching engine using rapidfuzz."""
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
            r'\blexar\b', r'\bnetac\b', r'\bgoodram\b',
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
            r'\bp210\b',    # Patriot P210
        ]

        for pattern in series_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            tokens.update(matches)

        return list(tokens)

    def _longest_model_in_title(self, normalized_title: str) -> Optional[tuple]:
        """Find the longest reference model that appears in the title.

        Returns a tuple (model_text, reference) so callers can also know which
        SSD reference the longest model belongs to.
        """
        longest = None
        longest_len = 0
        longest_ssd = None
        for ssd in self.ssds:
            norm_model = normalize_text(ssd.model)
            if norm_model in normalized_title and len(norm_model) > longest_len:
                longest = norm_model
                longest_len = len(norm_model)
                longest_ssd = ssd
        return (longest, longest_ssd) if longest else None

    def _score_ssd_match(self, ssd: SSDReference, normalized_title: str, extracted_capacity: Optional[int]) -> Tuple[float, str]:
        """
        Score how well an SSD matches the listing.
        Returns (score, method).
        """
        score = 0.0
        method = ""

        # Build reference name
        ssd_name = normalize_text(f"{ssd.brand} {ssd.model}")

        # Get SSD-related context (exclude GPU and CPU context)
        # Remove GPU model numbers that could be confused with SSD models
        # e.g., "RTX3070" contains "3070" which might match "M480" style models
        ssd_context = normalized_title
        # Remove GPU patterns like "rtx3070", "gtx1080", "rx580", etc.
        # Also remove "(gigabyte)" or brand mentions from GPU lines like "rtx 3070 (gigabyte)"
        gpu_patterns = [
            r'rtx\s*\d{4}', r'gtx\s*\d{3,4}', r'rx\s*\d{3,4}',
            r'geforce\s+rtx\s*\d{4}', r'geforce\s+gtx\s*\d{3,4}',
            r'radeon\s+rx\s*\d{3,4}',
            r'\(\s*gigabyte\s*\)',  # Remove "(gigabyte)" from GPU lines
            r'\(\s*asus\s*\)',       # Remove "(asus)" from GPU lines
            r'\(\s*msi\s*\)',        # Remove "(msi)" from GPU lines
        ]
        for pattern in gpu_patterns:
            ssd_context = re.sub(pattern, '', ssd_context, flags=re.IGNORECASE)

        # Remove CPU patterns to avoid matching "core" to SSD models like "MP600 CORE"
        # After normalize_text, Intel CPUs look like "i714700kf" (no spaces)
        # Also remove "intel" since it's almost always CPU in computer listings
        cpu_patterns = [
            r'core\s*i\d+[\w-]*',  # "core i7-14700kf" or "core i714700kf" or "core i7"
            r'corei\d+[\w-]*',      # "corei714700kf" (no space)
            r'ryzen\s*\d+\s*\d*',    # "ryzen 7" or "ryzen 7 8700f"
            r'i\d+-\d+\w*',          # "i7-14700kf" pattern alone
            r'i\d+\d{4,}\w*',        # "i714700kf" pattern (no dash)
            r'intel\s+core',          # "intel core" - Intel is almost always CPU in listings
            r'\bintel\b',            # standalone "intel" - likely CPU brand
        ]
        for pattern in cpu_patterns:
            ssd_context = re.sub(pattern, '', ssd_context, flags=re.IGNORECASE)

        # Check for exact name match
        if ssd_name in normalized_title:
            score = 100.0
            method = "exact"
        else:
            # Fuzzy match
            score = fuzz.token_set_ratio(normalized_title, ssd_name)
            method = "fuzzy"
            # Penalize fuzzy-only wins when there is no model anchor in the title.
            # This prevents generic brand-only matches like "Patriot 120gb ssd" -> PXD.
            ssd_model_only = normalize_text(ssd.model)
            if ssd_model_only not in ssd_context:
                score -= 25
                method += "+no_model_penalty"

        # Exact (or near-exact) model part should significantly outrank fuzzy-only
        # matches and should not be drowned out by capacity scoring of a wrong variant.
        ssd_model_only = normalize_text(ssd.model)
        model_parts = ssd_model_only.split()
        model_part_found = False
        for part in model_parts:
            if len(part) >= 3 and part in ssd_context:
                idx = ssd_context.find(part)
                if idx != -1:
                    surrounding = ssd_context[max(0, idx-10):min(len(ssd_context), idx+len(part)+10)]
                    gpu_indicators = ['rtx', 'gtx', 'rx', 'geforce', 'radeon', 'gpu', 'video', 'graphics']
                    if not any(ind in surrounding for ind in gpu_indicators):
                        score += 20  # Boost for partial model match
                        method += "+model_part"
                        model_part_found = True
                        break

        # Stronger bonus when the full model token appears as a whole word.
        # This helps SN850P beat SN850, P1 beat generic P-series, etc.
        if ssd_model_only in ssd_context:
            score += 60
            method += "+full_model"
            model_part_found = True

        # Substring penalty: if the title explicitly names a longer model (e.g. SN850P),
        # penalize the shorter model (SN850) that is only a prefix match.
        # This must run even when the full ssd model is found, because "sn850" is
        # found inside "sn850p" but the listing clearly means the longer variant.
        longest_result = self._longest_model_in_title(normalized_title)
        if longest_result:
            title_model, title_model_ssd = longest_result
            if (len(title_model) > len(ssd_model_only)
                    and title_model != ssd_model_only
                    and (title_model.startswith(ssd_model_only) or ssd_model_only.startswith(title_model))):
                score -= 80
                method += "+short_model_penalty"

        # Generic model guard: references whose model is just a generic word like "SSD"
        # should not win on capacity alone unless the brand is actually present in the title.
        generic_models = {'ssd', 'solid', 'drive', 'hard', 'harddrive'}
        if ssd_model_only in generic_models:
            ssd_brand_lower = (ssd.brand or '').lower()
            brand_in_context = bool(ssd_brand_lower) and (ssd_brand_lower in normalized_title or ssd_brand_lower in ssd_context)
            if not brand_in_context:
                score -= 150
                method += "+generic_model_no_brand"

        # If no concrete model part matched, penalize generic fuzzy wins
        # so that title-only brand matches don't win over unrelated models.
        if not model_part_found and not ssd_name in normalized_title:
            score -= 20
            method += "+no_model_anchor"

        # Special bonus for "nv2" in title when SSD model has it
        if 'nv2' in normalized_title and 'nv2' in ssd_model_only:
            score += 50
            method += "+nv2_match"

        # Penalize a match whose base model is a substring of the actual model in the title.
        # e.g. title has "sn850p", but reference is "sn850": that reference should not win.
        longest_result = self._longest_model_in_title(normalized_title)
        if longest_result:
            title_model, title_model_ssd = longest_result
            if (len(title_model) >= len(ssd_model_only)
                    and title_model != ssd_model_only
                    and not title_model.startswith(ssd_model_only)
                    and not ssd_model_only.startswith(title_model)):
                score -= 70
                method += "+substring_penalty"

        # Handle slash variants (e.g., SU650/SU655)
        if '/' in ssd.model:
            for variant in ssd.model.split('/'):
                norm_variant = normalize_text(variant.strip())
                if len(norm_variant) >= 3 and norm_variant in ssd_context:
                    # Check surrounding context
                    idx = ssd_context.find(norm_variant)
                    if idx != -1:
                        surrounding = ssd_context[max(0, idx-10):min(len(ssd_context), idx+len(norm_variant)+10)]
                        gpu_indicators = ['rtx', 'gtx', 'rx', 'geforce', 'radeon', 'gpu', 'video', 'graphics']
                        if not any(ind in surrounding for ind in gpu_indicators):
                            score += 30  # Higher boost for exact variant match
                            method += "+variant_exact"
                            break

        # Check for brand mention (handle typos with fuzzy matching)
        brand_mentioned = False
        ssd_brand_lower = ssd.brand.lower()
        if ssd_brand_lower in normalized_title:
            brand_mentioned = True
        else:
            # Try fuzzy matching for common typos (e.g., "Kinsgotn" -> "Kingston")
            words_in_title = normalized_title.split()
            for word in words_in_title:
                if len(word) >= 5:  # Only check substantial words
                    similarity = fuzz.ratio(word, ssd_brand_lower)
                    if similarity >= 75:  # 75% similarity threshold
                        brand_mentioned = True
                        break

        if brand_mentioned:
            score += 30
            method += "+brand_match"

        # Capacity matching - CRITICAL for correct SSD identification
        if extracted_capacity and ssd.capacity_gb:
            capacity_diff = abs(extracted_capacity - ssd.capacity_gb)
            if capacity_diff == 0:
                # Perfect capacity match - MAJOR boost
                score += 100
                method += "+capacity_exact"
            else:
                # Calculate tolerance (10% of extracted capacity, min 20GB, max 100GB)
                tolerance = min(max(extracted_capacity * 0.1, 20), 100)
                if capacity_diff <= tolerance:
                    # Within tolerance - small penalty proportional to difference
                    penalty = int((capacity_diff / tolerance) * 50)
                    score -= penalty
                    method += f"+capacity_near_{ssd.capacity_gb}"
                else:
                    # Outside tolerance - heavy penalty
                    score -= 200
                    method += f"+capacity_mismatch_{ssd.capacity_gb}vs{extracted_capacity}"

        return score, method

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

        # Remove GPU context before matching SSD
        # Remove GPU patterns like "rtx3070", "gtx1080", "rx580", etc.
        # Also remove "(gigabyte)" or brand mentions from GPU lines like "rtx 3070 (gigabyte)"
        gpu_patterns = [
            r'rtx\s*\d{4}', r'gtx\s*\d{3,4}', r'rx\s*\d{3,4}',
            r'geforce\s+rtx\s*\d{4}', r'geforce\s+gtx\s*\d{3,4}',
            r'radeon\s+rx\s*\d{3,4}',
            r'\(\s*gigabyte\s*\)',  # Remove "(gigabyte)" from GPU lines
            r'\(\s*asus\s*\)',       # Remove "(asus)" from GPU lines
            r'\(\s*msi\s*\)',        # Remove "(msi)" from GPU lines
        ]
        ssd_context = normalized
        for pattern in gpu_patterns:
            ssd_context = re.sub(pattern, '', ssd_context, flags=re.IGNORECASE)

        # Remove CPU patterns to avoid matching "core" to SSD models like "MP600 CORE"
        # After normalize_text, Intel CPUs look like "i714700kf" (no spaces)
        # Also remove "intel" since it's almost always CPU in computer listings
        cpu_patterns = [
            r'core\s*i\d+[\w-]*',  # "core i7-14700kf" or "core i714700kf" or "core i7"
            r'corei\d+[\w-]*',      # "corei714700kf" (no space)
            r'ryzen\s*\d+\s*\d*',    # "ryzen 7" or "ryzen 7 8700f"
            r'i\d+-\d+\w*',          # "i7-14700kf" pattern alone
            r'i\d+\d{4,}\w*',        # "i714700kf" pattern (no dash)
            r'intel\s+core',          # "intel core" - Intel is almost always CPU in listings
            r'\bintel\b',            # standalone "intel" - likely CPU brand
        ]
        for pattern in cpu_patterns:
            ssd_context = re.sub(pattern, '', ssd_context, flags=re.IGNORECASE)

        # Extract brand from title
        brand_tokens = self._extract_ssd_tokens(title)
        brands_in_title = set()
        for token in brand_tokens:
            if token.lower() in ['samsung', 'kingston', 'crucial', 'wd', 'western digital',
                                 'seagate', 'sandisk', 'intel', 'adata', 'teamgroup',
                                 'corsair', 'sabrent', 'silicon power', 'xpg', 'transcend',
                                 'patriot', 'hp', 'acer', 'gigabyte', 'msi', 'asus', 'lexar',
                                 'netac', 'goodram']:
                brands_in_title.add(token.lower())

        # SPECIAL HANDLING: Check for common typos using fuzzy matching
        # e.g., "Kinsgotn" should match "Kingston"
        known_brands = ['samsung', 'kingston', 'crucial', 'wd', 'western digital',
                        'seagate', 'sandisk', 'intel', 'adata', 'teamgroup',
                        'corsair', 'sabrent', 'silicon power', 'xpg', 'transcend',
                        'patriot', 'hp', 'acer', 'gigabyte', 'msi', 'asus', 'lexar',
                        'netac', 'goodram']
        normalized_lower = normalized.lower()
        words_in_title = normalized_lower.split()
        for word in words_in_title:
            if len(word) >= 5:  # Only check substantial words
                for known_brand in known_brands:
                    similarity = fuzz.ratio(word, known_brand)
                    if similarity >= 75:  # 75% similarity threshold for typos
                        brands_in_title.add(known_brand)
                        break

        # Get candidate SSDs by brand first
        candidates = []
        if brands_in_title:
            for brand in brands_in_title:
                if brand in self.brand_to_ssds:
                    candidates.extend(self.brand_to_ssds[brand])
        else:
            # No brand mentioned - don't try to match specific SSD
            # Return empty so computer_matcher can use generic fallback
            return SSDMatchResult()

        # Score all candidates before any capacity pre-filter so that
        # title-derived capacity does not hide the right model variant.
        best_ssd = None
        best_score = -float('inf')
        best_method = ""

        # Extract capacity from the title itself and use it as a tie-breaker when no
        # spec capacity was provided. This fixes "Patriot 120gb ssd" / "SN850P 2Tb" etc.
        title_capacity = self._extract_capacity(title)
        effective_capacity = extracted_capacity if extracted_capacity is not None else title_capacity

        for ssd in candidates:
            score, method = self._score_ssd_match(ssd, normalized, effective_capacity)

            if score > best_score:
                best_score = score
                best_ssd = ssd
                best_method = method

        # If the top candidate mismatches capacity, prefer a same-model variant with the
        # title-derived capacity as long as its name/model still matches strongly.
        if best_ssd and effective_capacity and best_ssd.capacity_gb:
            capacity_diff = abs(effective_capacity - best_ssd.capacity_gb)
            tolerance = min(max(effective_capacity * 0.1, 20), 100)
            if capacity_diff > tolerance:
                best_name = normalize_text(f"{best_ssd.brand} {best_ssd.model}")
                for ssd in candidates:
                    if ssd.id == best_ssd.id:
                        continue
                    if not ssd.capacity_gb:
                        continue
                    this_name = normalize_text(f"{ssd.brand} {ssd.model}")
                    if this_name != best_name:
                        continue
                    if abs(effective_capacity - ssd.capacity_gb) <= tolerance:
                        score, method = self._score_ssd_match(ssd, normalized, effective_capacity)
                        if score >= best_score * 0.85 and score >= 50:
                            best_ssd = ssd
                            best_score = score
                            best_method = method + "+capacity_variant"
                            break

        # Secondary fix: if the best candidate is a substring of a longer model mentioned
        # in the title, prefer the longer-model variant, but keep the capacity tie-breaker
        # so we don't swap a correct capacity match for a wrong-capacity sibling.
        if best_ssd and effective_capacity:
            longest_result = self._longest_model_in_title(normalized)
            if longest_result:
                title_model, title_model_ssd = longest_result
                ssd_model_only = normalize_text(best_ssd.model)
                if (title_model and title_model_ssd
                        and title_model != ssd_model_only
                        and title_model.startswith(ssd_model_only)
                        and title_model_ssd.brand.lower() == best_ssd.brand.lower()):
                    cap_ok = True
                    if effective_capacity and title_model_ssd.capacity_gb:
                        tolerance = min(max(effective_capacity * 0.1, 20), 100)
                        cap_ok = abs(effective_capacity - title_model_ssd.capacity_gb) <= tolerance
                    score, method = self._score_ssd_match(title_model_ssd, normalized, effective_capacity)
                    if score >= 50 and cap_ok:
                        best_ssd = title_model_ssd
                        best_score = score
                        best_method = method + "+full_title_model"

        # Require minimum score of 50 for a match
        if best_ssd and best_score >= 50:
            confidence = min(best_score / 100.0, 1.0)
            return SSDMatchResult(
                ssd=best_ssd,
                confidence=confidence,
                method=best_method
            )

        return SSDMatchResult()

    def get_ssd_by_id(self, ssd_id: int) -> Optional[SSDReference]:
        """Get an SSD by its ID."""
        for ssd in self.ssds:
            if ssd.id == ssd_id:
                return ssd
        return None
