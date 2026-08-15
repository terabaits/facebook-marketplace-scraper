"""Computer matcher - matches listings to components and applies fallbacks."""
import re
from typing import Optional, Dict, List, Tuple
from rapidfuzz import fuzz

from src.scraper.cpu_matcher import CPUMatcher
from src.scraper.matcher import GPUMatcher
from src.scraper.ram_matcher import RAMMatcher
from src.scraper.ssd_matcher import SSDMatcher
from src.scraper.psu_matcher import PSUMatcher
from src.scraper.case_matcher import CaseMatcher
from src.scraper.motherboard_matcher import MotherboardMatcher
from src.scraper.computer_monitor_matcher import ComputerMonitorMatcher
from src.models.schemas import CPUReference, GPUReference, RAMReference, SSDReference, PSUReference, CaseReference, MotherboardReference, MonitorReference
from src.models.computer_schemas import ComputerMatchResult
from src.utils.text import normalize_text
from src.utils.logger import get_logger

logger = get_logger("computer_matcher")


class ComputerMatcher:
    """Matches computer listings to their components."""

    # Entry-level motherboard prices by socket (approximate)
    MOTHERBOARD_PRICES = {
        # Intel
        'lga1700': 85.0,
        'lga1200': 65.0,  # i7-10700 socket
        'lga1151': 40.0,
        'lga1150': 40.0,
        'lga1155': 35.0,
        'lga2066': 250.0,
        'lga2011': 150.0,
        'lga2011-3': 180.0,
        # AMD
        'am5': 120.0,
        'am4': 40.0,
        'am3+': 35.0,
        'am3': 30.0,
        'fm2+': 30.0,
        'fm2': 25.0,
        'tr4': 300.0,
        'sTRX4': 350.0,
        'sWRX8': 400.0,
    }

    def __init__(self,
                 cpus: List[CPUReference],
                 gpus: List[GPUReference],
                 rams: List[RAMReference],
                 ssds: List[SSDReference],
                 psus: List[PSUReference],
                 cases: List[CaseReference],
                 motherboards: List[MotherboardReference] = None,
                 monitors: List[MonitorReference] = None):
        """Initialize with all component reference data."""
        self.cpu_matcher = CPUMatcher(cpus)
        self.gpu_matcher = GPUMatcher(gpus)
        self.ram_matcher = RAMMatcher(rams)
        self.ssd_matcher = SSDMatcher(ssds)
        self.psu_matcher = PSUMatcher(psus)
        self.case_matcher = CaseMatcher(cases)
        self.motherboard_matcher = MotherboardMatcher(motherboards) if motherboards else None
        self.monitor_matcher = ComputerMonitorMatcher(monitors) if monitors else None

        self.cpus = {c.id: c for c in cpus}
        self.gpus = {g.id: g for g in gpus}
        self.rams = {r.id: r for r in rams}
        self.ssds = {s.id: s for s in ssds}
        self.psus = {p.id: p for p in psus}
        self.cases = {c.id: c for c in cases}
        self.motherboards = {m.id: m for m in motherboards} if motherboards else {}
        self.monitors = {m.id: m for m in monitors} if monitors else {}

        mb_count = len(motherboards) if motherboards else 0
        mon_count = len(monitors) if monitors else 0
        logger.info(f"ComputerMatcher initialized: {len(cpus)} CPUs, {len(gpus)} GPUs, "
                   f"{len(rams)} RAMs, {len(ssds)} SSDs, {len(psus)} PSUs, {len(cases)} Cases, "
                   f"{mb_count} Motherboards, {mon_count} Monitors")

    def match(self, title: str, description: str = "", price: Optional[float] = None) -> ComputerMatchResult:
        """Match a computer listing to all its components."""
        full_text = f"{title} {description}".strip()
        normalized = normalize_text(full_text)
        text_lower = normalized.lower()

        result = ComputerMatchResult()

        # Match CPU
        # Try to extract a CPU base frequency (GHz) from the listing options.
        # Patterns cover both "Procesora frekvence, Ghz: 3.60" and merged "Ryzen 5 3.60".
        base_freq_mhz = None
        freq_patterns = [
            r'procesora\s+frekvence,?\s*ghz\s*[:\s]\s*(\d+\.\d+)',
            r'cpu\s+frekvence,?\s*ghz\s*[:\s]\s*(\d+\.\d+)',
            r'(?:amd|intel)\s+(?:ryzen|core|i[3579]).*?(\d+\.\d+)\s*ghz',
            r'(\d+\.\d+)\s*ghz',
        ]
        for pattern in freq_patterns:
            freq_match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if freq_match:
                try:
                    base_freq_mhz = int(float(freq_match.group(1)) * 1000)
                    break
                except ValueError:
                    pass
        cpu_match = self.cpu_matcher.match(title, description or "", base_freq_mhz=base_freq_mhz)
        if cpu_match.cpu:
            result.cpu = cpu_match.cpu.model_dump() if hasattr(cpu_match.cpu, 'model_dump') else cpu_match.cpu.__dict__
            result.cpu_confidence = cpu_match.confidence
            result.cpu_method = cpu_match.method

        # Match GPU
        # Skip if only integrated graphics mentioned
        # Also skip if listing explicitly says "no GPU" or "Nav" (Latvian for "none")
        # NOTE: "bez videokartes" means "without video card" but if a GPU is explicitly mentioned later, match it
        has_no_gpu = any(kw in text_lower for kw in ['video nav', 'nav video', 'no gpu', 'gpu nav',
                                                      'bez videokartes', 'bez video', 'nav videokarte',
                                                      'bez gpu', 'nav gpu'])

        # If GPU model is explicitly mentioned (e.g., "Videokarte: Powercolor red devil RX6800XT"), don't skip
        # This handles listings that say "can be purchased without GPU" but also specify the GPU
        gpu_explicitly_mentioned = any(kw in text_lower for kw in ['videokarte:', 'video:', 'gpu:', 'grafika:'])
        gpu_model_in_text = False
        if gpu_explicitly_mentioned:
            # Check if a GPU model appears after the explicit mention
            gpu_patterns = [r'rx\s*\d{4,5}', r'rtx\s*\d{3,4}', r'radeon', r'geforce']
            for pattern in gpu_patterns:
                if re.search(pattern, text_lower):
                    gpu_model_in_text = True
                    break

        # Also check if GPU model appears anywhere in text (even without explicit "videokarte:" label)
        # This handles "Ideāls datorspēlēm RX6800XT videokarti" pattern
        if not gpu_model_in_text:
            gpu_patterns = [r'rx\s*6800', r'rx\s*6900', r'rx\s*6700', r'rx\s*6600',
                           r'rtx\s*4090', r'rtx\s*4080', r'rtx\s*4070', r'rtx\s*3090',
                           r'radeon\s+rx\s*\d{4}']
            for pattern in gpu_patterns:
                if re.search(pattern, text_lower):
                    gpu_model_in_text = True
                    break

        # If GPU is explicitly mentioned with a model, don't skip even if "bez videokartes" appears
        if gpu_model_in_text:
            has_no_gpu = False

        # If explicit "no GPU" phrase is found, skip GPU matching entirely
        if not self._has_integrated_graphics_only(normalized) and not has_no_gpu:
            vram_mb = self._extract_vram_mention(full_text)
            gpu_match = self.gpu_matcher.match(full_text, "", vram_mb=vram_mb)
            # Only accept GPU match if confidence >= 0.60
            if gpu_match.gpu and gpu_match.confidence >= 0.60:
                result.gpu = gpu_match.gpu.model_dump() if hasattr(gpu_match.gpu, 'model_dump') else gpu_match.gpu.__dict__
                result.gpu_confidence = gpu_match.confidence
                result.gpu_method = gpu_match.method

        # Match RAM
        # Try to extract RAM capacity and DDR type from text
        ram_capacity = self._extract_ram_capacity(full_text)
        ram_ddr_type = self._extract_ram_ddr_type(full_text)
        ram_speed = self._extract_ram_frequency(full_text)

        ram_match = self.ram_matcher.match_listing(
            full_text,
            extracted_capacity=ram_capacity,
            extracted_ddr=ram_ddr_type,
            extracted_speed=ram_speed
        )

        # Use matched RAM if it's an exact match or high-confidence model_part match
        # AND the brand is mentioned in the text
        # AND the model name actually appears in the text
        is_specific_ram = False
        ram_is_generic = False
        if ram_match.ram:
            ram_name_lower = ram_match.ram.name.lower()
            brand = ram_name_lower.split()[0] if ram_name_lower else ""

            text_lower = normalized.lower()

            # Extract the specific line containing RAM keyword (to avoid SSD/HDD mentions leaking in)
            # Use full_text to preserve newlines for proper line extraction
            # First check for BRAND names (higher priority), then generic RAM keywords
            ram_line = ""
            lines = full_text.lower().split('\n')

            # First pass: look for brand/model names WITH RAM context (capacity, speed, GB, MHz, etc.)
            # This avoids matching "Corsair" in "Corsair Mid Tower Case"
            brand_keywords = ['kingston', 'hyperx', 'fury', 'furry', 'gskill', 'crucial', 'adata',
                            'viper', 'trident', 'vengeance', 'ripjaws', 'dominator', 'ballistix']
            ram_context_indicators = ['gb', 'mhz', 'ddr', 'ram', 'dim', 'stick', 'module']
            for i, line in enumerate(lines):
                has_brand = any(kw in line for kw in brand_keywords)
                has_ram_context = any(ind in line for ind in ram_context_indicators)
                if has_brand and has_ram_context:
                    ram_line = line
                    # Also include the next line (often contains the actual model)
                    if i + 1 < len(lines):
                        ram_line += " " + lines[i + 1]
                    break

            # Second pass: look for generic RAM keywords if no brand found
            if not ram_line:
                generic_ram_keywords = ['ram', 'operativ', 'atmina', 'memory', 'ddr', 'ram-', 'gb ram', 'atmiņa', 'atmiņas', 'operatīva']
                for i, line in enumerate(lines):
                    for kw in generic_ram_keywords:
                        if kw in line:
                            ram_line = line
                            # Also include the next line (often contains the actual model)
                            if i + 1 < len(lines):
                                ram_line += " " + lines[i + 1]
                            break
                    if ram_line:
                        break

            # If no RAM keyword found, use normalized text
            if not ram_line:
                ram_line = text_lower

            # Check if brand is in the specific RAM line (not just anywhere in text)
            # This prevents "Kingston" from SSD section matching a Kingston RAM
            brand_norm = brand.replace('.', '')  # Remove dots (e.g., "g.skill" -> "gskill")
            has_brand = brand in ram_line or brand_norm in ram_line

            # Special handling: HyperX is Kingston's gaming brand - if "hyperx" is in text,
            # consider it as having the Kingston brand (since HyperX = Kingston HyperX)
            if not has_brand and 'hyperx' in ram_name_lower and 'hyperx' in ram_line:
                has_brand = True

            # Special handling: For compound model names like "Viper Steel" or "Trident Z",
            # if multiple parts of the compound name are present in text, treat it as having brand+model
            # This MUST be checked first before individual model keywords to ensure compound models work
            compound_models = {
                'viper': 'patriot',
                'trident': 'gskill',
                'ripjaws': 'gskill',
                'vengeance': 'corsair',
                'dominator': 'corsair',
                'ballistix': 'crucial',
                'fury': 'kingston',
            }
            compound_model_matched = False
            for model_keyword, implied_brand in compound_models.items():
                if model_keyword in ram_name_lower and model_keyword in ram_line:
                    # Check if compound model has multiple parts
                    # e.g., "Viper Steel" - if both "viper" and "steel" are in text, it's a strong match
                    if 'steel' in ram_name_lower and 'steel' in ram_line and model_keyword == 'viper':
                        has_brand = True  # Treat as having brand since compound model is complete
                        compound_model_matched = True
                        break
                    elif 'z' in ram_name_lower and 'z' in ram_line and model_keyword in ('trident', 'vengeance'):
                        has_brand = True
                        compound_model_matched = True
                        break

            # Check for model series keyword in text (also within RAM line)
            model_keywords = ['vengeance', 'fury', 'ripjaws', 'trident', 'dominator',
                              'ballistix', 'flare', 'aorus', 'renegade', 'elite', 'neo',
                              't-force', 'spectrix', 'sniper', 'value', 'xlr8',
                              'viper', 'steel', 'patriot', 'hyperx', 'aegis',
                              'vipersteel', 'viper steel']
            has_model_in_text = compound_model_matched  # Already true if compound model matched
            for kw in model_keywords:
                if kw in ram_name_lower and kw in ram_line:
                    has_model_in_text = True
                    break

            # Special handling: If "furry" is in text and model is "Fury", consider it a match
            if not has_model_in_text and 'fury' in ram_name_lower and 'furry' in ram_line:
                has_model_in_text = True

            # Special handling: If "hyperx" is in text and the RAM is a HyperX model,
            # consider it a model match even if "fury" is not explicitly mentioned
            if not has_model_in_text and 'hyperx' in ram_name_lower and 'hyperx' in ram_line:
                has_model_in_text = True

            # Check for G.Skill model pattern match (e.g., F4-3200C16D or F4 3000 C16D)
            # Pattern needs to handle both hyphenated and space-separated formats
            has_gskill_model = 'gskill' in ram_line and re.search(r'f\d+[\s-]+\d+\s*c\d+d', ram_line)

            # Brands that are specific to RAM (not generic PC brands)
            # If these brands are mentioned with capacity/speed, accept the match even without model
            ram_specific_brands = {'gskill', 'g.skill', 'corsair', 'kingston', 'crucial',
                                   'teamgroup', 'adata', 'patriot', 'hyperx', 'ballistix'}
            is_ram_specific_brand = brand in ram_specific_brands or brand_norm in ram_specific_brands

            # Check if RAM is described generically (e.g., "16GB DDR4 3200 MHz" without brand)
            # This helps distinguish between generic RAM descriptions vs specific branded RAM
            ram_is_generic = (
                not has_brand and
                not has_model_in_text and
                ram_match.confidence < 0.8
            )

            is_exact = ram_match.method.split('+')[0] == 'exact'
            is_model_part = 'model_part' in ram_match.method
            is_gskill_match = 'gskill_freq' in ram_match.method or 'gskill_cap' in ram_match.method

            # Accept if:
            # 1. Exact match
            # 2. Model_part with brand AND model in text
            # 3. G.Skill pattern match
            # 4. RAM-specific brand (like G.Skill, Corsair) with good confidence (>0.7) and capacity match
            if is_exact:
                is_specific_ram = True
            elif is_model_part and has_brand and has_model_in_text:
                is_specific_ram = True
            elif is_gskill_match and has_gskill_model:
                # G.Skill model pattern detected in text with matching RAM
                is_specific_ram = True
            elif is_ram_specific_brand and has_brand and ram_match.confidence >= 0.70 and not ram_is_generic:
                # RAM-specific brand mentioned with good confidence - accept even without model name
                # BUT: If RAM is described generically (e.g., "16GB DDR4 3200 MHz"), don't match branded RAM
                # This prevents Kingston ValueRAM matching when the text says "16GB DDR4 3200" but "Kingston" is from SSD
                is_specific_ram = True
            else:
                is_specific_ram = False

        if ram_match.ram and is_specific_ram and not has_model_in_text and not ram_is_generic:
            logger.debug(f"Rejecting branded RAM match {ram_match.ram.name} because model name not in text")
            is_specific_ram = False

        # Additional check: If RAM is described generically, don't accept branded match
        if ram_match.ram and is_specific_ram and ram_is_generic:
            logger.debug(f"Rejecting branded RAM match {ram_match.ram.name} because RAM is described generically")
            is_specific_ram = False

        if ram_match.ram and is_specific_ram:
            result.ram = ram_match.ram.model_dump() if hasattr(ram_match.ram, 'model_dump') else ram_match.ram.__dict__
            result.ram_confidence = ram_match.confidence
            result.ram_method = ram_match.method

        # If no specific match, try brand+capacity+DDR type fallback
        # Only match if the RAM brand appears in RAM-related context
        # BUT: If RAM is described generically (e.g., "16GB DDR4 3200 MHz"), skip brand fallback
        # Get the RAM line for checking brand context - use full_text to preserve newlines
        ram_line_for_context = ""
        ram_keywords = ['ram', 'operativ', 'atmina', 'memory', 'ddr', 'ram-', 'gb ram', 'atmiņa', 'atmiņas']
        lines = full_text.lower().split('\n')
        for line in lines:
            for kw in ram_keywords:
                if kw in line:
                    ram_line_for_context = line
                    break
            if ram_line_for_context:
                break

        if not result.ram and ram_capacity and ram_ddr_type and not ram_is_generic:
            # Extract frequency from text (e.g., "2400MHz")
            freq_match = re.search(r'(\d{3,4})\s*mhz', normalized)
            extracted_freq = int(freq_match.group(1)) if freq_match else None

            # Search for RAMs where the brand or model appears NEAR RAM keywords
            text_lower = normalized.lower()

            # Get RAM-related context
            # First try to find a section with RAM keywords
            ram_context = ""

            # Look for RAM keywords in text
            text_lower = normalized.lower()
            for kw in ram_keywords:
                if kw in text_lower:
                    # Found RAM keyword - extract surrounding context (100 chars before/after)
                    kw_pos = text_lower.find(kw)
                    start = max(0, kw_pos - 100)
                    end = min(len(text_lower), kw_pos + 100)
                    ram_context = text_lower[start:end]
                    break

            # If no RAM keyword found, use full text
            if not ram_context:
                ram_context = text_lower

            best_match = None
            best_score = 0

            for ram in self.ram_matcher.rams:
                if ram.capacity_gb != ram_capacity:
                    continue
                # Check if DDR type matches
                ram_ddr = None
                ram_freq = None
                if ram.speed:
                    ddr_match = re.search(r'ddr(\d+)', ram.speed.lower())
                    if ddr_match:
                        ram_ddr = f"DDR{ddr_match.group(1)}"
                    # Extract frequency from speed (e.g., "DDR4-2400")
                    freq_m = re.search(r'(\d{4})', ram.speed)
                    if freq_m:
                        ram_freq = int(freq_m.group(1))
                if ram_ddr and ram_ddr != ram_ddr_type:
                    continue

                # Check if brand or model appears in RAM context (not just anywhere)
                ram_name_lower = ram.name.lower()
                brand = ram.name.split()[0].lower() if ram.name else ""

                # NEW: Check if brand is mentioned in SSD context but NOT in RAM context
                # This prevents "Kingston" from SSD section from matching Kingston RAM
                # when RAM is described generically
                brand_in_ssd_context = False
                ssd_keywords = ['ssd', 'cietie diski', 'cietais disks', 'nvme', 'm.2']

                # Find ALL occurrences of SSD keywords, not just the first one
                for kw in ssd_keywords:
                    start_pos = 0
                    while True:
                        kw_pos = text_lower.find(kw, start_pos)
                        if kw_pos == -1:
                            break
                        # Check if brand appears within 50 chars of SSD keyword
                        ssd_context_start = max(0, kw_pos - 50)
                        ssd_context_end = min(len(text_lower), kw_pos + 50)
                        ssd_context = text_lower[ssd_context_start:ssd_context_end]
                        if brand in ssd_context:
                            brand_in_ssd_context = True
                            break
                        # Move past this occurrence for next search
                        start_pos = kw_pos + 1
                    if brand_in_ssd_context:
                        break

                # If brand is in SSD context but NOT in RAM line (narrower context), skip this RAM
                # Use ram_line_for_context (the specific line with RAM keyword) instead of ram_context
                if ram_line_for_context:
                    brand_in_ram_line = brand in ram_line_for_context
                else:
                    brand_in_ram_line = brand in ram_context

                if brand_in_ssd_context and not brand_in_ram_line:
                    continue  # Skip this RAM - brand is from SSD section, not RAM

                # NEW: Check if brand is mentioned in PSU context but NOT in RAM context
                # This prevents "EVGA" from PSU section from matching EVGA RAM
                # when RAM is described generically
                brand_in_psu_context = False
                psu_keywords = ['psu', 'barošanas', 'bloc', 'power', 'supply', 'watt', 'w']

                # Find ALL occurrences of PSU keywords
                for kw in psu_keywords:
                    start_pos = 0
                    while True:
                        kw_pos = text_lower.find(kw, start_pos)
                        if kw_pos == -1:
                            break
                        # Check if brand appears within 50 chars of PSU keyword
                        psu_context_start = max(0, kw_pos - 50)
                        psu_context_end = min(len(text_lower), kw_pos + 50)
                        psu_context = text_lower[psu_context_start:psu_context_end]
                        if brand in psu_context:
                            brand_in_psu_context = True
                            break
                        # Move past this occurrence for next search
                        start_pos = kw_pos + 1
                    if brand_in_psu_context:
                        break

                # If brand is in PSU context but NOT in RAM line (narrower context), skip this RAM
                if ram_line_for_context:
                    brand_in_ram_line = brand in ram_line_for_context
                else:
                    brand_in_ram_line = brand in ram_context

                if brand_in_psu_context and not brand_in_ram_line:
                    continue  # Skip this RAM - brand is from PSU section, not RAM

                # Skip fallback matching for generic/ambiguous brand names like "HP", "Dell"
                # These brands alone don't indicate specific RAM - need model name
                # NOTE: EVGA is primarily a PSU/GPU brand - RAM should only match if model name is explicit
                generic_brands = {'hp', 'dell', 'lenovo', 'acer', 'asus', 'msi', 'gigabyte', 'evga'}

                # Short brand names (2-3 chars) need word boundaries to avoid false matches
                # e.g., "SK" in "disks" shouldn't match SK Hynix
                short_brands = {'sk', 'hp'}

                # Special handling for "g. skill" / "gskill"
                brand_in_ram_context = False
                if 'g.skill' in ram_name_lower or 'gskill' in ram_name_lower:
                    if any(x in ram_context for x in ['g.skill', 'gskill', 'g. skill']):
                        brand_in_ram_context = True
                elif 'hyperx' in ram_name_lower and 'hyperx' in ram_context:
                    # HyperX is mentioned in text - match any HyperX RAM
                    brand_in_ram_context = True
                elif brand and brand in ram_context:
                    # Check if brand is in the RAM-specific context
                    # For generic PC brands (HP, Dell), require model name too
                    if brand in generic_brands:
                        brand_in_ram_context = False  # Don't match on generic brand alone
                    elif brand in short_brands:
                        # Short brands need word boundaries to avoid false matches
                        # e.g., "SK" should not match "disks"
                        brand_pattern = r'\b' + re.escape(brand) + r'\b'
                        if re.search(brand_pattern, ram_context, re.IGNORECASE):
                            brand_in_ram_context = True
                        else:
                            brand_in_ram_context = False
                    else:
                        brand_in_ram_context = True

                # Also check for model series in RAM context
                model_in_ram_context = False
                model_keywords = ['ripjaws', 'vengeance', 'fury', 'dominator', 'trident', 'ballistix', 'flare', 'aorus', 'renegade', 'hyperx']
                for kw in model_keywords:
                    if kw in ram_name_lower and kw in ram_context:
                        model_in_ram_context = True
                        break

                # Special handling for Kingston HyperX - check if HyperX is mentioned in RAM context
                if not model_in_ram_context and 'hyperx' in ram_context:
                    if 'hyperx' in ram_name_lower:
                        model_in_ram_context = True

                # Special handling for "Corsair Vengeance" - extract variant from text
                if not model_in_ram_context and 'corsair' in ram_name_lower and 'corsair' in ram_context:
                    # Check for Vengeance variant in text (LPX, RGB, RGB Pro, etc.)
                    if 'vengeance' in ram_name_lower and 'vengeance' in ram_context:
                        # Check which variant is mentioned
                        vengeance_variants = ['lpx', 'rgb pro', 'rgb', 'led', 'performance']
                        text_variant = None
                        ram_variant = None
                        for variant in vengeance_variants:
                            if variant in ram_context:
                                text_variant = variant
                                break
                        for variant in vengeance_variants:
                            if variant in ram_name_lower:
                                ram_variant = variant
                                break
                        # If both have same variant or no variant specified, it's a match
                        if text_variant == ram_variant or (text_variant is None and ram_variant is None):
                            model_in_ram_context = True
                        # If text says just "Vengeance" without variant, match any Vengeance
                        elif text_variant is None and 'vengeance' in ram_context:
                            model_in_ram_context = True

                # For generic PC brands, require BOTH brand + model name match
                # For short brands without word boundary match, also skip
                if brand in generic_brands and not model_in_ram_context:
                    continue  # Skip this RAM if only generic brand matches

                # Skip if brand is short and doesn't have word boundary match
                if brand in short_brands and not brand_in_ram_context:
                    continue

                if brand_in_ram_context or model_in_ram_context:
                    # Score based on frequency match and model match
                    score = 1
                    if model_in_ram_context:
                        score += 5  # Bonus for model name match
                    if extracted_freq and ram_freq:
                        if ram_freq == extracted_freq:
                            score += 10  # Exact frequency match
                        elif abs(ram_freq - extracted_freq) <= 100:
                            score += 5   # Close frequency match
                    if best_match is None or score > best_score:
                        best_match = ram
                        best_score = score

            if best_match:
                result.ram = best_match.model_dump() if hasattr(best_match, 'model_dump') else best_match.__dict__
                result.ram_confidence = 0.6
                result.ram_method = f'brand_capacity_fallback_{ram_capacity}gb'

        # If still no match, use generic fallback
        # Also infer DDR type from CPU socket if available
        if not result.ram and ram_capacity:
            # Try to infer DDR type from CPU socket
            inferred_ddr = ram_ddr_type
            if result.cpu and not inferred_ddr:
                cpu_socket = result.cpu.get('socket', '')
                inferred_ddr = self._get_ddr_type_for_socket(cpu_socket)

            ddr_type = inferred_ddr or 'DDR4'
            result.ram = self.get_generic_ram(ram_capacity, ddr_type)
            result.ram_confidence = 0.5
            result.ram_method = f'fallback_{ddr_type.lower()}_{ram_capacity}gb'

        # Match SSD
        ssd_capacity = self._extract_ssd_capacity(full_text)

        # Check for explicitly mentioned SSD brand in SSD context
        # This helps prioritize matches when brand is explicitly stated (e.g., "SSD: Crucial 1TB")
        explicit_ssd_brand = self._extract_ssd_brand_from_context(normalized)

        ssd_match = None
        is_brand_specific_match = False

        # If an explicit brand is found, try to match only that brand first
        if explicit_ssd_brand:
            # Filter SSDs to only those from the explicit brand
            brand_ssds = [s for s in self.ssd_matcher.ssds
                          if s.brand.lower() == explicit_ssd_brand.lower()]
            if brand_ssds:
                # Create a temporary matcher with only this brand's SSDs
                from src.scraper.ssd_matcher import SSDMatcher
                brand_matcher = SSDMatcher(brand_ssds)
                ssd_match = brand_matcher.match_listing(full_text, extracted_capacity=ssd_capacity)

                # Check if the match is truly specific (model name appears in text)
                # If not, treat it as if no match was found
                if ssd_match.ssd:
                    ssd_model_normalized = normalize_text(ssd_match.ssd.model)
                    # Split model into parts and check if any substantial part is in the text
                    model_parts = [p for p in re.split(r'[/\s\-]+', ssd_model_normalized) if len(p) >= 3]

                    # Check for exact model match or substantial partial match
                    # Single generic words like "pro", "evo", "plus" don't count
                    generic_model_words = {'pro', 'evo', 'plus', 'x', 's', 'lite', 'ultra'}
                    has_specific_model_match = False

                    for part in model_parts:
                        if part in normalized and part not in generic_model_words:
                            has_specific_model_match = True
                            break

                    # Also check if this looks like a portable/external SSD
                    # Portable SSDs like X9 Pro should not match desktop/laptop listings
                    is_portable = any(kw in ssd_match.ssd.model.lower() for kw in
                                      ['x9', 'x8', 'x6', 'x10', 'portable', 'external'])
                    if is_portable and 'portable' not in normalized and 'external' not in normalized:
                        # This is a portable SSD but listing doesn't mention portability
                        has_specific_model_match = False

                    if not has_specific_model_match:
                        # No specific model match - discard this result
                        ssd_match = None

                # If no specific model matched but we have the brand and capacity,
                # use a generic fallback for this brand
                if not ssd_match and ssd_capacity:
                    ssd_match = self._create_generic_ssd_match(explicit_ssd_brand, ssd_capacity)
                    is_brand_specific_match = True

        # If no match yet (no explicit brand or brand match failed), use full matcher
        # NOTE: If we created a brand-specific generic fallback (is_brand_specific_match=True),
        # we should NOT run the full matcher - the explicit brand mention takes priority
        if not ssd_match and not is_brand_specific_match:
            ssd_match = self.ssd_matcher.match_listing(full_text, extracted_capacity=ssd_capacity)

        # Use matched SSD if it's an exact match or model_part match
        # AND the brand is mentioned in the text
        # AND the model name actually appears in the text (to avoid false matches)
        is_specific_ssd = False
        if ssd_match.ssd:
            ssd_brand = normalize_text(ssd_match.ssd.brand)
            ssd_model = normalize_text(ssd_match.ssd.model)

            # Check if brand is in text (with fuzzy matching for typos)
            has_brand = ssd_brand in normalized
            if not has_brand:
                # Try fuzzy matching for common typos (e.g., "Kinsgotn" -> "Kingston")
                words_in_text = normalized.split()
                for word in words_in_text:
                    if len(word) >= 5:  # Only check substantial words
                        similarity = fuzz.ratio(word, ssd_brand)
                        if similarity >= 75:  # 75% similarity threshold
                            has_brand = True
                            break

            # Also check if the brand from the matched SSD appears in SSD context
            # using fuzzy matching
            ssd_brand_lower = ssd_match.ssd.brand.lower()

            # Look for brand near SSD keywords
            ssd_keywords = ['ssd', 'cietie diski', 'cietais disks', 'm.2', 'nvme', 'sata']
            ssd_brand_in_ssd_context = False
            for kw in ssd_keywords:
                if kw in normalized:
                    kw_pos = normalized.find(kw)
                    # Check if brand appears within 50 chars of SSD keyword
                    context_start = max(0, kw_pos - 50)
                    context_end = min(len(normalized), kw_pos + 50)
                    context = normalized[context_start:context_end]
                    if ssd_brand_lower in context:
                        ssd_brand_in_ssd_context = True
                        break
                    # Also try fuzzy matching in context
                    if not ssd_brand_in_ssd_context:
                        context_words = context.split()
                        for word in context_words:
                            if len(word) >= 5:
                                similarity = fuzz.ratio(word, ssd_brand_lower)
                                if similarity >= 75:
                                    ssd_brand_in_ssd_context = True
                                    break

            # Check model match more flexibly (handle "sx8200 pro/s11 pro" vs "sx8200 pro")
            has_model_in_text = False
            if ssd_model in normalized:
                has_model_in_text = True
            else:
                # Try checking model parts
                model_parts = re.split(r'[\/\s\-]+', ssd_model)
                for part in model_parts:
                    if len(part) > 3 and part in normalized:
                        has_model_in_text = True
                        break

            is_exact = ssd_match.method.split('+')[0] == 'exact'
            is_model_part = 'model_part' in ssd_match.method
            is_capacity_match = 'capacity_exact' in ssd_match.method or 'capacity_near' in ssd_match.method

            # Check if the matched model is commonly a RAM model (not SSD)
            # These models should only match if there's explicit SSD context
            commonly_ram_models = ['renegade', 'fury', 'vengeance', 'ripjaws', 'trident',
                                   'dominator', 'ballistix', 'flare', 'aegis', 'hyperx']
            model_is_commonly_ram = any(ram_model in ssd_model.lower() for ram_model in commonly_ram_models)

            # Check for SSD keywords in text
            ssd_keywords_present = any(kw in normalized for kw in ['ssd', 'cietie diski', 'cietais disks', 'm.2', 'nvme', 'sata', 'cietnis'])

            # Accept if: exact match, OR (model_part AND model in text AND (brand in text OR brand in SSD context))
            # BUT: if model is commonly a RAM model, require SSD keywords in text OR explicit SSD context
            # ALSO: accept brand-specific generic fallbacks (is_brand_specific_match=True)
            is_specific_ssd = is_exact or (is_model_part and has_model_in_text and (has_brand or ssd_brand_in_ssd_context)) or is_brand_specific_match

            # Reject matches for commonly-RAM models if no SSD keywords present
            if is_specific_ssd and model_is_commonly_ram and not ssd_keywords_present and not ssd_brand_in_ssd_context:
                is_specific_ssd = False

            # NEW: Treat WD color series (Green, Blue, Black, Red) as generic when exact model isn't specified
            # "WD Green" alone should be generic, "WD Green SN350" would be specific
            wd_color_series = {'green', 'blue', 'black', 'red', 'purple', 'gold', 'sn350', 'sn570', 'sn770', 'sn850'}
            if is_specific_ssd and ssd_match.ssd:
                ssd_model_lower = ssd_match.ssd.model.lower()
                ssd_brand_lower = ssd_match.ssd.brand.lower() if ssd_match.ssd.brand else ""
                # Check if the ONLY matched part is a WD color series name
                if ssd_brand_lower == 'wd' or ssd_brand_lower == 'western digital':
                    # Get what was matched from the text
                    matched_model_parts = []
                    for part in re.split(r'[/\s\-]+', ssd_model_lower):
                        if part in normalized.lower():
                            matched_model_parts.append(part)

                    # If only color series name was matched (not specific model like SN350)
                    # and the method is just capacity_near (no exact model match), treat as generic
                    if (set(matched_model_parts) <= wd_color_series and
                        'capacity_near' in ssd_match.method and
                        not any(x in ssd_model_lower for x in ['sn350', 'sn570', 'sn770', 'sn850', 'sa400', 'mx', '870', '980', '970', '870', '860'])):
                        is_specific_ssd = False

        # Generic-model guard: references whose model is just a generic word (e.g., "SSD")
        # should not count as specific unless the brand appears in SSD context.
        if is_specific_ssd and ssd_match.ssd:
            generic_models = {'ssd', 'solid', 'drive', 'hard', 'harddrive'}
            ssd_model_lower = ssd_match.ssd.model.lower()
            ssd_brand_lower = ssd_match.ssd.brand.lower() if ssd_match.ssd.brand else ""
            if ssd_model_lower in generic_models and not ssd_brand_in_ssd_context:
                is_specific_ssd = False

        if ssd_match.ssd and is_specific_ssd:
            ssd_data = ssd_match.ssd.model_dump() if hasattr(ssd_match.ssd, 'model_dump') else ssd_match.ssd.__dict__
            # Add name field for display
            ssd_data['name'] = f"{ssd_match.ssd.brand} {ssd_match.ssd.model}"
            result.ssd = ssd_data
            result.ssd_confidence = ssd_match.confidence
            result.ssd_method = ssd_match.method
            logger.info(f"[SSD DEBUG] Set result.ssd: {result.ssd}")

        # If no specific match, try brand+capacity fallback
        if not result.ssd and ssd_capacity:
            # Search for SSDs where the brand or model appears in the text
            text_lower = normalized.lower()
            best_match = None
            best_score = 0

            for ssd in self.ssd_matcher.ssds:
                if ssd.capacity_gb:
                    # Use tolerance-based matching like the main matcher
                    tolerance = min(max(ssd_capacity * 0.1, 20), 100)
                    if abs(ssd.capacity_gb - ssd_capacity) > tolerance:
                        continue
                else:
                    continue

                ssd_name_lower = f"{ssd.brand} {ssd.model}".lower()
                ssd_brand = ssd.brand.lower() if ssd.brand else ""
                model_lower = ssd.model.lower() if ssd.model else ""

                # If "patriot" is explicitly mentioned in an SSD context, only match Patriot SSDs
                if self._brand_in_ssd_context(text_lower, 'patriot'):
                    if ssd_brand != 'patriot':
                        continue  # Skip non-Patriot SSDs when Patriot is explicitly mentioned
                    else:
                        # Patriot is mentioned - force brand_in_text
                        brand_in_text = True
                        # Check if model appears for scoring
                        if model_lower in text_lower:
                            model_in_text = True
                            model_score = 20
                        else:
                            model_in_text = False
                            model_score = 0

                        # Calculate score and potentially select this SSD
                        score = 5 + model_score
                        if best_match is None or score > best_score:
                            best_match = ssd
                            best_score = score
                        continue  # Skip to next SSD

                # If "goodram" is explicitly mentioned in an SSD context, only match Goodram SSDs
                if self._brand_in_ssd_context(text_lower, 'goodram'):
                    if ssd_brand != 'goodram':
                        continue
                    else:
                        brand_in_text = True
                        if model_lower in text_lower:
                            model_in_text = True
                            model_score = 20
                        else:
                            model_in_text = False
                            model_score = 0
                        score = 5 + model_score
                        if best_match is None or score > best_score:
                            best_match = ssd
                            best_score = score
                        continue

                # If "samsung" is explicitly mentioned in an SSD context, only match Samsung SSDs
                # This prevents "HyperX Fury" from interfering with "Samsung 500GB SSD"
                if self._brand_in_ssd_context(text_lower, 'samsung'):
                    if ssd_brand != 'samsung':
                        continue  # Skip non-Samsung SSDs when Samsung is explicitly mentioned
                    else:
                        # Samsung is mentioned - force brand_in_text
                        brand_in_text = True
                        # Check if model appears for scoring
                        if model_lower in text_lower:
                            model_in_text = True
                            model_score = 20
                        else:
                            model_in_text = False
                            model_score = 0

                        # Calculate score and potentially select this SSD
                        score = 5 + model_score
                        if best_match is None or score > best_score:
                            best_match = ssd
                            best_score = score
                        continue  # Skip to next SSD

                # If "kingston" is explicitly mentioned in an SSD context, only match Kingston SSDs
                if self._brand_in_ssd_context(text_lower, 'kingston'):
                    if ssd_brand != 'kingston':
                        continue  # Skip non-Kingston SSDs when Kingston is explicitly mentioned
                    else:
                        # Kingston is mentioned - force brand_in_text
                        brand_in_text = True
                        # Check if model appears for scoring
                        if model_lower in text_lower:
                            model_in_text = True
                            model_score = 20
                        else:
                            model_in_text = False
                            model_score = 0

                        # Calculate score and potentially select this SSD
                        score = 5 + model_score

                        # NVMe bonus for Kingston - prefer 1000GB over 960GB when no model specified
                        # and prefer NVMe drives when NVMe is mentioned
                        nvme_bonus = 0
                        if 'nvme' in text_lower or 'm.2' in text_lower:
                            if ssd.interface and 'nvme' in ssd.interface.lower():
                                nvme_bonus = 8

                        # Capacity match bonus: prefer exact 1000GB match over 960GB
                        # when listing says "1TB" (1000GB)
                        capacity_bonus = 0
                        if ssd.capacity_gb:
                            capacity_diff = abs(ssd.capacity_gb - ssd_capacity)
                            if capacity_diff == 0:
                                capacity_bonus = 10  # Exact match
                            elif capacity_diff <= 50:
                                capacity_bonus = 3   # Close match

                        score += nvme_bonus + capacity_bonus

                        if best_match is None or score > best_score:
                            best_match = ssd
                            best_score = score
                        continue  # Skip to next SSD

                # If "crucial" is explicitly mentioned in an SSD context, only match Crucial SSDs
                if self._brand_in_ssd_context(text_lower, 'crucial'):
                    if ssd_brand != 'crucial':
                        continue  # Skip non-Crucial SSDs when Crucial is explicitly mentioned
                    else:
                        # Crucial is mentioned - force brand_in_text
                        brand_in_text = True
                        # Check if model appears for scoring
                        if model_lower in text_lower:
                            model_in_text = True
                            model_score = 20
                        else:
                            model_in_text = False
                            model_score = 0

                        # Calculate score and potentially select this SSD
                        score = 5 + model_score

                        # Capacity match bonus: prefer exact 500GB match
                        capacity_bonus = 0
                        if ssd.capacity_gb:
                            capacity_diff = abs(ssd.capacity_gb - ssd_capacity)
                            if capacity_diff == 0:
                                capacity_bonus = 10  # Exact match
                            elif capacity_diff <= 50:
                                capacity_bonus = 3   # Close match

                        score += capacity_bonus

                        if best_match is None or score > best_score:
                            best_match = ssd
                            best_score = score
                        continue  # Skip to next SSD

                # This handles cases where all text is on one line
                # First, remove GPU context to avoid matching GPU brands as SSD brands
                # e.g., "rtx 3070 (gigabyte)" should not match Gigabyte SSD
                ssd_context = text_lower
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

                # Find SSD brand mentions that appear near SSD keywords
                # NOTE: Intel is excluded because "Intel" in listings almost always refers to the CPU,
                # not Intel SSDs. Intel SSDs should only match when the specific model (e.g., "545s", "660p") is mentioned.
                ssd_brand_keywords = ['samsung', 'kingston', 'wd', 'crucial', 'adata', 'sandisk', 'seagate', 'teamgroup', 'pny', 'netac']
                # Look for patterns like:
                #   - "samsung 500gb ssd" (brand before capacity, SSD after)
                #   - "ssd crucial mx500 1tb" (SSD before brand)
                #   - "wd 1tb nvme" (brand before capacity, NVMe after)
                brand_near_ssd = False
                ssd_context = text_lower

                # First check: SSD keyword anywhere in text with brand nearby (±40 chars)
                for brand in ssd_brand_keywords:
                    if brand in text_lower:
                        brand_pos = text_lower.find(brand)
                        # Check window around brand for SSD keywords
                        window_start = max(0, brand_pos - 40)
                        window_end = min(len(text_lower), brand_pos + 40)
                        window = text_lower[window_start:window_end]

                        if any(kw in window for kw in ['ssd', 'nvme', 'm.2', 'm2', 'solid']):
                            ssd_context = window
                            brand_near_ssd = True
                            break

                # Second check: brand before capacity (original logic)
                if not brand_near_ssd:
                    for brand in ssd_brand_keywords:
                        if brand in text_lower:
                            brand_pos = text_lower.find(brand)
                            # Check if "ssd", "nvme", or "m.2" appears within 30 chars AFTER brand
                            segment_after = text_lower[brand_pos:brand_pos + 30]
                            # Also check that brand comes BEFORE capacity number
                            cap_match = re.search(r'(\d+)\s*(?:gb|tb)', text_lower)
                            if cap_match:
                                cap_pos = cap_match.start()
                                if brand_pos < cap_pos:
                                    segment_around_cap = text_lower[cap_pos:cap_pos + 20]
                                    if any(kw in segment_around_cap for kw in ['ssd', 'nvme', 'm.2']):
                                        ssd_context = text_lower[max(0, brand_pos-10):cap_pos + 30]
                                        brand_near_ssd = True
                                        break

                # If no brand found near SSD keywords, skip
                if not brand_near_ssd:
                    continue

                # If "hyperx" is in SSD context but "samsung" also appears, prefer samsung
                if 'hyperx' in ssd_context and 'samsung' in ssd_context:
                    # Extract samsung segment
                    samsung_pos = ssd_context.find('samsung')
                    ssd_context = ssd_context[samsung_pos:samsung_pos + 80]

                # If "hyperx" is in the SSD context, "fury" is likely RAM, not SSD
                if 'hyperx' in ssd_context:
                    ssd_context = ssd_context.replace('fury', '')  # Remove "fury" from SSD context

                # Check if brand appears in SSD context (not just anywhere in text)
                brand_in_text = False
                ssd_brand = ssd.brand.lower()

                # SPECIAL HANDLING: Check for brand typos using fuzzy matching
                # e.g., "Kinsgotn" should match "Kingston"
                if ssd_brand in ssd_context:
                    brand_in_text = True
                else:
                    # Try fuzzy match for common typos
                    words_in_context = ssd_context.split()
                    for word in words_in_context:
                        if len(word) >= 5:  # Only check substantial words
                            # Check similarity (allow 2-3 char differences for longer words)
                            similarity = fuzz.ratio(word, ssd_brand)
                            if similarity >= 70:  # 70% similarity threshold
                                brand_in_text = True
                                break

                # Check if model appears in SSD context
                model_in_text = False
                model_score = 0
                model_lower = ssd.model.lower()

                # SPECIAL HANDLING: Check for model match even without brand
                # This handles cases like "netac 256gb" where brand extraction failed
                if model_lower in ssd_context:
                    model_in_text = True
                    model_score = 15  # Good score for model match
                elif any(part in ssd_context for part in re.split(r'[/\s\-]+', model_lower) if len(part) >= 3):
                    model_in_text = True
                    model_score = 10  # Partial match

                # Skip generic model names that match everywhere
                generic_models = {'ssd', 'hdd', 'nvme', 'disk', 'storage', 'eon', 'x3', 'extreme', 'aorus'}
                # Also skip WD color series (Green, Blue, Black, Red, Purple, Gold) when not accompanied by specific model number
                # These are descriptive series names, not specific models
                wd_color_series = {'green', 'blue', 'black', 'red', 'purple', 'gold'}

                # Check if any part of the model is generic
                model_parts_for_generic = re.split(r'[/\s\-]+', model_lower)
                if any(part in generic_models for part in model_parts_for_generic):
                    continue

                # For WD SSDs, if only color series is matched (not specific model like SN350), skip
                if ssd_brand == 'wd' or ssd_brand == 'western digital':
                    # Check if we have a specific model number, not just color
                    has_specific_model = any(x in model_lower for x in ['sn350', 'sn570', 'sn770', 'sn850', 'sn500', 'sn700', 'sa400', 'green sata'])
                    only_color_matched = set(model_parts_for_generic) & wd_color_series
                    if only_color_matched and not has_specific_model:
                        # Only color series matched (e.g., "Green"), no specific model - skip
                        continue

                # Check for full model match first - but in SSD context
                if model_lower in ssd_context:
                    model_in_text = True
                    model_score = 20  # Highest score for exact model match
                else:
                    # Split model by common separators and check each part in SSD context
                    model_parts = re.split(r'[/\s\-]+', model_lower)
                    matched_parts = []
                    for part in model_parts:
                        if len(part) > 3 and part in ssd_context:  # Only check substantial parts in SSD context
                            # Skip generic parts like "pro" that could be from "processor" or "professional"
                            if part not in ('pro', 'plus', 'evo', 'plus'):
                                matched_parts.append(part)

                    # Only count as model match if we matched multiple substantial parts
                    # or the brand is also present (prevents "pro" matching alone)
                    if len(matched_parts) >= 2 or (len(matched_parts) == 1 and brand_in_text):
                        model_in_text = True
                        model_score = 10 * len(matched_parts)  # Score based on number of parts matched

                    # Bonus if "pro" is also in SSD context for pro models (but only if brand matched)
                    if model_in_text and 'pro' in model_lower and 'pro' in ssd_context and brand_in_text:
                        model_score += 5

                if brand_in_text or model_in_text:
                    score = 0
                    if brand_in_text:
                        score += 5  # Base score for brand
                    if model_in_text:
                        score += model_score  # Variable score based on match quality

                    # NVMe/SATA bonus: If listing mentions NVMe/M.2, prefer NVMe drives
                    nvme_bonus = 0
                    if 'nvme' in ssd_context or 'm.2' in ssd_context:
                        # Check if this SSD is NVMe
                        if ssd.interface and 'nvme' in ssd.interface.lower():
                            nvme_bonus = 8  # Significant bonus for NVMe match
                    elif 'sata' in ssd_context and ssd.interface and 'sata' in ssd.interface.lower():
                        nvme_bonus = 3  # Smaller bonus for SATA match when SATA is mentioned

                    score += nvme_bonus

                    # Accept match if:
                    # 1. BOTH brand AND model match with score >= 15 (specific model match)
                    # 2. Brand-only match is acceptable if NVMe context matches (brand + nvme_bonus >= 10)
                    accept_match = False
                    if brand_in_text and model_in_text and score >= 15:
                        accept_match = True
                    elif brand_in_text and nvme_bonus >= 8 and score >= 13:
                        # Brand + NVMe context match - accept even without specific model
                        accept_match = True

                    if accept_match:
                        if best_match is None or score > best_score:
                            best_match = ssd
                            best_score = score

            if best_match:
                result.ssd = best_match.model_dump() if hasattr(best_match, 'model_dump') else best_match.__dict__
                result.ssd_confidence = 0.6
                result.ssd_method = f'brand_capacity_fallback_{ssd_capacity}gb'

        # If still no match, use generic fallback
        if not result.ssd and ssd_capacity:
            # Apply fallback SSD when capacity is known but no exact match
            result.ssd = {
                'id': -1,  # Negative ID indicates generic/synthetic
                'brand': 'Generic',
                'model': f'{ssd_capacity}GB SSD',
                'name': f'Generic {ssd_capacity}GB SSD',
                'capacity_gb': ssd_capacity,
                'type': 'SATA',
                'price': 30.0 if ssd_capacity <= 256 else 50.0 if ssd_capacity <= 512 else 80.0
            }
            result.ssd_confidence = 0.5
            result.ssd_method = f'fallback_{ssd_capacity}gb_ssd'

        # Check for multiple SSDs
        self._match_multiple_ssds(full_text, normalized, result)

        # Match Case BEFORE PSU so we can strip the case line/brand from the
        # text used for PSU matching. Otherwise case brands like "Antec" pollute
        # the PSU context and beat the real PSU brand (Deepcool).
        case_match = self.case_matcher.match_listing(full_text, price)
        # Only use matched case if the model appears in case-related context
        if case_match.case:
            case_name_lower = case_match.case.name.lower()
            brand = case_name_lower.split()[0] if case_name_lower else ""
            model_part = ' '.join(case_match.case.name.split()[1:]) if len(case_match.case.name.split()) > 1 else ""

            # Get case-related context
            case_context_lines = []
            for line in text_lower.split('\n'):
                if any(kw in line for kw in ['korpuss', 'case', 'korpusa', 'tower', 'atx', 'rgb vent']):
                    case_context_lines.append(line)
            case_context = ' '.join(case_context_lines)

            # Require model part to appear in case context OR high confidence exact match.
            # Strip trailing version suffixes (e.g., "V1", "V2") from the model part
            # so "Aerocool Viewport Mini V2" still matches "Aerocool Viewport Mini korpuss".
            model_part_stripped = re.sub(r'\s+(v|rev|version|mk)\s*\d+(?:\.\d+)?\s*$', '', model_part, flags=re.IGNORECASE).strip()
            has_model_in_case_context = model_part and (
                model_part.lower() in case_context or
                (model_part_stripped and model_part_stripped.lower() in case_context)
            )
            is_high_confidence = case_match.confidence >= 0.9 and case_match.method.startswith('exact')

            if has_model_in_case_context or is_high_confidence:
                result.case = case_match.case.model_dump() if hasattr(case_match.case, 'model_dump') else case_match.case.__dict__
                result.case_confidence = case_match.confidence
                result.case_method = case_match.method

        if not result.case:
            # Apply fallback case
            result.case = {'name': 'Generic PC Case', 'price': 15.0}
            result.case_confidence = 0.5
            result.case_method = 'fallback_generic'

        # Build a PSU-specific copy of the text with the matched case stripped
        # so case brands (e.g. "Antec") don't contaminate PSU scoring.
        psu_full_text = full_text
        psu_normalized = normalized
        psu_text_lower = text_lower
        if result.case and result.case.get('id') and result.case.get('id') != -1:
            case_name = result.case.get('name', '')
            if case_name:
                # Remove the whole case name substring
                psu_full_text = re.sub(r'\b' + re.escape(case_name) + r'\b', '', psu_full_text, flags=re.IGNORECASE)
                psu_normalized = re.sub(r'\b' + re.escape(case_name) + r'\b', '', psu_normalized, flags=re.IGNORECASE)
                psu_text_lower = re.sub(r'\b' + re.escape(case_name) + r'\b', '', psu_text_lower, flags=re.IGNORECASE)
        # Always remove the literal "korpuss" / "case" line tail from PSU text,
        # but only up to the next sentence boundary so we don't swallow whole paragraphs.
        for case_kw in ['korpuss', 'korpusa', 'case', 'tower']:
            psu_full_text = re.sub(r'\b' + case_kw + r'[^.\n]*', '', psu_full_text, flags=re.IGNORECASE)
            psu_normalized = re.sub(r'\b' + case_kw + r'[^.\n]*', '', psu_normalized, flags=re.IGNORECASE)
            psu_text_lower = re.sub(r'\b' + case_kw + r'[^.\n]*', '', psu_text_lower, flags=re.IGNORECASE)
        psu_full_text = re.sub(r'\s+', ' ', psu_full_text).strip()
        psu_normalized = re.sub(r'\s+', ' ', psu_normalized).strip()
        psu_text_lower = re.sub(r'\s+', ' ', psu_text_lower).strip()

        # Match PSU
        psu_match = self.psu_matcher.match_listing(psu_full_text, price)
        psu_wattage = self._extract_psu_wattage(psu_full_text)

        # Check if PSU is mentioned in text - if not, don't use matched PSU, use generic
        psu_keywords = ['psu', 'barosana', 'barošana', 'block', 'bloks', 'barošanas',
                        'powersupply', 'power supply', 'blok', 'barošana', 'barošanas']
        has_psu_mention = any(kw in psu_text_lower for kw in psu_keywords)

        # Also consider wattage patterns like "650W" as PSU indicators
        has_wattage_mention = bool(re.search(r'\d{3,4}w', psu_text_lower))
        has_psu_mention = has_psu_mention or has_wattage_mention

        # Also check if the matched PSU name contains motherboard keywords - reject if so
        mb_keywords_in_psu = False
        if psu_match.psu:
            psu_name_lower = psu_match.psu.name.lower()
            # Check for motherboard-specific terms in PSU name
            if any(kw in psu_name_lower for kw in ['gaming b', 'b450', 'b550', 'b760', 'x570', 'aorus elite', 'tuf gaming b']):
                mb_keywords_in_psu = True
                logger.warning(f"Rejecting PSU match '{psu_match.psu.name}' - contains motherboard keywords")

        if psu_match.psu and has_psu_mention and not mb_keywords_in_psu:
            # Only use matched PSU if PSU is explicitly mentioned AND doesn't have MB keywords
            result.psu = psu_match.psu.model_dump() if hasattr(psu_match.psu, 'model_dump') else psu_match.psu.__dict__
            result.psu_confidence = psu_match.confidence
            result.psu_method = psu_match.method
        elif psu_wattage:
            # Try brand+wattage fallback
            # Only match if PSU brand appears near PSU keywords
            psu_context_lines = []
            for line in psu_text_lower.split('\n'):
                # Skip lines that are clearly about motherboard or other components
                if any(kw in line for kw in ['pamat plate', 'motherboard', 'mb:', 'plate', 'korpuss', 'case:', 'gpu:', 'video:']):
                    continue
                if any(kw in line for kw in ['psu', 'barosana', 'barošana', 'block', 'bloks', 'power supply', '600w', '650w', '750w', 'silentium']):
                    psu_context_lines.append(line)
            psu_context = ' '.join(psu_context_lines)

            # Normalize psu_context to fix typos like 'chieftek' -> 'chieftec'
            psu_context_normalized = psu_context.replace('chieftek', 'chieftec')

            for psu in self.psu_matcher.psus:
                if psu.wattage:
                    # Use tolerance for wattage matching
                    if abs(psu.wattage - psu_wattage) > 50:
                        continue
                else:
                    continue
                # Check if brand appears in PSU context (handle multi-word brands like "be quiet")
                brand_in_psu_context = False
                if hasattr(psu, 'brand') and psu.brand:
                    psu_brand_norm = normalize_text(psu.brand)
                    if psu_brand_norm in psu_context_normalized:
                        brand_in_psu_context = True
                else:
                    # Try first word(s) of name
                    name_words = psu.name.lower().split()
                    if len(name_words) >= 2:
                        # Try "be quiet" style brands
                        two_word = f"{name_words[0]} {name_words[1]}"
                        if two_word in psu_context_normalized:
                            brand_in_psu_context = True
                    if not brand_in_psu_context and name_words[0] in psu_context_normalized:
                        brand_in_psu_context = True

                if brand_in_psu_context:
                    result.psu = psu.model_dump() if hasattr(psu, 'model_dump') else psu.__dict__
                    result.psu_confidence = 0.6
                    result.psu_method = f'brand_wattage_fallback_{psu_wattage}w'
                    break

        # If still no PSU, use generic fallback with extracted wattage if available
        if not result.psu:
            if psu_wattage:
                # Use the wattage extracted from the text
                result.psu = {'name': f'Generic {psu_wattage}W PSU', 'wattage': psu_wattage, 'price': 45.0}
                result.psu_confidence = 0.5
                result.psu_method = f'fallback_{psu_wattage}w_mentioned'
            elif result.gpu:
                result.psu = {'name': 'Generic 650W PSU', 'wattage': 650, 'price': 55.0}
                result.psu_confidence = 0.5
                result.psu_method = 'fallback_gpu_detected'
            else:
                result.psu = {'name': 'Generic 400W PSU', 'wattage': 400, 'price': 35.0}
                result.psu_confidence = 0.5
                result.psu_method = 'fallback_no_gpu'

        # Match Motherboard
        if self.motherboard_matcher:
            mb_match = self.motherboard_matcher.match_listing(full_text)
            if mb_match.motherboard:
                result.motherboard = mb_match.motherboard.model_dump() if hasattr(mb_match.motherboard, 'model_dump') else mb_match.motherboard.__dict__
                result.motherboard_confidence = mb_match.confidence
                result.motherboard_method = mb_match.method
                
                # If the listing explicitly says a micro-ATX form factor (e.g., "B450M")
                # but the matched board's model does not, prefer a matching board whose
                # model actually contains that suffix. This fixes cases where a generic
                # B450 board is returned for a "Asus B450M" listing.
                text_lower = full_text.lower()
                mb_model_lower = (result.motherboard.get('model') or '').lower()
                mb_brand_lower = (result.motherboard.get('brand') or '').lower()
                mb_chipset_lower = (result.motherboard.get('chipset') or '').lower()
                for suffix in ['b450m', 'b550m', 'b760m', 'a620m']:
                    if suffix in text_lower and suffix not in mb_model_lower:
                        candidates = [
                            mb for mb in self.motherboard_matcher.motherboards
                            if (mb.brand or '').lower() == mb_brand_lower
                            and (mb.chipset or '').lower() == mb_chipset_lower
                            and suffix in (mb.model or '').lower()
                        ]
                        if candidates:
                            # Prefer the shortest model name as a simple proxy for the
                            # budget/entry-level variant when the listing gives no suffix.
                            chosen = min(candidates, key=lambda mb: len((mb.model or '').replace(' ', '')))
                            result.motherboard = chosen.model_dump() if hasattr(chosen, 'model_dump') else {k: v for k, v in chosen.__class__.__dict__.items() if not k.startswith('_') and not callable(v)}
                            result.motherboard_confidence = 0.7
                            result.motherboard_method = f"{mb_match.method}_microatx_suffix"
                            break

        # Match Monitor (detect if included in sale)
        if self.monitor_matcher:
            # Pass full_text to ensure we capture monitor mentions anywhere in the listing
            mon_match = self.monitor_matcher.match_listing(title, description or "")
            if mon_match[0]:  # (monitor, confidence, method)
                result.monitor = mon_match[0].__dict__ if hasattr(mon_match[0], '__dict__') else mon_match[0]
                result.monitor_confidence = mon_match[1]
                result.monitor_method = mon_match[2]
                result.monitor_confidence = mon_match[1]
                result.monitor_method = mon_match[2]
                result.has_monitor = True
                result.monitor_included = mon_match[2] not in ['none', 'size_only']

        return result

    def get_motherboard_price(self, cpu: Optional[Dict]) -> Optional[float]:
        """Get appropriate motherboard price based on CPU socket."""
        if not cpu:
            return None

        socket = cpu.get('socket') or ''
        socket = socket.lower()
        if not socket:
            return None

        # Direct lookup
        if socket in self.MOTHERBOARD_PRICES:
            return self.MOTHERBOARD_PRICES[socket]

        # Try normalized socket name
        socket_clean = socket.replace(' ', '').replace('-', '').lower()
        for key, price in self.MOTHERBOARD_PRICES.items():
            if key in socket_clean or socket_clean in key:
                return price

        # Default fallback
        return 75.0

    def _extract_vram_mention(self, text: str) -> Optional[int]:
        """Extract VRAM mention from text (in MB)."""
        text_lower = text.lower()

        # First, remove lines that are clearly not GPU specs (RAM, SSD, etc.)
        # This helps avoid picking up "16GB" from "ddr3 16gb" or "16gb ssd"
        lines = text_lower.split('\n')
        gpu_related_text = []
        for line in lines:
            # Skip lines that mention RAM, SSD, NVMe, etc.
            if any(skip in line for skip in ['ram:', 'ddr', 'ssd', 'nvme', 'hdd', 'mb:', 'cpu:', 'psu:', 'm.2']):
                continue
            # Keep lines that mention GPU or look like GPU specs
            if any(gpu in line for gpu in ['gpu', 'video', 'grafika', 'gtx', 'rtx', 'rx', 'geforce', 'radeon']):
                gpu_related_text.append(line)

        gpu_text = ' '.join(gpu_related_text) if gpu_related_text else text_lower

        # Pattern 1: Look for GB after GPU-related words (VRAM, GPU, etc.)
        pattern1 = re.search(r'(\d+)\s?gb\s*(?:gpu|vram|v|video|grafika)', gpu_text)
        if pattern1:
            gb = int(pattern1.group(1))
            if 1 <= gb <= 64:
                return gb * 1024

        # Pattern 2: Look for GB right after GPU model (with possible text in between)
        pattern2 = re.search(r'(?:rx|rtx|gtx)\s*\d{3,4}(?:\s*(?:ti|xt|super|gaming|ventus|strix|gamingx|aorus|windforce|eagle|ftw|xc|kingpin|hybrid|hof|amp|trinity|twin|frozr|armor|phantom|x trio|suprim|ventus|dual|tuf|rog|strix|aero|gaming|g1|wf|oc))?\s*(\d+)\s*gb', gpu_text)
        if pattern2:
            gb = int(pattern2.group(1))
            if 1 <= gb <= 64:
                return gb * 1024

        # Pattern 3: Generic "X GB" near GPU-related keywords
        pattern3 = re.search(r'(?:gpu|video|grafika).*?(\d+)\s*gb', gpu_text)
        if pattern3:
            gb = int(pattern3.group(1))
            if 1 <= gb <= 64:
                return gb * 1024

        return None

    def _extract_ram_capacity(self, text: str) -> Optional[int]:
        """Extract RAM capacity from text in GB."""
        text_lower = text.lower()

        # Pattern 0: "4x8GB" or "4 x 8GB" or "4x 8GB" format - calculate total FIRST
        # This pattern is most reliable for multi-stick RAM configs
        multi_stick_patterns = [
            r'(\d+)\s*x\s*(\d+)\s*gb',             # "4x8GB" or "4 x 8GB"
            r'(\d+)\s*(?:x|×)\s*(\d+)\s*gb',       # "4×8GB" with times symbol
            r'(\d+)x\s*(\d+)\s*gb',                 # "4x 8GB" (no space after x)
            r'(\d+)\s*planks?.*?\d+\s*gb',          # "4 planks ... 8GB"
            r'(\d+)\s*(?:planki|plank|plashki|planku|modules?|sticks?).*?(\d+)\s*gb',  # "4 planki/plashki ... 8GB"
            r'(\d+)x.*?\b(\d+)\s*gb',               # "4x ... 8GB" with word boundary
        ]

        for pattern in multi_stick_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    sticks = int(match.group(1))
                    capacity_per_stick = int(match.group(2))
                    total = sticks * capacity_per_stick
                    if 4 <= total <= 512:  # Reasonable total RAM
                        return total
                except ValueError:
                    pass

        # Pattern 1: Look for RAM-related lines first
        lines = text_lower.split('\n')
        ram_lines = []
        for line in lines:
            if any(kw in line for kw in ['operativ', 'ram', 'atmiņ', 'ddr', 'memory', 'pam']):
                ram_lines.append(line)

        # Try to extract from RAM-related lines first
        ram_text = ' '.join(ram_lines) if ram_lines else text_lower

        # Pattern 2: RAM-specific patterns - look for total capacity first
        total_patterns = [
            r'(\d+)\s*gb\s*(?:total|visas|kopā)',  # "32GB total"
            r'(?:total|visas|kopā)\s*(\d+)\s*gb',
        ]
        for pattern in total_patterns:
            match = re.search(pattern, ram_text)
            if match:
                try:
                    val = int(match.group(1))
                    if 4 <= val <= 512:
                        return val
                except ValueError:
                    pass

        # Pattern 3: Latvian format - "Operativā atmiņa, Gb: 16" or "Gb: 16"
        # Note: normalize_text converts Latvian chars, so "atmiņa" becomes "atmina"
        # Also handle generic "16gb ram" format
        latvian_patterns = [
            r'gb\s*:?\s*(\d+)',  # Gb: 16
            r'atmina\s*,?\s*gb\s*:?\s*(\d+)',  # atmina, Gb: 16 (normalized)
            r'operativa\s+atmina.*?(\d+)\s*gb',  # operativa atmina...16 gb (normalized)
            r'(\d+)\s*gb\s*ram',  # "16gb ram" or "16 gb ram" (explicit RAM mention)
            r'(\d+)gb\s*ram',  # "16gb ram" (no space between number and gb)
        ]
        for pattern in latvian_patterns:
            match = re.search(pattern, ram_text)
            if match:
                try:
                    val = int(match.group(1))
                    if 4 <= val <= 512:
                        return val
                except ValueError:
                    pass

        # Pattern 4: Brand + capacity patterns
        brand_patterns = [
            r'(?:samsung|kingston|corsair|gskill|g\.?skill|crucial|hyperx)[^0-9]{0,30}(\d+)\s*gb',
        ]
        for pattern in brand_patterns:
            match = re.search(pattern, ram_text)
            if match:
                try:
                    val = int(match.group(1))
                    if 4 <= val <= 512:
                        return val
                except ValueError:
                    pass

        # Pattern 4: DDR + capacity
        ddr_patterns = [
            r'ddr\d?\s*[-]?\s*(\d+)\s*gb',
            r'ddr\d?[^a-zA-Z]{0,20}(\d+)\s*gb',
            r'(\d+)\s*gb[^a-zA-Z]{0,20}ddr',
        ]
        for pattern in ddr_patterns:
            match = re.search(pattern, ram_text)
            if match:
                try:
                    val = int(match.group(1))
                    if 4 <= val <= 512:
                        return val
                except ValueError:
                    pass

        # Fallback: generic X GB pattern (filter out GPU VRAM and SSD/HDD)
        gb_matches = list(re.finditer(r'\b(\d+)\s*gb\b', text_lower))
        for match in gb_matches:
            # Get smaller context around the match
            start = max(0, match.start() - 20)
            end = min(len(text_lower), match.end() + 20)
            context = text_lower[start:end]

            # Skip GPU VRAM - look for GPU patterns close to the number
            gpu_patterns = [
                r'gtx\s*\d+\s*gb',
                r'rtx\s*\d+\s*gb',
                r'rx\s*\d+\s*gb',
                r'geforce.*?\d+\s*gb',
                r'radeon.*?\d+\s*gb',
                r'gpu.*?\d+\s*gb',
                r'vram.*?\d+\s*gb',
                r'\d+\s*gb\s*vram',
                r'\d+\s*gb\s*gpu',
            ]
            is_gpu = any(re.search(pattern, context) for pattern in gpu_patterns)
            if is_gpu:
                continue

            # Skip SSD/HDD storage - look for storage patterns
            storage_patterns = [
                r'ssd.*?\d+\s*gb',
                r'hdd.*?\d+\s*gb',
                r'nvme.*?\d+\s*gb',
                r'm\.2.*?\d+\s*gb',
                r'disk.*?\d+\s*gb',
                r'\d+\s*gb\s*ssd',
                r'\d+\s*gb\s*hdd',
                r'\d+\s*gb\s*nvme',
            ]
            is_storage = any(re.search(pattern, context) for pattern in storage_patterns)
            if is_storage:
                continue

            try:
                val = int(match.group(1))
                if 4 <= val <= 512:
                    return val
            except ValueError:
                pass

        return None

    def _extract_ram_ddr_type(self, text: str) -> Optional[str]:
        """Extract DDR type (DDR3, DDR4, DDR5) from text."""
        text_lower = text.lower()

        # Look for RAM-related lines first
        lines = text_lower.split('\n')
        ram_lines = []
        for line in lines:
            if any(kw in line for kw in ['operativ', 'ram', 'atmiņ', 'ddr', 'memory', 'pam']):
                ram_lines.append(line)

        ram_text = ' '.join(ram_lines) if ram_lines else text_lower

        # Check for explicit DDR mentions in RAM context (not GDDR from GPU)
        # Pattern: "DDR4" followed by frequency or capacity
        ddr_patterns = [
            r'ddr\s*(\d+)[-\s]+(?:\d{3,4})',  # DDR4-3600 or DDR4 3600
            r'ddr\s*(\d+)\s*(?:mhz|gb)',       # DDR4 3200MHz or DDR4 16GB
            r'ddr\s*(\d+)\b',                  # Just DDR4
        ]

        for pattern in ddr_patterns:
            ddr_match = re.search(pattern, ram_text)
            if ddr_match:
                ddr_num = ddr_match.group(1)
                if ddr_num in ['3', '4', '5']:
                    return f"DDR{ddr_num}"

        # Check for "DDR" in general (exclude GDDR which is GPU memory)
        ddr_match = re.search(r'\bddr(\d+)', text_lower)
        if ddr_match:
            ddr_num = ddr_match.group(1)
            # Only return if it's a valid DDR version (not GDDR6 which might match)
            if ddr_num in ['3', '4', '5']:
                return f"DDR{ddr_num}"

        return None

    def _extract_ram_frequency(self, text: str) -> Optional[str]:
        """Extract RAM frequency from text (e.g., '3000MHz', 'DDR4-3200')."""
        text_lower = text.lower()

        # Look for RAM-related lines first
        lines = text_lower.split('\n')
        ram_lines = []
        for line in lines:
            if any(kw in line for kw in ['operativ', 'ram', 'atmiņ', 'ddr', 'memory', 'pam']):
                ram_lines.append(line)

        ram_text = ' '.join(ram_lines) if ram_lines else text_lower

        # Pattern 1: Frequency in MHz (e.g., "3000MHz", "3200 MHz")
        freq_patterns = [
            r'(\d{4})\s*mhz',       # 3000MHz or 3000 MHz
            r'ddr[\s-]*(\d)[\s-]*(\d{4})',  # DDR4-3200 or DDR4 3200
            r'(\d{4})\s*mt',        # 3200MT/s
        ]

        for pattern in freq_patterns:
            freq_match = re.search(pattern, ram_text)
            if freq_match:
                if len(freq_match.groups()) > 1:
                    freq = freq_match.group(2)
                else:
                    freq = freq_match.group(1)
                try:
                    val = int(freq)
                    if 2000 <= val <= 10000:  # Valid RAM frequency range
                        return f"DDR-{val}"
                except ValueError:
                    continue

        return None

    def _has_specific_ram_mention(self, text: str) -> bool:
        """Check if text mentions a specific RAM model/brand, not just capacity."""
        text_lower = text.lower()

        # Common RAM brands/models that indicate specific mention
        specific_patterns = [
            r'\bcorsair\b', r'\bkingston\b', r'\bgskill\b', r'\bg\.skill\b', r'\bg\.\s*skill\b',
            r'\bcrucial\b', r'\bteamgroup\b', r'\badata\b', r'\bpatriot\b',
            r'\bsilicon power\b', r'\bklevv\b', r'\bnetac\b', r'\bacer\b',
            r'\bhp\b', r'\bdell\b', r'\blexar\b', r'\bapacer\b', r'\bmushkin\b',
            r'\bgeil\b', r'\bthermaltake\b', r'\bneo forza\b',
            r'\bskhynix\b', r'\bhynix\b', r'\bhyperx\b', r'\bvengeance\b',
            r'\bdominator\b', r'\bripjaws\b', r'\btrident\b', r'\bflare\b',
            r'\bballistix\b', r'\bt-force\b', r'\bdark\b', r'\bfury\b',
            r'\bvalueram\b', r'\bsystem\b', r'\bblu\b', r'\bgreen\b',
        ]

        for pattern in specific_patterns:
            if re.search(pattern, text_lower):
                return True
        return False

    def _is_generic_ram_description(self, text: str) -> bool:
        """
        Check if RAM is described generically (only capacity + DDR type + frequency).

        This prevents matching branded RAM like Kingston ValueRAM when the text says
        something like "16GB DDR4 3200 MHz" but the brand appears elsewhere in the text
        (e.g., from the SSD section).

        Returns True if RAM is described generically, False if a specific brand/model is mentioned.
        """
        text_lower = text.lower()

        # Look for RAM-specific context (around RAM keywords)
        ram_keywords = ['operativ', 'atmiņ', 'atmina', 'ram', 'memory', 'ddr', 'pam']
        ram_context = ""
        lines = text_lower.split('\n')

        for line in lines:
            for kw in ram_keywords:
                if kw in line:
                    ram_context = line
                    break
            if ram_context:
                break

        # If no RAM keyword found, use full text
        if not ram_context:
            ram_context = text_lower

        # Check if specific RAM brand is mentioned in RAM context
        ram_brands = [
            'corsair', 'kingston', 'gskill', 'g.skill', 'g skill', 'crucial',
            'teamgroup', 'adata', 'patriot', 'silicon power', 'klevv', 'netac',
            'acer', 'hp', 'dell', 'lexar', 'apacer', 'mushkin', 'geil',
            'thermaltake', 'neo forza', 'skhynix', 'hynix', 'hyperx'
        ]

        # Check if specific RAM model is mentioned in RAM context
        ram_models = [
            'vengeance', 'fury', 'ripjaws', 'trident', 'dominator', 'ballistix',
            'flare', 'aorus', 'renegade', 'elite', 'neo', 't-force', 'spectrix',
            'sniper', 'value', 'xlr8', 'viper', 'steel', 'aegis', 'valueram',
            'f4-',  # G.Skill model pattern
        ]

        has_brand_in_context = any(brand in ram_context for brand in ram_brands)
        has_model_in_context = any(model in ram_context for model in ram_models)

        # If neither brand nor model is mentioned in RAM context, it's generic
        return not has_brand_in_context and not has_model_in_context

    def _has_specific_ssd_mention(self, text: str) -> bool:
        """Check if text mentions a specific SSD model/brand, not just capacity."""
        text_lower = text.lower()

        # First, remove GPU context to avoid matching GPU brands as SSD brands
        # e.g., "rtx 3070 (gigabyte)" should not match Gigabyte SSD
        gpu_patterns = [
            r'rtx\s*\d{4}', r'gtx\s*\d{3,4}', r'rx\s*\d{3,4}',
            r'geforce\s+rtx\s*\d{4}', r'geforce\s+gtx\s*\d{3,4}',
            r'radeon\s+rx\s*\d{3,4}',
            r'\(\s*gigabyte\s*\)',  # Remove "(gigabyte)" from GPU lines
            r'\(\s*asus\s*\)',       # Remove "(asus)" from GPU lines
            r'\(\s*msi\s*\)',        # Remove "(msi)" from GPU lines
        ]
        for pattern in gpu_patterns:
            text_lower = re.sub(pattern, '', text_lower, flags=re.IGNORECASE)

        # If 'patriot' is mentioned in an SSD context, it's almost certainly a Patriot SSD
        if self._brand_in_ssd_context(text_lower, 'patriot'):
            return True

        # Common SSD brands/models that indicate specific mention
        # NOTE: 'intel' is excluded - in computer listings "Intel" almost always refers to the CPU.
        # Intel SSDs should only match when specific model numbers (like "545s", "660p") are mentioned.
        specific_patterns = [
            r'\bsamsung\b', r'\bkingston\b', r'\bwd\b', r'\bwestern digital\b',
            r'\bcrucial\b', r'\badata\b', r'\bteamgroup\b',
            r'\bsilicon power\b', r'\bseagate\b', r'\btoshiba\b',
            r'\bsk hynix\b', r'\bhynix\b', r'\bacer\b', r'\bhp\b',
            r'\bsabrent\b', r'\bcorsair\b',
            # NOTE: gigabyte, msi, asus are excluded because they commonly appear as GPU brands
            # They should only match SSDs when explicitly in SSD context
            r'\bevo\b', r'\bpro\b', r'\b970\b', r'\b980\b', r'\b870\b',
            r'\b860\b', r'\b850\b', r'\b840\b', r'\bmx\d+\b',
            r'\bsn\d+\b', r'\brocket\b', r'\bmp\d+\b',
            r'\bblue\b', r'\bgreen\b', r'\bred\b', r'\bblack\b',
            r'\bcolorful\b', r'\bxpg\b', r'\bspectrix\b', r'\bgammix\b',
            r'\bapacer\b', r'\blexar\b', r'\btranscend\b', r'\bcaviar\b',
            r'\bmx\d+\b', r'\bsn\d+\b', r'\bcs\d+\b', r'\bwd\d+\b',
            r'\b545s\b', r'\b660p\b', r'\b670p\b', r'\b760p\b',  # Intel SSD specific models
            r'\bp210\b',  # Patriot P210
        ]

        for pattern in specific_patterns:
            if re.search(pattern, text_lower):
                return True
        return False

    def _extract_ssd_brand_from_context(self, text: str) -> Optional[str]:
        """
        Extract an explicitly mentioned SSD brand from SSD context.
        Looks for patterns like "SSD: Crucial 1TB" or "SSD: Samsung 512GB"
        where a brand is explicitly stated near an SSD keyword.

        Prioritizes patterns where brand appears RIGHT AFTER SSD keyword (e.g., "SSD: Crucial")
        over brands that just happen to be in the general vicinity.

        Returns the brand name if found, None otherwise.
        """
        text_lower = text.lower()

        # First, remove GPU context to avoid matching GPU brands
        # e.g., "rtx 3070 (gigabyte)" should not match Gigabyte SSD
        gpu_patterns = [
            r'rtx\s*\d{4}', r'gtx\s*\d{3,4}', r'rx\s*\d{3,4}',
            r'geforce\s+rtx\s*\d{4}', r'geforce\s+gtx\s*\d{3,4}',
            r'radeon\s+rx\s*\d{3,4}',
            r'\(\s*gigabyte\s*\)',  # Remove "(gigabyte)" from GPU lines
            r'\(\s*asus\s*\)',       # Remove "(asus)" from GPU lines
            r'\(\s*msi\s*\)',        # Remove "(msi)" from GPU lines
        ]
        for pattern in gpu_patterns:
            text_lower = re.sub(pattern, '', text_lower, flags=re.IGNORECASE)

        # Check if any SSD-specific brand is mentioned - if so, ignore GPU/MOBO brands
        ssd_specific_brands = ['patriot', 'samsung', 'kingston', 'crucial', 'wd', 'western digital',
                      'intel', 'adata', 'teamgroup', 'corsair',
                      'seagate', 'sandisk', 'silicon power', 'transcend',
                      'netac', 'lexar', 'hp', 'acer', 'goodram']

        # Check if any SSD-specific brand is mentioned
        has_ssd_specific_brand = any(brand in text_lower for brand in ssd_specific_brands)

        # If 'patriot' is mentioned in an SSD context, prioritize it
        if self._brand_in_ssd_context(text_lower, 'patriot'):
            return 'patriot'

        if has_ssd_specific_brand:
            # Only use SSD-specific brands, ignore GPU/MOBO brands
            ssd_brands = ssd_specific_brands
        else:
            # No SSD-specific brand found, can try GPU/MOBO brands
            ssd_brands = ['samsung', 'kingston', 'crucial', 'wd', 'western digital',
                      'intel', 'adata', 'teamgroup', 'corsair', 'gigabyte',
                      'seagate', 'sandisk', 'silicon power', 'transcend',
                      'netac', 'patriot', 'lexar', 'hp', 'acer', 'msi', 'asus', 'goodram']

        # PRIORITY 1: Look for "SSD: Brand" pattern - brand right after SSD with colon
        # This is the most explicit pattern: "SSD: Crucial 1TB"
        ssd_colon_pattern = r'ssd\s*:\s*(\w+)'
        match = re.search(ssd_colon_pattern, text_lower)
        if match:
            potential_brand = match.group(1).lower()
            if potential_brand in ssd_brands:
                return potential_brand

        # PRIORITY 2: Look for "ssd brand" pattern - brand immediately after SSD keyword
        # Pattern: "ssd crucial" or "ssd samsung"
        for brand in ssd_brands:
            # Look for "ssd" followed by brand within 10 chars
            pattern = rf'ssd\s*[:\-]?\s*{brand}\b'
            if re.search(pattern, text_lower):
                return brand

        # PRIORITY 3: Look for SSD keywords and extract surrounding context.
        # Prefer the brand whose occurrence is closest to the SSD keyword so that
        # "Goodram PX500 ... ssd disks" picks Goodram even if another brand (Seagate)
        # appears elsewhere in the same broad window.
        ssd_keywords = ['ssd', 'cietie diski', 'cietais disks', 'm.2', 'nvme']

        best_brand = None
        best_distance = None
        for kw in ssd_keywords:
            for m in re.finditer(kw, text_lower):
                kw_pos = m.start()
                context_start = max(0, kw_pos - 60)
                context_end = min(len(text_lower), kw_pos + 60)
                context = text_lower[context_start:context_end]
                for brand in ssd_brands:
                    for brand_match in re.finditer(r'\\b' + re.escape(brand) + r'\\b', context):
                        distance = abs(brand_match.start() - (kw_pos - context_start))
                        if best_distance is None or distance < best_distance:
                            best_distance = distance
                            best_brand = brand
        if best_brand:
            return best_brand

        return None

    def _create_generic_ssd_match(self, brand: str, capacity_gb: int) -> 'SSDMatchResult':
        """
        Find a real SSD match for an explicitly mentioned brand + capacity.
        This is used when we know the brand (e.g., "SSD: Crucial 1TB") but no specific model is mentioned.

        Searches the database for SSDs matching the brand and capacity, returns the best match.
        If no exact match found, tries to find any SSD from that brand.
        """
        from src.models.schemas import SSDMatchResult

        brand_lower = brand.lower()
        tolerance = min(max(capacity_gb * 0.1, 20), 100)  # 10% tolerance, min 20GB, max 100GB

        # Find all SSDs from this brand with matching capacity
        matching_ssds = []
        for ssd in self.ssd_matcher.ssds:
            if ssd.brand.lower() == brand_lower:
                if ssd.capacity_gb:
                    capacity_diff = abs(ssd.capacity_gb - capacity_gb)
                    if capacity_diff <= tolerance:
                        # Score based on capacity closeness
                        score = 100 - int((capacity_diff / tolerance) * 50)
                        matching_ssds.append((ssd, score, capacity_diff))

        if matching_ssds:
            # Sort by capacity difference (exact matches first), then by score
            matching_ssds.sort(key=lambda x: (x[2], -x[1]))
            best_ssd, score, _ = matching_ssds[0]

            confidence = min(score / 100.0, 1.0)
            return SSDMatchResult(
                ssd=best_ssd,
                confidence=confidence,
                method=f"brand_capacity_match_{brand}_{capacity_gb}gb"
            )

        # If no capacity match, try to find any SSD from this brand as fallback
        brand_ssds = [ssd for ssd in self.ssd_matcher.ssds if ssd.brand.lower() == brand_lower]
        if brand_ssds:
            # Return the first one (could be improved to pick most popular/common)
            return SSDMatchResult(
                ssd=brand_ssds[0],
                confidence=0.5,
                method=f"brand_fallback_{brand}"
            )

        # No SSDs from this brand found - return empty result
        return SSDMatchResult()

    def _extract_ssd_capacity(self, text: str) -> Optional[int]:
        """Extract SSD capacity from text in GB."""
        text_lower = text.lower()

        # Check for combined storage patterns like "1.38 TB (SSD + HDD)" or "500GB SSD + 1TB HDD"
        # These indicate total storage, not SSD-only - skip SSD extraction
        combined_storage_patterns = [
            r'\(\s*ssd\s*\+\s*hdd\s*\)',  # "(SSD + HDD)"
            r'\(\s*hdd\s*\+\s*ssd\s*\)',  # "(HDD + SSD)"
            r'(?:\d+\s*(?:gb|tb)\s+)?ssd\s*\+\s*\d+\s*(?:gb|tb)\s+hdd',  # "1TB SSD + 2TB HDD"
            r'total.*storage',  # "total storage"
        ]
        for pattern in combined_storage_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                # Combined storage mentioned - can't determine SSD-only capacity
                # UNLESS we can find a specific SSD mention with brand
                if not re.search(r'\b(?:kingston|samsung|crucial|wd|adata|netac)\s+\w*\s*\d+\s*(?:gb|tb)', text_lower, re.IGNORECASE):
                    return None

        # Look for SSD-specific patterns that include the word "ssd" or "sdd" typo near the capacity
        # Pattern: "240GB SSD" or "240 GB SSD" or "ssd 240gb" or "sdd 240gb" (typo)
        # PRIORITY: Patterns that explicitly mention SSD/SDD/NVMe first to avoid matching HDD values
        ssd_patterns = [
            # "SSD: 2000GB" or "SSD 2000 GB" - SSD followed by just capacity (no brand) - HIGHEST PRIORITY
            r'\b(?:ssd|sdd)\s*:?\s*(\d{3,4})\s*gb\b',
            # "SSD: Crucial 120GB" - SSD followed by optional colon, optional brand, then capacity
            r'\b(?:ssd|sdd)\s*:?\s*(?:[\w\s]+?)?(\d{3,4})\s*gb\b',
            # "ADATA SU630 256GB" or "Samsung 870 EVO 512GB" - brand + model + capacity
            r'\b(?:intel|samsung|kingston|crucial|wd|western digital|adata|team)\s+[a-z0-9\-]+\s+(\d{3,4})\s*gb\b',
            # "240GB SSD" or "240 GB SSD" - capacity immediately followed by SSD/SDD
            r'(\d{3,4})\s*gb\s+(?:ssd|sdd)\b',
            # "nvme 240gb" or "m.2 240gb"
            r'\b(?:nvme|m\.2)\s+(\d{3,4})\s*gb\b',
            # "240gb nvme" or "240gb m.2"
            r'(\d{3,4})\s*gb\s+(?:nvme|m\.2)\b',
            # "Intel 256GB" or "Samsung 512GB" - brand + capacity (with SSD mentioned elsewhere)
            r'\b(?:intel|samsung|kingston|crucial|wd|western digital|adata|team)\s+(\d{3,4})\s*gb\b',
            # Generic "m2 256GB" or "m.2 256GB"
            r'\bm\.?2\s+(\d{3,4})\s*gb\b',
        ]

        for pattern in ssd_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass

        # Look for SSD-specific patterns first (before generic patterns)
        # Pattern: "netac 256gb ssd" or "kingston nv2 1tb"
        ssd_specific_patterns = [
            r'(?:netac|kingston|samsung|wd|crucial|intel|adata)\s+(?:[a-z0-9\-]+\s+)?(\d{3,4})\s*gb(?:\s+ssd)?',  # "netac 256gb ssd" or "nv2 1tb ssd"
            r'(?:netac|kingston|samsung|wd|crucial|intel|adata)\s+(?:[a-z0-9\-]+\s+)?(\d+(?:\.\d+)?)\s*tb',  # "netac 1tb"
        ]
        for pattern in ssd_specific_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    val = int(match.group(1))
                    if val >= 128:  # SSDs are usually 128GB+
                        return val
                except ValueError:
                    pass

        # Check if SSD/NVMe/M.2 is mentioned anywhere in text
        has_ssd_mention = any(kw in text_lower for kw in ['ssd', 'nvme', 'm.2', 'm2'])

        # If SSD is mentioned, look for capacity numbers more broadly
        if has_ssd_mention:
            # Look for TB with decimals (1.38TB, 2TB, etc.) - case insensitive
            tb_patterns = [
                r'(\d+(?:\.\d+)?)\s*tb\s+ssd\b',
                r'\bssd\s+(\d+(?:\.\d+)?)\s*tb\b',
                r'(\d+(?:\.\d+)?)\s*tb\s+(?:nvme|m\.2)',
                r'(?:nvme|m\.2)\s+(\d+(?:\.\d+)?)\s*tb',
                r'ssd\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*tb\b',  # "SSD: 1TB" or "SSD-1TB"
            ]
            for pattern in tb_patterns:
                match = re.search(pattern, text_lower, re.IGNORECASE)
                if match:
                    try:
                        return int(float(match.group(1)) * 1000)
                    except ValueError:
                        pass

            # Look for SSD-specific GB patterns - NOT generic GPU VRAM
            # Must have SSD keyword somewhere in the line/phrase
            ssd_line_pattern = r'(?:^|\n|;)\s*[^.\n;]*\b(\d{3,4})\s*gb\b[^.\n;]*\b(?:ssd|nvme|m\.2|m2)'
            ssd_match = re.search(ssd_line_pattern, text_lower, re.MULTILINE)
            if ssd_match:
                try:
                    val = int(ssd_match.group(1))
                    if val >= 128:
                        return val
                except ValueError:
                    pass

            # Alternative: SSD keyword BEFORE capacity
            ssd_before_pattern = r'\b(?:ssd|nvme|m\.2|m2)\s+[^.\n;]*?\b(\d{3,4})\s*gb'
            ssd_before_match = re.search(ssd_before_pattern, text_lower)
            if ssd_before_match:
                try:
                    val = int(ssd_before_match.group(1))
                    if val >= 128:
                        return val
                except ValueError:
                    pass

        # TB patterns - more flexible (support decimals like 1.38TB)
        tb_patterns = [
            r'(\d+(?:\.\d+)?)\s*tb\s+ssd\b',
            r'\bssd\s+(\d+(?:\.\d+)?)\s*tb\b',
            r'\b(?:nvme|m\.2)\s+(\d+(?:\.\d+)?)\s*tb\b',
            r'(\d+(?:\.\d+)?)\s*tb\s+(?:nvme|ssd|m\.2)',
            r'\bssd.*?(\d+(?:\.\d+)?)\s*tb\b',
            r'(\d+(?:\.\d+)?)\s*tb\b.*?(?:ssd|nvme|m\.2)',
        ]

        for pattern in tb_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(float(match.group(1)) * 1000)
                except ValueError:
                    pass

        # Model-specific patterns (e.g., "A55 512 GB" or "Patriot P210 128GB")
        model_patterns = [
            r'\b(?:a55|s55|a60|a65|s60|s70|mx500|870\s*evo|980\s*pro|sn770|sn850|cs\d+|wd\s*blue|wd\s*black)[\s\-]+(\d{3,4})\s*gb\b',
            r'\b(?:patriot)\s+p210\s+(\d{3,4})\s*gb\b',  # "Patriot P210 128GB"
            r'\bp210\s+(\d{3,4})\s*gb\b',  # "P210 128GB"
        ]

        for pattern in model_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    pass

        return None

    def _extract_psu_wattage(self, text: str) -> Optional[int]:
        """Extract PSU wattage from text, ignoring CPU socket designations like LGA1151."""
        text_lower = text.lower()
        # Strip CPU socket labels before wattage extraction so LGA1151v2, LGA1200, LGA1700, AM4, AM5 don't become watts.
        text_lower = re.sub(r'\blga\s*\d+(?:\s*v?\d+)?', '', text_lower)
        text_lower = re.sub(r'\bam[45]\b', '', text_lower)
        text_lower = re.sub(r'\bsocket\s+\d+', '', text_lower)

        # Common wattage patterns
        patterns = [
            r'(\d{3,4})\s*w',           # 530W, 650 W
            r'(\d{3,4})\s* watt',       # 650 watt
            r'barosanas\s+bloks.*?\d{3,4}',  # Latvian: "Barošanas bloks" followed by number
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    wattage = int(match.group(1))
                    if 300 <= wattage <= 2000:  # Reasonable PSU wattage range
                        return wattage
                except ValueError:
                    pass

        # Also check for wattage in PSU model names (e.g., "CX750M", "RM650X")
        # Pattern: look for 3-4 digit numbers near PSU keywords or in Corsair/EVGA/Seasonic model patterns
        psu_model_patterns = [
            r'cx(\d{3,4})m',            # Corsair CX750M
            r'rm(\d{3,4})x?',          # Corsair RM750, RM750X
            r'sf(\d{3,4})',             # Corsair SF750
            r'tx(\d{3,4})',             # Corsair TX750
            r'vs(\d{3,4})',             # Corsair VS650
            r'pq(\d{3,4})g?',           # Deepcool PQ750G
            r'pf(\d{3,4})',             # Deepcool PF700
            r'gd(\d{3,4})',             # EVGA GD750
            r'gq(\d{3,4})',             # EVGA GQ750
            r'ga(\d{3,4})',             # EVGA GA750
            r'gm(\d{3,4})',             # EVGA GM750
            r'focus\s*gx?\s*(\d{3,4})',  # Seasonic Focus GX750
            r'core\s*(\d{3,4})',         # Seasonic Core GM650
        ]

        for pattern in psu_model_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    wattage = int(match.group(1))
                    if 300 <= wattage <= 2000:
                        return wattage
                except ValueError:
                    pass

        return None

    def _match_multiple_ssds(self, full_text: str, normalized: str, result: ComputerMatchResult) -> None:
        """
        Check for multiple SSDs in the listing and add them to result.additional_ssds.
        Handles cases where multiple SSDs of same capacity are listed.
        """
        text_lower = full_text.lower()

        # Find all SSD capacity mentions
        # Pattern: capacity followed by SSD keyword, or SSD keyword followed by capacity
        ssd_mentions = []

        # Pattern 1: "128GB SSD" or "500GB SSD" (allow optional dash/colon between)
        pattern1 = re.finditer(r'(\d{3,4})\s*gb\s*[-:]?\s*(?:ssd|nvme|m\s*\.\s*2)', text_lower)
        for match in pattern1:
            capacity = int(match.group(1))
            # Get context around this match
            start = max(0, match.start() - 50)
            end = min(len(text_lower), match.end() + 20)
            context = text_lower[start:end]
            ssd_mentions.append((capacity, context, match.start()))

        # Pattern 2: "SSD 128GB" or "NVMe 500GB" (allow optional dash/colon and "M. 2" spacing)
        pattern2 = re.finditer(r'(?:ssd|nvme|m\s*\.\s*2)\s*[-:]?\s*(\d{3,4})\s*gb', text_lower)
        for match in pattern2:
            capacity = int(match.group(1))
            start = max(0, match.start() - 50)
            end = min(len(text_lower), match.end() + 20)
            context = text_lower[start:end]
            ssd_mentions.append((capacity, context, match.start()))

        # Pattern 3: "119GB Patriot P210 128GB (SATA (SSD))" - capacity before brand/model with SSD at end
        # This handles the case where there's text between the capacity and SSD keyword
        pattern3 = re.finditer(r'(\d{3,4})\s*gb\s+\w+.*?\(.*?ssd.*?\)', text_lower)
        for match in pattern3:
            capacity = int(match.group(1))
            start = max(0, match.start() - 50)
            end = min(len(text_lower), match.end() + 20)
            context = text_lower[start:end]
            ssd_mentions.append((capacity, context, match.start()))

        # Remove duplicates (same position) - but keep same-capacity SSDs at different positions
        unique_mentions = []
        seen_positions = set()
        for capacity, context, pos in ssd_mentions:
            # Use exact position with 15-char tolerance to allow same-capacity SSDs
            # that are mentioned separately (e.g., two identical SSDs) while collapsing
            # repeated tokens like "512 GB SSD / 512 GB M.2" on the same short phrase.
            is_duplicate = False
            for seen_pos in seen_positions:
                if abs(pos - seen_pos) < 15:
                    is_duplicate = True
                    break
            if not is_duplicate:
                seen_positions.add(pos)
                unique_mentions.append((capacity, context))

        # If we found more than one SSD, add extras to result
        if len(unique_mentions) > 1:
            result.additional_ssds = []
            for capacity, context in unique_mentions[1:]:  # Skip first one (already in result.ssd)
                # Try to find the brand whose occurrence is closest to the capacity/SSD keyword.
                ssd_brand = None
                best_distance = None
                center = len(context) // 2
                for brand in ['samsung', 'kingston', 'crucial', 'wd', 'intel', 'adata',
                              'netac', 'teamgroup', 'silicon power', 'transcend', 'patriot',
                              'gigabyte', 'msi', 'asrock', 'asus', 'lexar', 'goodram']:
                    for brand_match in re.finditer(r'\\b' + re.escape(brand) + r'\\b', context):
                        distance = abs(brand_match.start() - center)
                        if best_distance is None or distance < best_distance:
                            best_distance = distance
                            ssd_brand = brand.title()

                # Try to find actual SSD match from database
                ssd_match = None
                if ssd_brand:
                    # Search for SSD with matching brand and capacity
                    tolerance = min(max(capacity * 0.1, 20), 100)
                    for ssd in self.ssd_matcher.ssds:
                        if ssd.brand.lower() == ssd_brand.lower() and ssd.capacity_gb:
                            if abs(ssd.capacity_gb - capacity) <= tolerance:
                                ssd_match = ssd
                                break

                if ssd_match:
                    # Use actual SSD from database
                    ssd_info = {
                        'id': ssd_match.id,
                        'brand': ssd_match.brand,
                        'model': ssd_match.model,
                        'capacity_gb': ssd_match.capacity_gb,
                        'type': ssd_match.interface or ('NVMe' if 'nvme' in context else 'SATA'),
                        'price': 50.0  # SSDReference doesn't have price, use default
                    }
                else:
                    # Generic SSD
                    ssd_info = {
                        'id': -1,
                        'brand': ssd_brand or 'Generic',
                        'model': f'{capacity}GB SSD',
                        'capacity_gb': capacity,
                        'type': 'NVMe' if 'nvme' in context else 'SATA',
                        'price': 30.0 if capacity <= 256 else 50.0 if capacity <= 512 else 80.0
                    }
                result.additional_ssds.append(ssd_info)

    def _brand_in_ssd_context(self, text_lower: str, brand: str, window: int = 80) -> bool:
        """Return True if the brand appears within `window` chars of an SSD keyword.

        This prevents RAM/PSU brands (e.g. 'Patriot Viper' RAM) from being treated
        as SSD brands when they are not in an SSD context.
        """
        ssd_keywords = ['ssd', 'cietie diski', 'cietais disks', 'm.2', 'm2', 'nvme', 'solid']
        for brand_match in re.finditer(r'\\b' + re.escape(brand) + r'\\b', text_lower):
            bpos = brand_match.start()
            segment = text_lower[max(0, bpos - window):min(len(text_lower), bpos + window)]
            # Ignore brand occurrences that sit inside a clear RAM line
            ram_line_indicators = ['ram', 'operativ', 'atmiņ', 'atmina', 'ddr', 'viper', 'vengeance', 'fury']
            if any(kw in segment for kw in ram_line_indicators) and not any(kw in segment for kw in ssd_keywords):
                continue
            if any(kw in segment for kw in ssd_keywords):
                return True
        return False

    def _has_integrated_graphics_only(self, text: str) -> bool:
        """Check if text only mentions integrated graphics (not discrete GPU)."""
        text_lower = text.lower()

        # Patterns that indicate integrated graphics only
        integrated_patterns = [
            r'intel\s+(?:uhd|hd|xe)\s+graphics',  # Intel UHD Graphics, Intel HD Graphics, Intel Xe
            r'intel\s+graphics\s+\d+',  # Intel Graphics 630
            r'amd\s+vega\s+\d+',  # AMD Vega (integrated)
            r'amd\s+radeon\s+vega',  # AMD Radeon Vega
        ]

        for pattern in integrated_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _get_ddr_type_for_socket(self, socket: str) -> Optional[str]:
        """Get typical DDR type for a CPU socket."""
        ddr2_sockets = ['lga775', 'lga771']  # Older Xeons and Core 2 era
        ddr3_sockets = ['lga1150', 'lga1155', 'lga1156', 'am3+', 'am3', 'fm2+', 'fm2', 'fm1']
        ddr4_sockets = ['lga1151', 'lga1200', 'lga1700', 'am4', 'am5', 'lga2011', 'lga2011-3', 'lga2066']
        ddr5_sockets = ['lga1700', 'am5']  # Note: LGA1700 and AM5 support both DDR4 and DDR5

        socket_lower = socket.lower() if socket else ''
        # Remove any whitespace or dashes for comparison
        socket_clean = socket_lower.replace(' ', '').replace('-', '')

        if socket_clean in ['lga1700', 'am5']:
            # These support both DDR4 and DDR5 - can't determine from socket alone
            return None
        elif socket_clean in ddr2_sockets:
            return 'DDR2'
        elif socket_clean in ddr3_sockets:
            return 'DDR3'
        elif socket_clean in ddr4_sockets:
            return 'DDR4'
        elif socket_clean in ddr5_sockets:
            return 'DDR5'
        return None

    def get_generic_ram(self, capacity_gb: int, ddr_type: str = 'DDR4') -> Dict:
        """Get generic RAM price based on capacity and type."""
        # DDR2 prices per GB (older, usually cheaper)
        ddr2_prices = {2: 8, 4: 12, 8: 20}
        # DDR3 prices per GB
        ddr3_prices = {4: 10, 8: 18, 16: 30, 32: 60}
        # DDR4 prices per GB
        ddr4_prices = {8: 15, 16: 25, 32: 45, 64: 90}
        # DDR5 prices per GB
        ddr5_prices = {8: 20, 16: 35, 32: 65, 64: 130}

        if ddr_type == 'DDR2':
            price = ddr2_prices.get(capacity_gb, capacity_gb * 4)
        elif ddr_type == 'DDR3':
            price = ddr3_prices.get(capacity_gb, capacity_gb * 1.8)
        elif ddr_type == 'DDR5':
            price = ddr5_prices.get(capacity_gb, capacity_gb * 2)
        else:
            price = ddr4_prices.get(capacity_gb, capacity_gb * 1.5)

        return {
            'name': f'Generic {capacity_gb}GB {ddr_type}',
            'capacity_gb': capacity_gb,
            'type': ddr_type,
            'price': price
        }

    def get_component_by_id(self, component_type: str, component_id: int) -> Optional[Dict]:
        """Get component details by ID."""
        if component_type == 'cpu':
            cpu = self.cpus.get(component_id)
            return cpu.model_dump() if cpu else None
        elif component_type == 'gpu':
            gpu = self.gpus.get(component_id)
            return gpu.model_dump() if gpu else None
        elif component_type == 'ram':
            ram = self.rams.get(component_id)
            return ram.model_dump() if ram else None
        elif component_type == 'ssd':
            ssd = self.ssds.get(component_id)
            return ssd.model_dump() if ssd else None
        elif component_type == 'psu':
            psu = self.psus.get(component_id)
            return psu.model_dump() if psu else None
        elif component_type == 'case':
            case = self.cases.get(component_id)
            return case.model_dump() if case else None
        elif component_type == 'motherboard':
            mb = self.motherboards.get(component_id)
            return mb.model_dump() if mb else None
        return None