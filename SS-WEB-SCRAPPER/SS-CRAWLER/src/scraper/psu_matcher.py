"""PSU matching engine using rapidfuzz."""
import re
from typing import Optional, List, Tuple, Dict
from rapidfuzz import fuzz

from src.models.schemas import PSUReference, PSUMatchResult
from src.utils.text import normalize_text
from src.utils.logger import get_logger

logger = get_logger("psu_matcher")


class PSUMatcher:
    """Matches scraped PSU listings to PSU reference database."""
    
    def __init__(self, psu_list: List[PSUReference]):
        """Initialize with PSU reference list."""
        self.psus = psu_list
        self._build_index()
        logger.info(f"PSUMatcher initialized with {len(psu_list)} PSU references")
    
    def _build_index(self):
        """Build search index from PSU references."""
        self.searchable_names = []
        self.name_to_psus: Dict[str, List[PSUReference]] = {}
        self.brand_to_psus: Dict[str, List[PSUReference]] = {}
        
        # Multi-word brands that need special handling
        self.multi_word_brands = {
            'cooler master': 'cooler master',
            'be quiet': 'be quiet',
            'be quiet!': 'be quiet',
            'super flower': 'super flower',
        }
        
        for psu in self.psus:
            # Primary name
            norm = normalize_text(psu.name)
            self.searchable_names.append(norm)
            if norm not in self.name_to_psus:
                self.name_to_psus[norm] = []
            self.name_to_psus[norm].append(psu)
            
            # Brand index - handle multi-word brands
            psu_name_lower = psu.name.lower()
            brand_key = None
            
            # Check for multi-word brands first
            if psu_name_lower.startswith('cooler master'):
                brand_key = 'cooler master'
            elif psu_name_lower.startswith('be quiet') or psu_name_lower.startswith('be quiet!'):
                brand_key = 'be quiet'
            elif psu_name_lower.startswith('super flower'):
                brand_key = 'super flower'
            elif psu_name_lower.startswith('xfx'):
                brand_key = 'xfx'
            else:
                # Single-word brand
                brand_key = normalize_text(psu.name.split()[0]) if psu.name else ""
            
            if brand_key:
                if brand_key not in self.brand_to_psus:
                    self.brand_to_psus[brand_key] = []
                self.brand_to_psus[brand_key].append(psu)
            
            # All keyword variants
            for kw in psu.search_keywords:
                if kw:
                    norm_kw = normalize_text(kw)
                    self.searchable_names.append(norm_kw)
                    if norm_kw not in self.name_to_psus:
                        self.name_to_psus[norm_kw] = []
                    self.name_to_psus[norm_kw].append(psu)
    
    def match_listing(self, title: str, price: Optional[float] = None) -> PSUMatchResult:
        """Match a listing to a PSU reference."""
        if not title or len(title.strip()) < 3:
            return PSUMatchResult()
        
        normalized = normalize_text(title)
        
        # Small form factor / mini PC listings use external power bricks, not ATX PSUs.
        # Do not try to match a reference ATX PSU for these.
        sff_patterns = [
            r'\bbrix\b',
            r'\bnuc\b',
            r'\bmini\s*(?:pc|dators|kompiuters|computer)\b',
            r'\bsmall\s*form\s*factor\b',
            r'\btiny\b',
            r'\bcompute\s*stick\b',
            r'\bintel\s*celeron\s*n\d+\b.*\bmini\b',
        ]
        for pattern in sff_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                logger.debug(f"Small form factor / mini PC detected, skipping PSU matching")
                return PSUMatchResult()
        
        # Remove motherboard context to avoid matching motherboard brands as PSU brands
        # e.g., "Asus All Series" should not match "Asus Prime 750W" PSU
        psu_context = normalized
        # Remove motherboard lines/sections
        mb_patterns = [
            r'pamat\s+plate[^.]*',  # "pamat plate" + rest of line (Latvian)
            r'motherboard[^.]*',      # "motherboard" + rest of line
            r'mātesplate[^.]*',       # Latvian
            r'mb:[^.]*',              # "MB:" + rest of line
            r'board[^.]*',            # "Board" + rest of line (but NOT "power supply" board)
            r'asus\s+allseries[^.]*',  # "Asus AllSeries" (no space)
            r'asus\s+all\s+series[^.]*',  # "Asus All Series" (with space)
            r'asus\s+sistemas\s+bloks[^.]*',  # "Asus sistemas bloks" (system unit, contains brand)
            r'sistemas\s+bloks[^.]*',  # "sistemas bloks" section
        ]
        for pattern in mb_patterns:
            psu_context = re.sub(pattern, '', psu_context, flags=re.IGNORECASE)
        psu_context = re.sub(r'\s+', ' ', psu_context).strip()
        
        logger.debug(f"PSU context filtered: '{psu_context[:150]}...'")
        
        # Check if PSU is EXPLICITLY STATED AS NOT INCLUDED
        # Patterns like "trūkst tikai Gpu, korpuss un Psu" (missing GPU, case and PSU)
        # or "trūkst...psu" (missing...psu)
        missing_patterns = [
            r'trukst\s+.*\bpsu\b',  # trukst ... psu
            r'nav\s+.*\bpsu\b',     # nav ... psu (doesn't have PSU)
            r'bez\s+.*\bpsu\b',     # bez ... psu (without PSU)
            r'trukst\s+tikai\s+.*\bpsu\b',  # trukst tikai ... psu (only missing PSU)
        ]
        for pattern in missing_patterns:
            if re.search(pattern, normalized, re.IGNORECASE):
                logger.debug(f"PSU explicitly stated as NOT included in listing: {pattern}")
                return PSUMatchResult()
        
        # Check if PSU is mentioned as part of "what's NOT included"
        # This catches phrases like "trūkst tikai Gpu, korpuss un Psu" 
        # where PSU is listed among missing items
        if 'trukst' in normalized or 'trūkst' in title.lower():
            # Find the "trūkst" section and check if PSU is in the missing items list
            trukst_match = re.search(r'trukst[^.]*', normalized, re.IGNORECASE)
            if trukst_match:
                missing_section = trukst_match.group(0)
                # Check if PSU keywords appear in the missing items section
                psu_in_missing = any(kw in missing_section for kw in ['psu', 'barosana', 'barošana', 'block', 'bloks'])
                if psu_in_missing:
                    logger.debug(f"PSU listed as missing item in 'trūkst' section: {missing_section}")
                    return PSUMatchResult()
        
        # Check if PSU is mentioned in text - if not, return no match
        # Use psu_context (with motherboard lines removed) instead of normalized
        psu_keywords = ['psu', 'barosana', 'barošana', 'block', 'bloks', 'barošanas', 
                        'powersupply', 'power supply', 'blok', 'barošana', 'w', 'barošanas']
        has_psu_mention = any(kw in psu_context for kw in psu_keywords)
        
        # Also check for wattage patterns like "550w", "650w" which indicate PSU
        has_wattage = bool(re.search(r'\d{3,4}w', psu_context))
        
        if not has_psu_mention and not has_wattage:
            # No PSU mentioned - don't try to match
            return PSUMatchResult()
        
        # Extract brand from PSU context (not full normalized text)
        brand_tokens = self._extract_psu_tokens(psu_context)
        brands_in_title = set()
        for token in brand_tokens:
            if token.lower() in self.brand_to_psus:
                brands_in_title.add(token.lower())
        
        # Get candidates
        candidates = []
        if brands_in_title:
            for brand in brands_in_title:
                candidates.extend(self.brand_to_psus[brand])
        else:
            candidates = self.psus
        
        # Score all candidates using psu_context
        best_psu = None
        best_score = -float('inf')
        best_method = ""
        
        for psu in candidates:
            score, method = self._score_psu_match(psu, psu_context, price)
            if score > best_score:
                best_score = score
                best_psu = psu
                best_method = method
        
        # If best match is Asus brand but no explicit PSU context, reject it
        # "Asus Prime" could be motherboard, not PSU
        if best_psu and best_psu.name.lower().startswith('asus'):
            # Check if "asus" appears in the filtered PSU context
            asus_pos = psu_context.find('asus')
            # Also check for "allseries" pattern (motherboard context) 
            allseries_pos = psu_context.find('allseries')
            if asus_pos < 0 or (allseries_pos >= 0 and abs(asus_pos - allseries_pos) < 20):
                # "asus" was filtered out OR it's part of "asus allseries" motherboard pattern - reject
                logger.debug(f"Rejecting Asus PSU match - part of motherboard context")
                return PSUMatchResult()
            else:
                # Check surrounding context for PSU indicators
                context_around = psu_context[max(0, asus_pos-30):min(len(psu_context), asus_pos+30)]
                psu_indicators = ['psu', 'power', 'blok', 'w', 'barošana', 'barosana', 'supply']
                has_psu_context = any(kw in context_around for kw in psu_indicators)
                if not has_psu_context:
                    logger.debug(f"Rejecting Asus PSU match - no PSU context indicators")
                    return PSUMatchResult()

        if best_psu and best_score >= 50:
            confidence = min(best_score / 100.0, 1.0)
            return PSUMatchResult(
                psu=best_psu,
                confidence=confidence,
                method=best_method
            )
        
        return PSUMatchResult()
    
    def _score_psu_match(self, psu: PSUReference, normalized_title: str,
                         price: Optional[float]) -> Tuple[float, str]:
        """Score how well a PSU matches the listing."""
        score = 0.0
        method = ""
        
        # Normalize PSU name from reference
        psu_name = normalize_text(psu.name)
        
        # Extract wattage from title FIRST (for all logic)
        title_wattage = self._extract_wattage(normalized_title)
        psu_wattage = str(psu.wattage) if psu.wattage else None
        
        # Special handling for "be quiet!" variations - normalize title for comparison
        normalized_for_brand = normalized_title.replace('bequiet', 'be quiet').replace('bequiet!', 'be quiet')
        
        # Fix common typos in normalized title
        normalized_for_brand = normalized_for_brand.replace('thoughpower', 'toughpower')
        normalized_for_brand = normalized_for_brand.replace('thermaltakethough', 'thermaltaketough')
        normalized_for_brand = normalized_for_brand.replace('chieftek', 'chieftec')  # Fix typo: CHIEFTEK -> Chieftec
        
        # Also fix typo in psu_name for comparison
        psu_name_fixed = psu_name.replace('thoughpower', 'toughpower')
        
        # Get PSU brand and check if in PSU context
        psu_name_lower = psu.name.lower()
        if psu_name_lower.startswith('cooler master'):
            psu_brand = 'cooler master'
        elif psu_name_lower.startswith('be quiet'):
            psu_brand = 'be quiet'
        elif psu_name_lower.startswith('super flower'):
            psu_brand = 'super flower'
        elif psu_name_lower.startswith('xfx'):
            psu_brand = 'xfx'
        elif psu_name_lower.startswith('xilence'):
            psu_brand = 'xilence'
        elif psu_name_lower.startswith('kolink'):
            psu_brand = 'kolink'
        else:
            psu_brand = psu.name.split()[0].lower() if psu.name else ""
        
        # Find the position of "psu" or similar keyword in the text
        psu_pos = -1
        for kw in ['psu', 'barosana', 'barošana', 'block', 'bloks', 'barošanas', 'powersupply']:
            pos = normalized_title.find(kw)
            if pos != -1:
                psu_pos = pos
                break
        
        # Get text AROUND the PSU keyword (100 chars before and after)
        # Use normalized_for_brand (with typo fixes) for consistency
        if psu_pos != -1:
            start = max(0, psu_pos - 50)
            end = min(len(normalized_for_brand), psu_pos + 100)
            psu_context = normalized_for_brand[start:end]
        else:
            psu_context = normalized_for_brand
        
        # Check if brand is in PSU context
        has_brand_in_title = False
        if psu_brand == 'cooler master' and ('cooler master' in psu_context or 'coolermaster' in psu_context):
            has_brand_in_title = True
        elif psu_brand == 'be quiet' and ('be quiet' in psu_context or 'bequiet' in psu_context):
            has_brand_in_title = True
        elif psu_brand == 'super flower' and ('super flower' in psu_context or 'superflower' in psu_context):
            has_brand_in_title = True
        elif psu_brand == 'xfx' and 'xfx' in psu_context:
            has_brand_in_title = True
        elif psu_brand == 'chieftec' and ('chieftec' in psu_context or 'chieftek' in psu_context):
            has_brand_in_title = True
        elif psu_brand == 'xilence' and 'xilence' in psu_context:
            has_brand_in_title = True
        elif psu_brand == 'kolink' and 'kolink' in psu_context:
            has_brand_in_title = True
        elif psu_brand and psu_brand in psu_context:
            has_brand_in_title = True
        
        # Check for exact brand+model match in PSU context (high priority)
        # e.g., "Barošanas bloks:XILENCE 600W" should match Xilence PSU
        psu_brand_lower = psu_brand.lower() if psu_brand else ""
        if psu_brand_lower and psu_brand_lower in psu_context:
            # Give massive bonus for brand appearing in PSU section
            score += 100
            method += "+brand_in_psu_section"
            has_brand_in_title = True
        elif psu_brand_lower and psu_brand_lower in normalized_title:
            # Brand in title but not PSU context
            score += 10
            method += "+brand_in_title"
        
        # Extract model number from PSU name (e.g., "cx600" from "Corsair CX600", "xtr750" from "XFX XTR")
        psu_model_num = None
        model_match = re.search(r'(cx|rm|tx|sf|ax|hx|vs|cv|system power|pure power|dark power|xtr)\s*(\d{3,4})', psu_name, re.IGNORECASE)
        if model_match:
            psu_model_num = (model_match.group(1).lower(), model_match.group(2))
        
        # Check for exact model number match in title (e.g., "cx600" in "corsair cx600")
        if psu_model_num:
            series, wattage = psu_model_num
            # Look for pattern like "cx600" or "cx 600" or "cx750m" in title
            model_patterns = [
                rf'{series}\s*{wattage}[m]?\b',  # cx600, cx 600, cx750m
                rf'{series}\s*{wattage}[m]?w\b',  # cx600w, cx 600w, cx750mw
            ]
            for pattern in model_patterns:
                if re.search(pattern, normalized_title, re.IGNORECASE):
                    # Found exact model match
                    if title_wattage and title_wattage == wattage:
                        # Wattage came from the model number itself - high score!
                        score = 150.0
                        method = f"exact_model_{series}{wattage}"
                        return score, method
                    elif title_wattage and title_wattage != wattage:
                        score = 70.0
                        method = f"model_match_wattage_conflict"
                    else:
                        score = 150.0
                        method = f"exact_model_{series}{wattage}"
                    return score, method
        
        # Special handling for XFX XTR series (e.g., "xtr750")
        if 'xfx' in normalized_title and 'xtr' in normalized_title:
            if 'xfx' in psu_name_lower and 'xtr' in psu_name_lower:
                # Strong bonus for XFX XTR match
                score += 60
                method += "+xfx_xtr_series"
                
                # Extract wattage from title (e.g., "xtr750" -> 750)
                xtr_wattage_match = re.search(r'xtr(\d{3,4})', normalized_title, re.IGNORECASE)
                if xtr_wattage_match:
                    title_xtr_wattage = xtr_wattage_match.group(1)
                    if psu_wattage and psu_wattage == title_xtr_wattage:
                        score += 40  # Extra bonus for wattage match
                        method += "+xtr_wattage_match"
                        return score, method
                return score, method
        
        # Make sure we don't match XFX XT when text has XFX XTR
        if 'xfx' in normalized_title and 'xtr' in normalized_title:
            # Text mentions XFX XTR specifically
            if 'xfx' in psu_name_lower and 'xt' in psu_name_lower and 'xtr' not in psu_name_lower:
                # This is an XT series PSU but text mentions XTR - skip
                score = 0
                method = "xt_vs_xtr_mismatch"
                return score, method
        
        # Check for generic "Corsair 650W" or "Corsair 750W" patterns
        generic_match = re.search(r'corsair\s+(\d{3,4})w', normalized_title, re.IGNORECASE)
        if generic_match:
            generic_wattage = generic_match.group(1)
            if psu_wattage and psu_wattage == generic_wattage:
                score = 75.0
                method = f"generic_corsair_{generic_wattage}w"
                if psu_name.startswith('corsair'):
                    score += 10
                    method += "+brand_match"
                return score, method
        
        # Special handling for Chieftec SILICON series when wattage matches
        # This handles listings with "CHIEFTEK 650W" where we want to match SILICON specifically
        if 'chieftec' in psu_name_lower and 'silicon' in psu_name_lower:
            # Check if title has chieftek/chieftec + matching wattage
            has_chieftek = 'chieftek' in normalized_for_brand or 'chieftec' in normalized_for_brand
            if has_chieftek and title_wattage:
                if psu_wattage == title_wattage:
                    # Exact match: Chieftec SILICON with correct wattage
                    score = 130.0  # High score but below exact_model
                    method = "chieftec_silicon_wattage_match"
                    return score, method
        
        # Exact name match - but check wattage conflict and PSU context first
        if (psu_name in normalized_title or psu_name in normalized_for_brand or 
            psu_name_fixed in normalized_title or psu_name_fixed in normalized_for_brand):
            if title_wattage and psu_wattage and title_wattage != psu_wattage:
                score = 50.0
                method = "partial_name_wattage_mismatch"
            elif not has_brand_in_title:
                # Name matches but brand is not in PSU context
                score = 40.0
                method = "exact_name_wrong_context"
            else:
                score = 100.0
                method = "exact"
        else:
            score = fuzz.token_set_ratio(normalized_title, psu_name)
            method = "fuzzy"
        
        # If we have wattage in title, boost score for matching wattage
        if title_wattage and psu_wattage:
            title_watt_int = int(title_wattage)
            psu_watt_int = int(psu_wattage)
            wattage_diff = abs(title_watt_int - psu_watt_int)
            
            if wattage_diff == 0:
                score += 40
                method += "+wattage_match"
            elif wattage_diff <= 50:
                score += 25 - wattage_diff
                method += "+wattage_tolerance"
            else:
                score -= 60
                method += "+wattage_mismatch"
        elif title_wattage and not psu_wattage:
            score += 10
            method += "+wattage_mentioned"
        
        # Check if PSU is mentioned at all
        psu_keywords = ['psu', 'barosana', 'barošana', 'block', 'bloks', 'barošanas', 
                        'powersupply', 'power supply', 'blok', 'barošana']
        has_psu_mention = any(kw in normalized_title for kw in psu_keywords)
        if not has_psu_mention and not title_wattage:
            return 0, "no_psu_in_text"
        
        # Model part matching - check for series names in PSU context
        model_parts = psu_name.split()
        for part in model_parts:
            if len(part) >= 3 and part in psu_context:
                score += 10
                method += "+model_part"
                break
        
        # Penalize if brand is NOT in PSU context but IS elsewhere in the text
        if psu_brand and psu_brand in normalized_title and not has_brand_in_title:
            score -= 40
            method += "+brand_misplaced"
        
        # Special bonus for series matches
        if 'system power' in normalized_title and 'system power' in psu_name:
            score += 20
            method += "+system_power"
        
        if 'pure power' in normalized_title and 'pure power' in psu_name:
            score += 20
            method += "+pure_power"
        
        if 'dark power' in normalized_title and 'dark power' in psu_name:
            score += 20
            method += "+dark_power"
        
        if 'cooler master' in normalized_title and 'masterwatt' in normalized_title:
            if 'cooler master' in psu_name and 'masterwatt' in psu_name:
                score += 50
                method += "+coolermaster_masterwatt"
        
        return score, method
    
    def _extract_wattage(self, text: str) -> Optional[str]:
        """Extract wattage (e.g., 300W, 650W, CX750) from text."""
        patterns = [
            r'\b(\d{3,4})\s*w\b',
            r'\b(\d{3,4})w\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        model_wattage_patterns = [
            r'\b(?:cx|rm|tx|sf|ax|hx|vs|cv)\s*(\d{3,4})\b',
            r'\bevga\s*(?:g[+-]?\s*)?(\d{3,4})\b',
            r'\bsupernova\s*(?:g[+-]?\s*)?(\d{3,4})\b',
            r'\bfocus\s*(?:gx|px|sx)?\s*-?\s*(\d{3,4})\b',
            r'\bprime\s*(?:tx|px|gx)?\s*-?\s*(\d{3,4})\b',
            r'\b(?:toughpower|thoughpower)\s*(?:gf|gx)?\s*(?:\d+)?\s*-?\s*(\d{3,4})\b',
            r'\b(?:system|pure|dark)\s*power\s*(?:\d+)?\s*-?\s*(\d{3,4})\b',
            r'\bocz\d*(\d{3,4})\w*',
        ]
        for pattern in model_wattage_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                logger.debug(f"Extracted wattage {match.group(1)} from PSU model pattern")
                return match.group(1)
        
        return None
    
    def _extract_psu_tokens(self, title: str) -> List[str]:
        """Extract PSU-specific tokens."""
        tokens = set()
        normalized = normalize_text(title)
        
        brand_patterns = [
            r'\bcorsair\b', r'\bevga\b', r'\bseasonic\b', r'\bthermaltake\b',
            r'\bbe\s*quiet!?\b', r'\bbequiet!?\b', r'\bcooler\s*master\b',
            r'\bcoolermaster\b', r'\bmsi\b', r'\basus\b', r'\bgigabyte\b',
            r'\bphanteks\b', r'\bfractal\b', r'\bsuper\s*flower\b',
            r'\bsuperflower\b', r'\bsilverstone\b', r'\bdeepcool\b',
            r'\bnzxt\b', r'\bantec\b', r'\benermax\b', r'\bfsp\b',
            r'\bchieftec\b', r'\bchieftek\b', r'\bxilence\b', r'\bkolink\b', r'\bsharkoon\b',
            r'\bthoughpower\b', r'\bocz\b', r'\bxfx\b',
        ]
        
        for pattern in brand_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            for match in matches:
                match_lower = match.lower()
                if 'bequiet' in match_lower or 'be quiet' in match_lower:
                    tokens.add('be quiet')
                elif 'coolermaster' in match_lower or 'cooler master' in match_lower:
                    tokens.add('cooler master')
                elif 'chieftec' in match_lower or 'chieftek' in match_lower:
                    tokens.add('chieftec')  # Normalize both spellings to chieftec
                elif 'superflower' in match_lower or 'super flower' in match_lower:
                    tokens.add('super flower')
                elif 'thoughpower' in match_lower:
                    tokens.add('toughpower')
                elif 'xfx' in match_lower:
                    tokens.add('xfx')
                else:
                    tokens.add(match_lower)
        
        return list(tokens)
