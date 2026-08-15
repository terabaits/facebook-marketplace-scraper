"""Console matching engine for game consoles."""
import re
from typing import Optional, List, Tuple
from rapidfuzz import fuzz, process

from src.models.schemas import ConsoleReference, ConsoleVariant, ConsoleEdition, ConsoleMatchResult
from src.utils.text import normalize_text
from src.utils.logger import get_logger

logger = get_logger("console_matcher")


class ConsoleMatcher:
    """Matches scraped listing titles to console reference database.
    
    Strategy:
    1. Console matching - identify base console (PS3, Xbox 360, Switch, etc.)
    2. Variant matching - identify specific model (Slim, Pro, etc.)
    3. Edition matching - identify special editions (bundle packs, etc.)
    """
    
    def __init__(self, consoles: List[ConsoleReference], 
                 variants: List[ConsoleVariant],
                 editions: List[ConsoleEdition]):
        self.consoles = consoles
        self.variants = variants
        self.editions = editions
        
        # Build lookup indexes
        self.name_to_console = {}
        self.variants_by_console = {}
        self.editions_by_console = {}
        
        for console in consoles:
            norm_name = normalize_text(console.name)
            self.name_to_console[norm_name] = console
        
        for variant in variants:
            if variant.console_id not in self.variants_by_console:
                self.variants_by_console[variant.console_id] = []
            self.variants_by_console[variant.console_id].append(variant)
        
        for edition in editions:
            if edition.console_id not in self.editions_by_console:
                self.editions_by_console[edition.console_id] = []
            self.editions_by_console[edition.console_id].append(edition)
        
        logger.info(f"ConsoleMatcher initialized with {len(consoles)} consoles, {len(variants)} variants, {len(editions)} editions")
    
    def match(self, title: str, description: str = "", price: float = 0.0) -> ConsoleMatchResult:
        """Match listing text to best console reference.
        
        Args:
            title: Listing title
            description: Listing description
            price: Listing price in EUR (for default model selection)
        
        Returns ConsoleMatchResult with matched console, variant, and edition
        """
        full_text = f"{title} {description}".strip()
        if not full_text:
            return ConsoleMatchResult()
        
        normalized_title = normalize_text(title)
        normalized_full = normalize_text(full_text)
        
        # Step 1: Match console - prioritize title matches
        console_match, console_confidence = self._match_console(normalized_title, title)
        
        # Check if title match is generic (e.g., just "nintendo" vs "nintendo switch")
        # If so, also check full text for more specific match
        title_is_generic = False
        if console_match:
            console_norm = normalize_text(console_match.name)
            # Generic if matched console name has more words than the pattern
            # e.g., title matched "nintendo" but console is "nintendo gamecube"
            title_pattern = ''
            for ck, patterns in [
                ('nintendo', ['nintendo']),
                ('playstation', ['playstation']),
                ('xbox', ['xbox']),
            ]:
                for p in patterns:
                    if p in normalized_title:
                        title_pattern = ck
                        break
            
            if title_pattern:
                # If console name starts with pattern but has additional words, it's generic
                title_is_generic = console_norm.startswith(title_pattern + ' ')
        
        # If no confident match from title, OR title match is generic, try full text
        if not console_match or console_confidence < 0.7 or title_is_generic:
            console_match_full, console_confidence_full = self._match_console(normalized_full, full_text)
            if console_match_full:
                # Prefer full text match if it's more specific
                full_norm = normalize_text(console_match_full.name)
                full_is_generic = full_norm == 'nintendo'
                
                if not console_match:
                    # No title match, use full text
                    console_match = console_match_full
                    console_confidence = console_confidence_full * 0.9
                elif title_is_generic and not full_is_generic:
                    # Title is generic but full text is specific - prefer full text
                    console_match = console_match_full
                    console_confidence = console_confidence_full * 0.95
                elif console_confidence_full > console_confidence + 0.1:
                    # Full text has significantly better confidence
                    console_match = console_match_full
                    console_confidence = console_confidence_full * 0.9
        
        if not console_match:
            # Try fallback matching for common patterns
            console_match, console_confidence = self._fallback_console_match(normalized_title)
            if not console_match:
                console_match, console_confidence = self._fallback_console_match(normalized_full)
            if not console_match:
                return ConsoleMatchResult(confidence=0.0, method="none")
        
        # Step 2: Match variant (if console matched)
        variant_match = None
        variant_confidence = 0.0
        if console_match:
            # Try title first for variant matching
            variant_match, variant_confidence = self._match_variant(
                normalized_title, title, console_match.id
            )
            
            # If no variant from title, try full text
            if not variant_match:
                variant_match, variant_confidence = self._match_variant(
                    normalized_full, full_text, console_match.id
                )
        
        # Step 3: Match edition
        edition_match = None
        edition_confidence = 0.0
        if console_match:
            # Try title first
            edition_match, edition_confidence = self._match_edition(
                normalized_title, title, console_match.id
            )
            if not edition_match:
                edition_match, edition_confidence = self._match_edition(
                    normalized_full, full_text, console_match.id
                )
        
        # Determine method
        if variant_match and edition_match:
            method = "console+variant+edition"
        elif variant_match:
            method = "console+variant"
        elif edition_match:
            method = "console+edition"
        else:
            method = "console_only"
        
        return ConsoleMatchResult(
            console=console_match,
            variant=variant_match,
            edition=edition_match,
            console_confidence=console_confidence,
            variant_confidence=variant_confidence,
            edition_confidence=edition_confidence,
            method=method
        )
    
    def _match_console(self, normalized: str, full_text: str) -> Tuple[Optional[ConsoleReference], float]:
        """Match base console."""
        candidates = []
        seen = set()
        
        text_lower = normalized.lower()
        
        # Priority matching - check for most specific matches first (longer patterns before shorter)
        console_priority_patterns = [
            # PlayStation Portable (check before base PlayStation)
            ('playstation portable street', ['psp street', 'playstation portable street']),
            ('playstation portable', ['psp', 'playstation portable']),
            # PSP Go (check before base PSP)
            ('psp go', ['psp go', 'playstation portable go']),
            # PlayStation Vita (check before base PlayStation)
            ('playstation vita', ['ps vita', 'playstation vita', 'vita']),
            # PlayStation specific models (with typo tolerance)
            ('playstation 5 pro', ['ps5 pro', 'playstation 5 pro', 'playstation5 pro', 'playstaion 5 pro']),
            ('playstation 5 slim', ['ps5 slim', 'playstation 5 slim', 'playstation5 slim', 'playstaion 5 slim']),
            ('playstation 5', ['ps5', 'playstation 5', 'playstation5', 'playstaion 5']),
            ('playstation 4 pro', ['ps4 pro', 'playstation 4 pro', 'playstation4 pro', 'playstaion 4 pro']),
            ('playstation 4 slim', ['ps4 slim', 'playstation 4 slim', 'playstation4 slim', 'playstaion 4 slim']),
            ('playstation 4', ['ps4', 'playstation 4', 'playstation4', 'playstaion 4']),
            ('playstation 3 super slim', ['ps3 super slim', 'playstation 3 super slim']),
            ('playstation 3 slim', ['ps3 slim', 'playstation 3 slim']),
            ('playstation 3', ['ps3', 'playstation 3', 'playstation3']),
            ('playstation 2 slimline', ['ps2 slim', 'playstation 2 slimline']),
            ('playstation 2', ['ps2', 'playstation 2', 'playstation2']),
            ('playstation portal', ['playstation portal', 'ps portal']),
            # PlayStation VR (check before base PlayStation)
            ('playstation vr2', ['psvr2', 'playstation vr2', 'ps vr2', 'vr2']),
            ('playstation vr', ['psvr', 'playstation vr', 'ps vr']),
            # PlayStation generic (check last)
            ('playstation', ['playstation', 'ps1', 'ps one']),
            # Xbox variants
            ('xbox series x', ['xbox series x', 'xbox seriesx', 'series x']),
            ('xbox series s', ['xbox series s', 'xbox seriess', 'series s']),
            ('xbox one x', ['xbox one x', 'xbox onex']),
            ('xbox one s all digital', ['xbox one s all digital', 'xbox one s digital', 'xbox one all digital']),
            ('xbox one s', ['xbox ones']),
            ('xbox one', ['xbox one', 'xboxone']),
            ('xbox 360', ['xbox 360', 'xbox360', '360']),
            ('xbox', ['xbox', 'original xbox']),
            # Steam Deck (check before generic 'steam' or 'deck')
            ('steam deck', ['steam deck', 'steamdeck']),
            # Meta Quest (check before generic 'quest')
            ('meta quest pro', ['meta quest pro', 'quest pro', 'metaquest pro']),
            ('meta quest 3s', ['meta quest 3s', 'quest 3s', 'metaquest 3s']),
            ('meta quest 3', ['meta quest 3', 'quest 3', 'metaquest 3']),
            ('meta quest 2', ['meta quest 2', 'quest 2', 'oculus quest 2', 'metaquest 2', 'metaquest-2', 'metaquest2']),
            ('meta quest', ['meta quest', 'oculus quest', 'metaquest']),
            # Nintendo variants
            ('nintendo switch 2', ['switch 2', 'nintendo switch 2', 'switch2']),
            ('nintendo switch oled', ['switch oled', 'nintendo switch oled']),
            ('nintendo switch lite', ['switch lite', 'nintendo switch lite']),
            ('nintendo switch', ['switch', 'nintendo switch']),
            ('wii u', ['wii u']),
            ('wii', ['wii']),
            ('nintendo gamecube', ['gamecube', 'nintendo gamecube', 'ngc']),
            ('nintendo wii u', ['wii u', 'nintendo wii u']),
            ('nintendo wii', ['wii', 'nintendo wii']),
            ('nintendo 3ds', ['3ds', 'nintendo 3ds']),
            ('nintendo 2ds', ['2ds', 'nintendo 2ds']),
            ('nintendo ds', ['ds', 'nintendo ds']),
            # Generic Nintendo fallback
            ('nintendo', ['nintendo']),
        ]
        
        # Check patterns in order, with word boundary matching for shorter patterns
        for console_key, patterns in console_priority_patterns:
            for pattern in patterns:
                # For multi-word patterns, check as substring
                # For single-word patterns, use word boundaries
                if ' ' in pattern:
                    # Multi-word pattern - check as substring (more flexible)
                    found = pattern in text_lower
                elif len(pattern) < 10:
                    # Short single-word pattern - use word boundaries
                    if re.search(rf'\b{re.escape(pattern)}\b', text_lower):
                        found = True
                    else:
                        found = False
                else:
                    # Longer patterns can match as substring
                    found = pattern in text_lower
                
                if found:
                    for console in self.consoles:
                        if console.id not in seen:
                            console_norm = normalize_text(console.name)
                            # Special case: PSP defaults to 2000 if no specific model mentioned
                            if pattern == 'psp' and console_key == 'playstation portable':
                                # Find PSP 2000 specifically
                                for c in self.consoles:
                                    if 'playstation portable 2000' in normalize_text(c.name):
                                        candidates.append((c, 0.90))
                                        seen.add(c.id)
                                        break
                                break
                            elif console_key == console_norm or console_norm.startswith(console_key + ' '):
                                # console_key matches exactly or is prefix of console_norm
                                confidence = 0.95 if console_key == console_norm else 0.90
                                candidates.append((console, confidence))
                                seen.add(console.id)
                                break
        
        # Sort by confidence (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            return candidates[0]
        return None, 0.0
    
    def _fallback_console_match(self, normalized: str) -> Tuple[Optional[ConsoleReference], float]:
        """Fallback matching for when standard matching fails."""
        text_lower = normalized.lower()
        
        # Check for partial matches
        if 'ps3' in text_lower or 'ps 3' in text_lower:
            for c in self.consoles:
                if 'playstation 3' in normalize_text(c.name):
                    return c, 0.70
        
        if 'ps4' in text_lower or 'ps 4' in text_lower:
            for c in self.consoles:
                if 'playstation 4' in normalize_text(c.name):
                    return c, 0.70
        
        if 'xbox' in text_lower:
            if '360' in text_lower:
                for c in self.consoles:
                    if 'xbox 360' in normalize_text(c.name):
                        return c, 0.70
            elif 'one' in text_lower:
                for c in self.consoles:
                    if 'xbox one' in normalize_text(c.name):
                        return c, 0.70
            else:
                for c in self.consoles:
                    if normalize_text(c.name) == 'xbox':
                        return c, 0.70
        
        return None, 0.0
    
    def _match_variant(self, normalized: str, full_text: str, console_id: int) -> Tuple[Optional[ConsoleVariant], float]:
        """Match console variant."""
        variants = self.variants_by_console.get(console_id, [])
        if not variants:
            return None, 0.0
        
        candidates = []
        seen = set()
        
        text_lower = normalized.lower()
        
        for variant in variants:
            if variant.id in seen:
                continue
            
            variant_norm = normalize_text(variant.model_name)
            
            # Check for model number patterns
            # PS3: CECH-XXXX
            if 'cech' in variant_norm:
                if re.search(r'cech[\s-]?\w+', text_lower):
                    model_match = re.search(r'cech[\s-]?(\w+)', text_lower)
                    if model_match:
                        model_code = model_match.group(1).lower()
                        variant_cech_match = re.search(r'cech([a-z]+)', variant_norm)
                        if variant_cech_match:
                            variant_pattern = variant_cech_match.group(1).lower()
                            variant_base = variant_pattern.replace('xx', '')
                            if model_code.startswith(variant_base):
                                candidates.append((variant, 0.95))
                                seen.add(variant.id)
                                continue
            
            # Xbox 360: Arcade, Pro, Elite, S, E
            if 'xbox 360' in variant_norm:
                if 'arcade' in text_lower and 'arcade' in variant_norm:
                    candidates.append((variant, 0.90))
                    seen.add(variant.id)
                    continue
                if 'elite' in text_lower and 'elite' in variant_norm:
                    candidates.append((variant, 0.90))
                    seen.add(variant.id)
                    continue
                # Check for 'E' model - must be "360 e" pattern in text AND variant ends with " e"
                # Make sure it's not Elite by checking variant ends with just " e" not " elite"
                if re.search(r'360\s+e\b', text_lower):
                    # Check variant is specifically the E model: ends with " e" and NOT "elite"
                    if variant_norm.endswith(' e') and not variant_norm.endswith('elite'):
                        candidates.append((variant, 0.95))
                        seen.add(variant.id)
                        continue
                # Check for 'S' model in Xbox 360 - must have "360" before the 's'
                if re.search(r'360\s+s\b', text_lower):
                    if 's' in variant_norm and 'slim' not in variant_norm:
                        candidates.append((variant, 0.85))
                        seen.add(variant.id)
                        continue
            
            # PS5: Slim Digital, Slim
            if 'playstation 5' in variant_norm or 'ps5' in variant_norm:
                # Check for Digital first (more specific)
                if 'digital' in text_lower and 'digital' in variant_norm:
                    candidates.append((variant, 0.95))
                    seen.add(variant.id)
                    continue
                # Only match non-digital Slim if digital is NOT in text
                if 'digital' not in text_lower:
                    if re.search(r'(?:\b|\d)slim\b', text_lower) and 'slim' in variant_norm and 'digital' not in variant_norm:
                        candidates.append((variant, 0.95))
                        seen.add(variant.id)
                        continue
            
            # PS4: Pro, Slim (handle patterns like "4pro", "4slim")
            if 'playstation 4' in variant_norm or 'ps4' in variant_norm:
                # Match "pro" at word boundary OR preceded by digit (e.g., "4pro")
                # but not inside other words (e.g., "prodaetsya")
                pro_pattern = r'(?:\b|\d)pro\b'
                slim_pattern = r'(?:\b|\d)slim\b'
                if re.search(pro_pattern, text_lower) and 'pro' in variant_norm:
                    candidates.append((variant, 0.95))
                    seen.add(variant.id)
                    continue
                if re.search(slim_pattern, text_lower) and 'slim' in variant_norm:
                    candidates.append((variant, 0.95))
                    seen.add(variant.id)
                    continue
            
            # Switch: V1, V2, OLED, Lite
            if 'switch' in variant_norm:
                if 'oled' in text_lower and 'oled' in variant_norm:
                    candidates.append((variant, 0.95))
                    seen.add(variant.id)
                    continue
                if 'lite' in text_lower and 'lite' in variant_norm:
                    candidates.append((variant, 0.95))
                    seen.add(variant.id)
                    continue
                if 'v2' in text_lower or 'new' in text_lower:
                    if 'v2' in variant_norm or 'new' in variant_norm:
                        candidates.append((variant, 0.85))
                        seen.add(variant.id)
                        continue
            
            # Fuzzy match variant name
            if variant_norm in text_lower:
                candidates.append((variant, 0.80))
                seen.add(variant.id)
                continue
            
            # Check storage capacity
            if variant.storage_gb:
                storage_patterns = [
                    rf'\b{variant.storage_gb}\s*gb?\b',
                    rf'\b{variant.storage_gb}\s*g\b',
                ]
                for pattern in storage_patterns:
                    if re.search(pattern, text_lower):
                        candidates.append((variant, 0.70))
                        seen.add(variant.id)
                        break
        
        # Sort by confidence (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            return candidates[0]
        return None, 0.0
    
    def _match_edition(self, normalized: str, full_text: str, console_id: Optional[int]) -> Tuple[Optional[ConsoleEdition], float]:
        """Match special edition."""
        if not console_id:
            return None, 0.0
        
        editions = self.editions_by_console.get(console_id, [])
        if not editions:
            return None, 0.0
        
        candidates = []
        seen = set()
        
        text_lower = normalized.lower()
        
        for edition in editions:
            if edition.id in seen:
                continue
            
            edition_norm = normalize_text(edition.edition_name)
            
            # Check for edition name in text
            if edition_norm in text_lower:
                candidates.append((edition, 0.85))
                seen.add(edition.id)
                continue
            
            # Check search keywords - require specific keywords, not generic ones
            for kw in edition.search_keywords:
                if kw and kw in text_lower:
                    # Skip generic keywords like just "switch" or "nintendo switch"
                    # Require edition-specific terms (game names, colors, etc.)
                    kw_lower = kw.lower()
                    if len(kw_lower) > 10 or any(term in kw_lower for term in ['edition', 'bundle', 'color', 'mario', 'zelda', 'pokemon', 'animal', 'fortnite', 'splatoon', 'monster']):
                        candidates.append((edition, 0.80))
                        seen.add(edition.id)
                        break
        
        # Sort by confidence
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            return candidates[0]
        return None, 0.0
    
    def get_candidates(self, text: str, limit: int = 5) -> List[Tuple[ConsoleReference, float]]:
        """Get top console candidates for a given text (for debugging)."""
        normalized = normalize_text(text)
        text_lower = normalized.lower()
        
        candidates = []
        seen = set()
        
        for console in self.consoles:
            if console.id in seen:
                continue
            
            console_norm = normalize_text(console.name)
            score = 0.0
            
            # Exact match
            if console_norm in text_lower:
                score = 1.0
            # Partial match
            elif any(word in text_lower for word in console_norm.split() if len(word) > 2):
                score = 0.7
            # Fuzzy match
            else:
                ratio = fuzz.partial_ratio(console_norm, text_lower) / 100.0
                if ratio > 0.6:
                    score = ratio * 0.5
            
            if score > 0:
                candidates.append((console, score))
                seen.add(console.id)
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:limit]
