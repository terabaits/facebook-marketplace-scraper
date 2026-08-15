"""Motherboard matching engine using rapidfuzz."""
import re
from typing import Optional, List, Tuple, Dict
from rapidfuzz import fuzz, process

from src.models.schemas import MotherboardReference, MotherboardMatchResult
from src.utils.text import normalize_text
from src.utils.logger import get_logger

logger = get_logger("motherboard_matcher")


class MotherboardMatcher:
    """Matches scraped motherboard listings to motherboard reference database."""
    
    def __init__(self, motherboard_list: List[MotherboardReference]):
        """Initialize with motherboard reference list."""
        self.motherboards = motherboard_list
        self._build_index()
        logger.info(f"MotherboardMatcher initialized with {len(motherboard_list)} motherboards")
    
    def _build_index(self):
        """Build search index from motherboard references."""
        self.brand_model_names: Dict[str, MotherboardReference] = {}  # brand+model only
        self.keyword_to_mbs: Dict[str, List[MotherboardReference]] = {}  # keywords -> list of MBs
        self.all_names = []
        
        for mb in self.motherboards:
            # Primary name: Brand + Model (for exact matching)
            norm = normalize_text(f"{mb.brand} {mb.model}")
            self.all_names.append(norm)
            self.brand_model_names[norm] = mb
            
            # Also add brand + model without common prefixes (like GA- for Gigabyte, MS- for MSI)
            model_clean = mb.model
            for prefix in ['GA-', 'MS-', 'PRIME ', 'TUF ', 'ROG ']:
                if model_clean.startswith(prefix):
                    model_clean = model_clean[len(prefix):]
                    norm_clean = normalize_text(f"{mb.brand} {model_clean}")
                    self.all_names.append(norm_clean)
                    self.brand_model_names[norm_clean] = mb
                    break
            
            # Also add variants without hyphens (e.g., "b450-plus" -> "b450plus")
            # This handles cases where sellers write "B450PLUS" or "B450Plus"
            model_no_hyphens = mb.model.replace('-', '').replace(' ', '')
            norm_no_hyphens = normalize_text(f"{mb.brand} {model_no_hyphens}")
            if norm_no_hyphens not in self.brand_model_names:
                self.all_names.append(norm_no_hyphens)
                self.brand_model_names[norm_no_hyphens] = mb
            
            # Also add model-only variant without prefix
            for prefix in ['GA-', 'MS-']:
                if mb.model.startswith(prefix):
                    model_no_prefix = mb.model[len(prefix):]
                    norm_no_prefix = normalize_text(f"{mb.brand} {model_no_prefix}")
                    if norm_no_prefix not in self.brand_model_names:
                        self.all_names.append(norm_no_prefix)
                        self.brand_model_names[norm_no_prefix] = mb
                    # Also add model-only alias (no brand) for listings that omit the brand.
                    # Exact match on model-only is only used within motherboard context.
                    norm_model_only = normalize_text(model_no_prefix)
                    if norm_model_only not in self.brand_model_names and len(norm_model_only) >= 4:
                        self.all_names.append(norm_model_only)
                        self.brand_model_names[norm_model_only] = mb
            
            # Keywords (for scoring, not exact matching)
            for kw in mb.search_keywords:
                kw_norm = normalize_text(kw)
                if kw_norm not in self.keyword_to_mbs:
                    self.keyword_to_mbs[kw_norm] = []
                self.keyword_to_mbs[kw_norm].append(mb)
                if kw_norm not in self.all_names:
                    self.all_names.append(kw_norm)
    
    def _extract_motherboard_tokens(self, text: str) -> List[str]:
        """Extract motherboard-specific tokens."""
        tokens = set()
        normalized = normalize_text(text)
        
        # Common motherboard patterns
        chipset_patterns = [
            r'\bb450\b', r'\bb550\b', r'\bx570\b', r'\ba520\b',
            r'\bh470\b', r'\bh570\b', r'\bz490\b', r'\bz590\b',
            r'\bh610\b', r'\bb660\b', r'\bz690\b', r'\bz790\b',
        ]
        
        for pattern in chipset_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            tokens.update(matches)
        
        # Brand patterns
        brand_patterns = [
            r'\basus\b', r'\bmsi\b', r'\bgigabyte\b', r'\basrock\b',
            r'\bprime\b', r'\btuf\b', r'\brog\b', r'\bproart\b',
            r'\bmag\b', r'\bmpg\b', r'\bmeg\b', r'\bmortar\b',
            r'\baorus\b', r'\bvision\b', r'\bdesignare\b',
            r'\bextreme\b', r'\bphantom\b', r'\bpro\b',
        ]
        
        for pattern in brand_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            tokens.update(matches)
        
        # Form factor
        if 'micro atx' in normalized or 'matx' in normalized:
            tokens.add('matx')
        if 'atx' in normalized:
            tokens.add('atx')
        if 'mini itx' in normalized or 'mitx' in normalized:
            tokens.add('mitx')
        
        return list(tokens)
    
    def _score_motherboard_match(self, mb: MotherboardReference, normalized_title: str) -> Tuple[float, str]:
        """Score how well a motherboard matches the listing."""
        score = 0.0
        method = ""
        
        # Build reference name
        mb_name = normalize_text(f"{mb.brand} {mb.model}")
        
        # Check for exact name match
        if mb_name in normalized_title:
            score = 100.0
            method = "exact"
        else:
            # Fuzzy match
            score = fuzz.token_set_ratio(normalized_title, mb_name)
            method = "fuzzy"
        
        # Chipset match bonus (HUGE bonus - chipset is very specific)
        if mb.chipset and mb.chipset.lower() in normalized_title:
            score += 30  # Increased from 10
            method += "+chipset"
        elif mb.chipset:
            # Check if a DIFFERENT chipset is mentioned - penalize heavily
            chipset_pattern = r'\b(b450|b550|x570|a520|h470|h570|z490|z590|h610|b660|z690|z790|b350|x370|b450m|b350m)\b'
            mentioned_chipsets = re.findall(chipset_pattern, normalized_title, re.IGNORECASE)
            if mentioned_chipsets:
                # A chipset is mentioned but it's not ours - check if it matches
                mb_chipset_lower = mb.chipset.lower()
                if not any(c.lower() == mb_chipset_lower for c in mentioned_chipsets):
                    # Wrong chipset mentioned - heavy penalty
                    score -= 50
                    method += "+wrong_chipset"
        
        # Socket match bonus
        if mb.socket and mb.socket.lower() in normalized_title:
            score += 10
            method += "+socket"
        
        # Model parts match - require chipset to match for generic models like "Gaming"
        model_parts = mb.model.lower().split()
        model_part_found = False
        for part in model_parts:
            if len(part) >= 3 and part in normalized_title:
                # For generic model names like "Gaming", "Pro", require chipset match
                if part.lower() in ['gaming', 'pro', 'prime', 'plus', 'ultra']:
                    if mb.chipset and mb.chipset.lower() in normalized_title:
                        score += 5
                        method += "+model_part"
                        model_part_found = True
                        break
                else:
                    score += 5
                    method += "+model_part"
                    model_part_found = True
                    break
        
        # NEW: Special bonus for compound MSI model names
        # e.g., "GAMING PLUS MAX" should be stronger than just "PLUS" or "GAMING" separately
        if mb.brand.lower() == 'msi':
            model_lower = mb.model.lower()
            # Check for compound model patterns
            if 'gaming plus max' in model_lower and 'gaming' in normalized_title and 'plus' in normalized_title and 'max' in normalized_title:
                score += 25  # Strong bonus for full compound match
                method += "+msi_gaming_plus_max"
            elif 'tomahawk max' in model_lower and 'tomahawk' in normalized_title and 'max' in normalized_title:
                score += 25  # Strong bonus for TOMAHAWK MAX
                method += "+msi_tomahawk_max"
            elif 'gaming plus' in model_lower and 'gaming' in normalized_title and 'plus' in normalized_title:
                score += 20  # Medium bonus for GAMING PLUS
                method += "+msi_gaming_plus"
            elif 'tomahawk' in model_lower and 'tomahawk' in normalized_title:
                score += 15  # Standard bonus for TOMAHAWK
                method += "+msi_tomahawk"
        
        return score, method  # Return raw score for comparison, cap later
    
    def match_listing(self, full_text: str) -> MotherboardMatchResult:
        """Match a listing to a motherboard reference."""
        normalized = normalize_text(full_text)
        
        # Get motherboard context - look in lines mentioning motherboard keywords
        # AND lines with MSI/Gigabyte/ASUS/ASRock brand names
        lines = full_text.lower().split('\n')
        mb_context_lines = []
        
        for i, line in enumerate(lines):
            # Check if this line has motherboard keywords
            has_mb_kw = any(kw in line for kw in ['motherboard', 'pamat plate', 'mātesplate', 'mb:', 'mainboard'])
            # Check if this line has brand names (often followed by model)
            has_brand = any(brand in line for brand in ['msi', 'gigabyte', 'asus', 'asrock', 'asrock'])
            if has_mb_kw or has_brand:
                # Include this line and nearby lines (2 before, 2 after) for context
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    if lines[j] not in mb_context_lines:
                        mb_context_lines.append(lines[j])
        
        mb_context = ' '.join(mb_context_lines) if mb_context_lines else normalized
        mb_context = normalize_text(mb_context)  # Normalize to remove hyphens
        
        # Check for generic motherboard references that shouldn't match specific models
        # e.g., "Asus All Series" is a generic placeholder, not a specific model
        generic_patterns = [
            r'\ball\s+series\b',  # "All Series" is generic
            r'\bgeneric\s+motherboard\b',
            r'\bstandard\s+mb\b',
            r'\bdefault\s+board\b',
        ]
        for pattern in generic_patterns:
            if re.search(pattern, full_text.lower()):
                logger.debug(f"Generic motherboard reference found, skipping specific matching")
                return MotherboardMatchResult()
        
        # Extract tokens from full text (for chipset/socket matching)
        tokens = self._extract_motherboard_tokens(full_text)
        
        # Try exact matches first (full brand + model only) - but only in MB context
        # Sort by length (descending) so "gigabyte h510m h" matches before "gigabyte h"
        sorted_names = sorted(self.brand_model_names.items(), key=lambda x: len(x[0]), reverse=True)
        for name, mb in sorted_names:
            if name in mb_context:  # Use mb_context instead of normalized
                method = "exact"
                # If this is a model-only match (no brand in the alias), require motherboard context
                if ' ' not in name.strip():
                    method = "exact_model_only"
                return MotherboardMatchResult(
                    motherboard=mb,
                    confidence=1.0,
                    method=method
                )
        
        # Score all motherboards and find best - but only those with brand in MB context
        best_score = 0.0
        best_mb = None
        best_method = "none"
        
        for mb in self.motherboards:
            # Skip if brand not mentioned in motherboard context
            brand_in_mb_context = mb.brand.lower() in mb_context
            
            # NEW: Infer brand from chipset+model patterns for MSI
            # e.g., "B450 GAMING PLUS MAX" is always an MSI board
            if not brand_in_mb_context and mb.brand.lower() == 'msi':
                if mb.chipset and mb.chipset.lower() in mb_context:
                    chipset_pos = mb_context.find(mb.chipset.lower())
                    after_chipset = mb_context[chipset_pos:chipset_pos + 100] if chipset_pos >= 0 else ""
                    # If chipset is followed by gaming keywords, likely MSI
                    if 'gaming' in after_chipset or 'tomahawk' in after_chipset or 'max' in after_chipset:
                        brand_in_mb_context = True
            
            # Also allow if specific model keywords are in MB context
            # Special handling for version numbers like "2.0" in "H310M S2H 2.0"
            model_in_mb_context = False
            model_lower = mb.model.lower()
            for part in model_lower.split():
                if len(part) >= 3 and part in mb_context:
                    model_in_mb_context = True
                    break

            # Fallback: model without common vendor prefix (e.g., Gigabyte "GA-AX370-Gaming 3"
            # often listed as "AX370-Gaming 3"). Only valid within motherboard context.
            if not model_in_mb_context and mb.brand.lower() in ['gigabyte', 'msi', 'asus', 'asrock']:
                prefixless = re.sub(r'^(ga-|ms-|tuf |rog |prime |pro )', '', model_lower).replace('-', '')
                if prefixless != model_lower.replace('-', '') and prefixless in mb_context:
                    model_in_mb_context = True
            # Check for version pattern like "2.0" at end of model
            if not model_in_mb_context and re.search(r'\.\d$', model_lower):
                # Model ends with version like "2.0" - check if base model is in context
                base_model = re.sub(r'\.\d$', '', model_lower).strip()
                if base_model and base_model in mb_context:
                    model_in_mb_context = True
            
            # Only consider if brand or model is in MB context
            if not (brand_in_mb_context or model_in_mb_context):
                continue
            
            score, method = self._score_motherboard_match(mb, mb_context)
            
            # Tiebreaker: prefer motherboards with model_part in text
            if score == best_score and score > 0:
                # Check if current best has model_part
                current_has_model = False
                new_has_model = False
                
                for part in mb.model.lower().split():
                    if len(part) >= 3 and part in mb_context:
                        if part.lower() not in ['gaming', 'pro', 'prime', 'plus', 'ultra'] or (mb.chipset and mb.chipset.lower() in mb_context):
                            new_has_model = True
                            break
                
                if best_mb:
                    for part in best_mb.model.lower().split():
                        if len(part) >= 3 and part in mb_context:
                            if part.lower() not in ['gaming', 'pro', 'prime', 'plus', 'ultra'] or (best_mb.chipset and best_mb.chipset.lower() in mb_context):
                                current_has_model = True
                                break
                
                if new_has_model and not current_has_model:
                    best_mb = mb
                    best_method = method
            elif score > best_score:
                best_score = score
                best_mb = mb
                best_method = method
        
        if best_mb and best_score >= 75:
            # Cap confidence at 1.0
            confidence = min(best_score / 100.0, 1.0)
            return MotherboardMatchResult(
                motherboard=best_mb,
                confidence=confidence,
                method=best_method or "fuzzy"
            )
        
        return MotherboardMatchResult()
