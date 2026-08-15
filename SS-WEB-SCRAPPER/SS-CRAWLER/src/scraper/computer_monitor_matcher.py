"""Monitor matcher for detecting monitors in computer listings."""
import re
from typing import Optional, List, Tuple, Dict
from rapidfuzz import fuzz

from src.models.schemas import MonitorReference
from src.utils.text import normalize_text
from src.utils.logger import get_logger

logger = get_logger("computer_monitor_matcher")


class ComputerMonitorMatcher:
    """
    Detects if a monitor is included in a computer listing.
    This is different from the standalone monitor scraper - it's designed
    to detect "monitor included" mentions in PC listings.
    """

    def __init__(self, monitors: List[MonitorReference]):
        """Initialize with monitor reference data."""
        self.monitors = monitors
        self._build_index()
        logger.info(f"ComputerMonitorMatcher initialized with {len(monitors)} monitors")

    def _build_index(self):
        """Build search index from monitor references."""
        self.brand_to_monitors: Dict[str, List[MonitorReference]] = {}
        self.model_to_monitor: Dict[str, MonitorReference] = {}

        for mon in self.monitors:
            # Index by brand
            brand_key = normalize_text(mon.brand)
            if brand_key not in self.brand_to_monitors:
                self.brand_to_monitors[brand_key] = []
            self.brand_to_monitors[brand_key].append(mon)

            # Index by model (exact and partial)
            model_key = normalize_text(mon.model)
            self.model_to_monitor[model_key] = mon

    def _extract_size_from_text(self, text: str) -> Optional[str]:
        """Extract monitor size from text (e.g., '24', '27', '32').

        Must be careful to not pick up CPU/GPU model numbers like "3600" or "3060".
        """
        text_lower = text.lower()

        # First, exclude sections that mention CPU/GPU
        cpu_gpu_patterns = [
            r'ryzen\s+\d+',
            r'i\d+-\d+',  # Intel CPUs
            r'i\d+\s*-\s*\d+',
            r'rtx\s*\d+',
            r'gtx\s*\d+',
            r'rx\s*\d+',
            r'radeon\s+\w+',
            r'core\s+i\d+',
        ]

        # Find monitor-related sections
        monitor_sections = []

        # Look for sections mentioning "monitor" or "ekrans" (Latvian)
        monitor_keywords = ['monitor', 'ekrans', 'displejs', 'displays']
        lines = text_lower.split('\n')

        for line in lines:
            line_lower = line.lower()
            # Check if line mentions monitor
            if any(kw in line_lower for kw in monitor_keywords):
                monitor_sections.append(line_lower)
            # Also check lines with + symbol (often indicates additional items)
            elif '+' in line and any(kw in line_lower for kw in ['pc', 'dators', 'komp']):
                monitor_sections.append(line_lower)

        # Search in monitor sections first
        search_text = ' '.join(monitor_sections) if monitor_sections else text_lower

        # Match patterns like "24", "24\"", "24 inch", "27.5"
        # Require inch indicator or be careful about context
        size_patterns = [
            r'(\d{2,3}(?:\.\d)?)\s*["\']\s*(?:inch|in)?',  # 24" or 24'
            r'(\d{2,3})\s*(?:inch|in|′′|collas)',  # 24 inch, 24 collas (Latvian)
            r'\bmonitors?\s+(?:\w+\s+)?(\d{2,3})\b',  # "monitor 24" or "monitors hp 24" or "monitorā 27"
            r'ekrans\w*\s+(?:\w+\s+)?(\d{2,3})\b',  # Latvian "ekrans 24" or "ekrans hp 24"
            r'\+\s*(?:monitor|ekrans)?\s*[:\-]?\s*(\d{2,3})',  # + monitor 24
            r'monitors?\s+(?:\w+\s+)?(\d{2,3})\s*(?:collas|inch)',  # "monitor hp 24 collas"
            r'(\d{2,3})\s*collas',  # "27 collas" - Latvian for inches
        ]

        for pattern in size_patterns:
            match = re.search(pattern, search_text)
            if match:
                size = match.group(1)
                # Validate: monitor sizes are typically 21-49 inches
                try:
                    size_num = float(size)
                    if 21 <= size_num <= 49:
                        return str(int(size_num))
                except ValueError:
                    pass

        return None

    def _extract_resolution_from_text(self, text: str) -> Optional[str]:
        """Extract resolution from text."""
        res_patterns = [
            r'\b(1920\s*x\s*1080|1080p|fhd|full\s*hd)\b',
            r'\b(2560\s*x\s*1440|1440p|qhd|wqhd)\b',
            r'\b(3840\s*x\s*2160|2160p|4k|uhd|ultra\s*hd)\b',
            r'\b(3440\s*x\s*1440|ultrawide)\b',
            r'\b(5120\s*x\s*1440)\b',
        ]

        for pattern in res_patterns:
            match = re.search(pattern, text.lower())
            if match:
                res = match.group(1)
                # Normalize
                if '1080' in res or 'fhd' in res:
                    return "1920x1080"
                elif '1440' in res or 'qhd' in res or 'wqhd' in res:
                    return "2560x1440"
                elif '2160' in res or '4k' in res or 'uhd' in res:
                    return "3840x2160"
                elif '3440' in res:
                    return "3440x1440"
                return res

        return None

    def _extract_refresh_rate(self, text: str) -> Optional[str]:
        """Extract refresh rate from text."""
        refresh_patterns = [
            r'\b(\d{2,3})\s*hz\b',
            r'\b(\d{2,3})\s*hertz\b',
            r'\b(\d{2,3})\s*гц\b',  # Cyrillic
        ]

        for pattern in refresh_patterns:
            match = re.search(pattern, text.lower())
            if match:
                return match.group(1)

        return None

    def _extract_panel_type(self, text: str) -> Optional[str]:
        """Extract panel type from text."""
        panel_patterns = [
            (r'\bips\b', 'IPS'),
            (r'\bva\b', 'VA'),
            (r'\btn\b', 'TN'),
            (r'\boled\b', 'OLED'),
            (r'\bmini[-\s]?led\b', 'Mini LED'),
        ]

        for pattern, panel_type in panel_patterns:
            if re.search(pattern, text.lower()):
                return panel_type

        return None

    def _extract_monitor_context(self, text: str) -> str:
        """Extract text that is in monitor context (near monitor keywords)."""
        text_lower = text.lower()
        monitor_keywords = ['monitor', 'ekrans', 'displejs', 'displays', 'screen', 'ultragear', '144hz']

        # Find lines with monitor keywords
        lines = text_lower.split('\n')
        monitor_context_parts = []

        for line in lines:
            line_lower = line.lower()
            if any(kw in line_lower for kw in monitor_keywords):
                monitor_context_parts.append(line_lower)

        # If no lines with newlines found, check if text is single-line
        if not monitor_context_parts:
            # For single-line text, extract the portion around monitor keywords
            for kw in monitor_keywords:
                if kw in text_lower:
                    # Find position of keyword and extract surrounding text
                    kw_pos = text_lower.find(kw)
                    start = max(0, kw_pos - 200)  # 200 chars before
                    end = min(len(text_lower), kw_pos + len(kw) + 200)  # 200 chars after
                    monitor_context_parts.append(text_lower[start:end])
                    break

        return ' '.join(monitor_context_parts) if monitor_context_parts else ""
    
    def _has_explicit_monitor_context(self, text: str) -> bool:
        """Check if text explicitly mentions a monitor (not just numbers that could be GPU)."""
        text_lower = text.lower()
        
        # Keywords that unambiguously indicate a monitor
        explicit_patterns = [
            r'monitor\s*[:\-]',  # "Monitor:" or "Monitor -"
            r'monitors?\s+(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc|lenovo|msi)',
            r'(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc|lenovo|msi)\s+monitors?',
            r'ekr[aā]ns',  # Latvian for "screen"
            r'displejs',   # Latvian for "display"
        ]
        
        for pattern in explicit_patterns:
            if re.search(pattern, text_lower):
                return True
        return False

    def _create_generic_monitor(self, size: Optional[str], resolution: Optional[str],
                                   refresh: Optional[str], panel: Optional[str],
                                   is_included: bool, detection_method: str):
        """Create a generic monitor when no specific model is found."""
        size_str = size or "24"
        res_str = resolution or "1920x1080"

        generic_monitor = MonitorReference(
            id=-1,
            brand="Generic",
            model=f"{size_str}\" {res_str}",
            size=size_str,
            resolution=res_str,
            refresh_rate=refresh or "60",
            panel_type=panel or "IPS",
            search_keywords=["generic", "monitor", size_str, res_str],
            normalized_name=normalize_text(f"Generic {size_str} {res_str}")
        )

        confidence = 0.50 if is_included else 0.30
        method = detection_method if is_included else "size_only"

        logger.info(f"Generic monitor detected: {generic_monitor.model} ({confidence:.0%})")
        return generic_monitor, confidence, method

    def _detect_monitor_mentioned(self, text: str) -> Tuple[bool, str]:
        """Detect if monitor is mentioned as included in the listing."""
        text_lower = text.lower()

        # Keywords indicating monitor is included
        inclusion_patterns = [
            r'monitors?\s*[:\-]?\s*(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)',  # Handle "Monitor: AOC" format
            r'monitors?\s+(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)',
            r'(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)\s+monitors?',
            r'(?:ekrans|displejs|displays?)\s+(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)',
            r'(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)\s+(?:ekrans|displejs|displays?)',
            r'(?i)monitors?\s+(?:\d{2,3})["\']?\s*(?:collas|inch|in|\")',
            r'(?i)(?:\d{2,3})["\']?\s*(?:collas|inch|in|\\")\s+monitors?',
            r'monitors?\s+(?:dāvan|gift|included|komplekt|līdzi)',
            r'(?:dāvan|gift|included|komplekt|līdzi)\s+monitors?',
            r'ekrans\s+(?:dāvan|gift|included|komplekt|līdzi)',
            r'displejs\s+(?:dāvan|gift|included|komplekt|līdzi)',
            r'(?i)monitors?\s+(?:\d{2,3})\s+(?:collas|inch)',
            r'(?i)hp\s+(?:\d{2,3})\s+collas',
            r'(?i)lg\s+(?:\d{2,3})\s+collas',
            r'(?i)dell\s+(?:\d{2,3})\s+collas',
            r'(?i)asus\s+(?:\d{2,3})\s+collas',
            r'ultragear',  # LG UltraGear is definitely a monitor
        ]

        for pattern in inclusion_patterns:
            if re.search(pattern, text_lower):
                return True, "monitor_mentioned"

        # Simple keyword check
        monitor_keywords = ['monitors', 'ekrans', 'displejs', 'displays', 'screen']
        for kw in monitor_keywords:
            if kw in text_lower:
                return True, f"keyword_{kw}"

        return False, "none"

    def match_listing(self, title: str, description: str) -> Tuple[Optional[MonitorReference], float, str]:
        """
        Match a computer listing to a monitor reference.

        Returns:
            Tuple of (matched_monitor, confidence, match_method)
        """
        full_text = f"{title} {description}".lower()
        normalized = normalize_text(full_text)

        # Check for explicit monitor mention first - if present, don't skip even with GPU in text
        has_explicit_monitor = self._has_explicit_monitor_context(full_text)

        # Skip if text contains GPU patterns that would cause false matches
        # e.g., "RX 570" shouldn't match "Proview 570" monitor
        # BUT: Only skip if there's NO explicit monitor mention in the text
        gpu_indicators = ['rx 570', 'rx 580', 'rx 590', 'gtx 1660', 'rtx 3060', 'rtx 3070', 'rtx 3080', 'rtx 4060']
        text_lower = full_text.lower()
        if not has_explicit_monitor:  # Only apply GPU skip if no explicit monitor context
            for gpu in gpu_indicators:
                if gpu in text_lower:
                    # Check if this is causing a false monitor match
                    # Extract number from GPU pattern
                    gpu_num = ''.join(filter(str.isdigit, gpu))
                    # If monitor model contains same number, it's likely a false match
                    for mon in self.monitors:
                        mon_model = normalize_text(mon.model)
                        if gpu_num in mon_model and gpu_num in ['570', '580', '1660', '3060', '3070', '3080']:
                            # This is likely a GPU, skip monitor matching
                            logger.debug(f"Skipping monitor match - GPU pattern '{gpu}' detected")
                            return None, 0.0, "gpu_detected_no_monitor"

        # Also skip if no monitor-related keywords in text and weak matches
        # "HP 32" without "monitor" context is likely false
        has_monitor_context = any(kw in text_lower for kw in ['monitor', 'ekrans', 'displejs', 'displays', 'screen'])
        if not has_monitor_context:
            # Check if the only matches are weak numeric ones
            size_only_match = self._extract_size_from_text(full_text)
            if not size_only_match:
                # No explicit monitor context AND no size extracted - this is a very weak match
                # Still allow the matching to proceed, but will be rejected later if score is too low
                logger.debug("No monitor context and no size extracted - will apply stricter thresholds")

        # First check if monitor is explicitly mentioned as included
        is_included, detection_method = self._detect_monitor_mentioned(full_text)

        # NEW: Check for specific gaming monitor model patterns that should match regardless of context
        # These are common gaming monitors that might not have "monitor" keyword nearby
        gaming_monitor_patterns = [
            # LG UltraGear patterns
            (r'lg\s+24gn\d+', 'LG', '24GN'),  # LG 24GN600, LG 24GN650, etc.
            (r'lg\s+27gn\d+', 'LG', '27GN'),
            (r'lg\s+32gn\d+', 'LG', '32GN'),
            (r'24gn\d+', 'LG', '24GN'),  # Just the model number
            (r'27gn\d+', 'LG', '27GN'),
            (r'32gn\d+', 'LG', '32GN'),
            # AOC Gaming patterns
            (r'aoc\s+24g2', 'AOC', '24G2'),
            (r'aoc\s+27g2', 'AOC', '27G2'),
            # ASUS TUF Gaming
            (r'asus\s+vg\d+', 'ASUS', 'VG'),
            (r'vg\d+\s+asus', 'ASUS', 'VG'),
        ]
        
        for pattern, brand_hint, model_hint in gaming_monitor_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                # Found a gaming monitor pattern - search for matching monitor
                logger.info(f"Gaming monitor pattern found: {pattern}")
                for mon in self.monitors:
                    if brand_hint.lower() in normalize_text(mon.brand):
                        mon_model_lower = normalize_text(mon.model).lower()
                        if model_hint.lower() in mon_model_lower:
                            # Found matching monitor
                            logger.info(f"Matched gaming monitor: {mon.brand} {mon.model}")
                            return mon, 0.85, "gaming_model_match"

        # Extract specs from listing
        extracted_size = self._extract_size_from_text(full_text)
        extracted_resolution = self._extract_resolution_from_text(full_text)
        extracted_refresh = self._extract_refresh_rate(full_text)
        extracted_panel = self._extract_panel_type(full_text)

        logger.debug(f"Monitor detection: size={extracted_size}, res={extracted_resolution}, "
                    f"refresh={extracted_refresh}, panel={extracted_panel}, included={is_included}")

        best_match = None
        best_score = 0.0
        best_method = "none"

        # Search through monitor references
        # Only consider matches in monitor context (near monitor keywords)
        # Extract monitor context - text near monitor keywords
        monitor_context = self._extract_monitor_context(full_text)
        if not monitor_context:
            # No monitor context found - skip detailed matching
            if is_included:
                # Monitor is mentioned but no context - return generic
                return self._create_generic_monitor(extracted_size, extracted_resolution,
                                                     extracted_refresh, extracted_panel,
                                                     is_included, detection_method)
            return None, 0.0, "no_monitor_context"
        
        # Create filtered context ONCE outside the loop
        # This excludes refresh rates and response times to avoid matching "240" from "240hz"
        monitor_context_filtered = monitor_context
        # Remove Hz patterns like "240hz", "144 hz", etc.
        monitor_context_filtered = re.sub(r'\d{2,3}\s*hz\b', '', monitor_context_filtered, flags=re.IGNORECASE)
        # Remove ms patterns like "0.1ms", "1 ms", etc.
        monitor_context_filtered = re.sub(r'\d+(?:\.\d+)?\s*ms\b', '', monitor_context_filtered, flags=re.IGNORECASE)
        
        logger.info(f"[MONITOR DEBUG] Original context: '{monitor_context}'")
        logger.info(f"[MONITOR DEBUG] Filtered context: '{monitor_context_filtered}'")
        logger.info(f"[MONITOR DEBUG] Extracted size: {extracted_size}, refresh: {extracted_refresh}")

        for mon in self.monitors:
            score = 0.0
            matches = []

            # Check brand match - must be in monitor context
            brand_clean = normalize_text(mon.brand)
            if brand_clean in monitor_context:
                score += 0.30
                matches.append("brand")

            # Check model match - must be in monitor context, not just anywhere in text
            model_clean = normalize_text(mon.model)
            # Use word boundaries for model matching to avoid partial matches
            escaped = re.escape(model_clean)
            model_full_match = re.search(r'(?i)\b' + escaped + r'\b', monitor_context)
            if model_full_match:
                score += 0.50  # Increased weight for full model match
                matches.append("model_full")
            else:
                # Check if text contains start of model (e.g., "sa270" matches "sa270bid")
                # Use FILTERED context to avoid matching refresh rates
                if len(model_clean) >= 4:
                    # Check for partial match where text has shorter version of model
                    # e.g., text has "sa270", model is "sa270bid"
                    for i in range(len(model_clean), 3, -1):
                        model_prefix = model_clean[:i]
                        # Skip if prefix is just the brand name (prevents "hp" matching "hp hp 27mq")
                        if model_prefix == brand_clean:
                            continue
                        if model_prefix in monitor_context_filtered:
                            score += 0.35  # Strong partial match
                            matches.append("model_prefix")
                            break

                # NEW: Check for partial numeric model matches
                # e.g., text has "2590G4", model is "G2590FX" - both contain "2590"
                # BUT: Don't match refresh rates (e.g., "240hz" shouldn't match "240B1CB")
                if "model_prefix" not in matches and "model_full" not in matches:
                    # Extract numeric sequences from model
                    model_numbers = set(re.findall(r'\d{3,}', model_clean))
                    
                    # Use FILTERED context (already removed Hz/ms patterns above)
                    text_numbers = set(re.findall(r'\d{3,}', monitor_context_filtered))  # 3+ digit numbers

                    # Check for overlapping numbers
                    common_numbers = text_numbers & model_numbers
                    if common_numbers:
                        # Found common numbers - likely same model series
                        score += 0.30
                        matches.append("model_number_match")

                # NEW: Check for model match without suffix (e.g., "24gn600" matches "24gn600b")
                # This handles cases where the listing omits the suffix letter
                if "model_prefix" not in matches and "model_full" not in matches and "model_number_match" not in matches:
                    # Remove trailing letters from model to get base model number
                    base_model = re.sub(r'[a-z]+$', '', model_clean)  # e.g., "24gn600b" -> "24gn600"
                    # Use FILTERED context for base model matching too
                    if base_model and len(base_model) >= 5 and base_model in monitor_context_filtered:
                        score += 0.35  # Strong partial match for base model
                        matches.append("model_base")

                # Check partial model match - require word boundaries
                if "model_prefix" not in matches and "model_number_match" not in matches and "model_base" not in matches:
                    model_parts = mon.model.split()
                    for part in model_parts:
                        part_clean = normalize_text(part)
                        # Skip if part is just the brand name
                        if part_clean == brand_clean:
                            continue
                        if len(part_clean) >= 3:
                            # Use word boundary regex for stricter matching
                            escaped = re.escape(part_clean)
                            pattern = r'(?i)\b' + escaped + r'\b'
                            # Use FILTERED context for partial matches too
                            if re.search(pattern, monitor_context_filtered):
                                score += 0.20
                                matches.append("model_partial")
                                break

            # Check size match - require matching size if size is explicitly mentioned
            if mon.size and extracted_size:
                mon_size = str(int(float(mon.size))) if '.' in mon.size else mon.size
                if mon_size == extracted_size:
                    score += 0.15
                    matches.append("size")
                else:
                    # Size mismatch - but allow if there's very strong model match
                    # e.g., "2590G4" should match "G2590FX" even though one is 25" and other is 24"
                    # The model numbers overlap (2590) which is stronger than exact size match
                    has_strong_model_match = "model_full" in matches or "model_number_match" in matches
                    if has_strong_model_match:
                        # Size mismatch but strong model match - still allow but lower score
                        score += 0.05  # Reduced size bonus for mismatch
                        matches.append("size_mismatch_allowed")
                    else:
                        # Size mismatch and no strong model match - reject
                        score = 0  # Reset score - size is critical
                        matches = []
                        continue  # Skip to next monitor

            # Check resolution match
            if mon.resolution and extracted_resolution:
                if normalize_text(mon.resolution) == normalize_text(extracted_resolution):
                    score += 0.10
                    matches.append("resolution")

            # Check refresh rate match
            if mon.refresh_rate and extracted_refresh:
                if mon.refresh_rate == extracted_refresh:
                    score += 0.05
                    matches.append("refresh")

            # Check panel type match
            if mon.panel_type and extracted_panel:
                if mon.panel_type.upper() == extracted_panel.upper():
                    score += 0.05
                    matches.append("panel")

            if score > best_score:
                best_score = score
                best_match = mon
                best_method = "+".join(matches) if matches else "fuzzy"
                
                if score >= 0.449:
                    logger.info(f"[MONITOR DEBUG] Top match so far: {mon.brand} {mon.model} score={score:.2f} method={best_method}")

        # Return match if found with sufficient confidence
        # Require explicit monitor mention OR size+resolution for weak matches
        if best_match and best_score >= 0.449:  # Use 0.449 to handle floating point precision (0.45 exactly)
            # Check if this is a strong match (brand + model) or has monitor context
            has_brand = "brand" in best_method
            has_model = "model_full" in best_method or "model_partial" in best_method or "model_prefix" in best_method or "model_number_match" in best_method

            # For monitor context, we already extracted it - use it directly
            has_monitor_context = is_included  # is_included means monitor is mentioned

            # Reject matches where the brand is also a motherboard/GPU brand but no monitor context
            # e.g., "Gigabyte" appears in motherboard section but no monitor keywords
            ambiguous_brands = ['gigabyte', 'asus', 'msi', 'asrock', 'aorus', 'evga']
            if has_brand and not has_monitor_context:
                brand_lower = best_match.brand.lower()
                if brand_lower in ambiguous_brands:
                    logger.debug(f"Monitor match rejected - ambiguous brand '{brand_lower}' without monitor context: {best_match.model}")
                    return None, 0.0, "rejected_ambiguous_brand"

            # If monitor is mentioned but no model match, try brand+size matching
            # BUT: Only use this if we didn't already find a good match through scoring
            # The scoring loop already handles brand+size+refresh matching better
            if has_monitor_context and not has_model and best_score < 0.50:
                # Check if this is a monitor-only brand (not also motherboard/GPU)
                monitor_only_brands = ['hp', 'dell', 'lg', 'samsung', 'philips', 'benq', 'viewsonic', 'aoc', 'lenovo']
                ambiguous_brands = ['gigabyte', 'asus', 'msi', 'asrock', 'aorus', 'evga']
                
                brand_lower = best_match.brand.lower()
                logger.debug(f"Brand+size check: brand={brand_lower}, has_monitor_context={has_monitor_context}, extracted_size={extracted_size}")
                
                if brand_lower in monitor_only_brands and extracted_size:
                    # For monitor-only brands with size, accept the closest size match
                    # Find all monitors from this brand with matching size
                    matching_size_monitors = []
                    logger.debug(f"Searching for {brand_lower} monitors with size {extracted_size}")
                    
                    for mon in self.monitors:
                        if mon.brand.lower() == brand_lower and mon.size:
                            try:
                                mon_size = int(float(mon.size))
                                extracted_size_int = int(float(extracted_size))
                                if mon_size == extracted_size_int:
                                    matching_size_monitors.append(mon)
                                    logger.debug(f"  Found match: {mon.model} (size: {mon.size})")
                            except (ValueError, TypeError) as e:
                                logger.debug(f"  Error with {mon.model}: {e}")
                                pass
                    
                    logger.debug(f"Total matching monitors: {len(matching_size_monitors)}")
                    
                    if matching_size_monitors:
                        # Prefer monitors with matching refresh rate if available
                        best_refresh_match = None
                        for mon in matching_size_monitors:
                            if extracted_refresh and mon.refresh_rate == extracted_refresh:
                                best_refresh_match = mon
                                break
                        
                        if best_refresh_match:
                            best_match = best_refresh_match
                            logger.info(f"Brand+size+refresh match: {best_match.brand} {best_match.model}")
                        else:
                            # Return the first matching monitor from this brand+size
                            best_match = matching_size_monitors[0]
                            logger.info(f"Brand+size match: {best_match.brand} {best_match.model}")
                        best_method = "brand+size_match"
                        best_score = 0.45
                        # Continue to return this match below
                    else:
                        # No size match - use generic
                        logger.debug(f"Monitor mentioned but no model/size match - using generic: {best_match.brand}")
                        return self._create_generic_monitor(extracted_size, extracted_resolution,
                                                             extracted_refresh, extracted_panel,
                                                             is_included, detection_method)
                else:
                    # Ambiguous brand or no size - use generic
                    logger.debug(f"Monitor mentioned but no model match - using generic: {best_match.brand}")
                    return self._create_generic_monitor(extracted_size, extracted_resolution,
                                                         extracted_refresh, extracted_panel,
                                                         is_included, detection_method)

            # STRONGER REQUIREMENTS: Without explicit monitor mention, need very strong evidence
            # Require either: full model match, OR brand+model, OR high score
            if not has_monitor_context:
                # No explicit monitor context - be very strict
                if best_score < 0.60:  # Increased from 0.70
                    logger.debug(f"Monitor match rejected - no context and weak score: {best_match.brand} {best_match.model} ({best_score:.0%})")
                    return None, 0.0, "rejected_no_context"
                elif not has_model:
                    logger.debug(f"Monitor match rejected - no context and no model match: {best_match.brand} {best_match.model}")
                    return None, 0.0, "rejected_no_model"
                elif not has_brand:
                    logger.debug(f"Monitor match rejected - no context and no brand match: {best_match.brand} {best_match.model}")
                    return None, 0.0, "rejected_no_brand"

            logger.info(f"Monitor matched: {best_match.brand} {best_match.model} ({best_score:.0%})")
            return best_match, min(1.0, best_score), best_method

        # If monitor is explicitly mentioned but no specific model found,
        # return a generic monitor
        if is_included or extracted_size:
            # Create a generic monitor reference
            size_str = extracted_size or "24"
            res_str = extracted_resolution or "1920x1080"

            generic_monitor = MonitorReference(
                id=-1,  # Indicates generic
                brand="Generic",
                model=f"{size_str}\" {res_str}",
                size=size_str,
                resolution=res_str,
                refresh_rate=extracted_refresh or "60",
                panel_type=extracted_panel or "IPS",
                search_keywords=["generic", "monitor", size_str, res_str],
                normalized_name=normalize_text(f"Generic {size_str} {res_str}")
            )

            confidence = 0.50 if is_included else 0.30
            method = detection_method if is_included else "size_only"

            logger.info(f"Generic monitor detected: {generic_monitor.model} ({confidence:.0%})")
            return generic_monitor, confidence, method

        return None, 0.0, "none"

    def get_estimated_price(self, monitor: MonitorReference) -> float:
        """Get estimated price for a monitor."""
        # Generic monitor pricing based on size and resolution
        size = float(monitor.size) if monitor.size else 24
        res = monitor.resolution or "1920x1080"

        # Base prices by size
        base_prices = {
            22: 80,
            24: 100,
            27: 180,
            32: 250,
        }

        # Find closest size
        closest_size = min(base_prices.keys(), key=lambda x: abs(x - size))
        price = base_prices[closest_size]

        # Adjust for resolution
        if "2560x1440" in res or "1440" in res:
            price += 80
        elif "3840x2160" in res or "4k" in res.lower():
            price += 150
        elif "3440x1440" in res:
            price += 120  # Ultrawide

        # Adjust for refresh rate
        refresh = int(monitor.refresh_rate) if monitor.refresh_rate and monitor.refresh_rate.isdigit() else 60
        if refresh >= 144:
            price += 50
        elif refresh >= 120:
            price += 30
        elif refresh >= 75:
            price += 15

        # Adjust for panel type
        if monitor.panel_type:
            panel = monitor.panel_type.upper()
            if panel == "OLED":
                price += 200
            elif panel == "MINI LED":
                price += 100
            elif panel == "IPS":
                price += 20

        return price
