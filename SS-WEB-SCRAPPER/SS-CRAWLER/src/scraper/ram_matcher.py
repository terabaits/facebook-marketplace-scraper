"""RAM matching engine using rapidfuzz."""
import re
from typing import Optional, List, Tuple, Dict
from rapidfuzz import fuzz, process

from src.models.schemas import RAMReference, RAMMatchResult
from src.utils.text import normalize_text
from src.utils.logger import get_logger

logger = get_logger("ram_matcher")


class RAMMatcher:
    """
    Matches scraped RAM listing titles to RAM reference database.
    """

    def __init__(self, ram_list: List[RAMReference]):
        """
        Initialize with RAM reference list.

        Args:
            ram_list: List of RAMReference loaded from database
        """
        self.rams = ram_list
        self._build_index()
        logger.info(f"RAMMatcher initialized with {len(ram_list)} RAM references")

    def _build_index(self):
        """Build search index from RAM references."""
        self.name_to_rams: Dict[str, List[RAMReference]] = {}  # name -> list of RAMs (different specs)
        self.searchable_names = []
        self.brand_to_rams: Dict[str, List[RAMReference]] = {}  # Group RAMs by brand
        self.id_to_ram: Dict[int, RAMReference] = {}  # ID to RAM lookup

        for ram in self.rams:
            # Index by ID
            self.id_to_ram[ram.id] = ram
            
            # Primary name: Name
            norm = normalize_text(ram.name)
            self.searchable_names.append(norm)
            if norm not in self.name_to_rams:
                self.name_to_rams[norm] = []
            self.name_to_rams[norm].append(ram)

            # Also add the pre-computed normalized_name from DB
            if ram.normalized_name:
                if ram.normalized_name not in self.name_to_rams:
                    self.name_to_rams[ram.normalized_name] = []
                    self.searchable_names.append(ram.normalized_name)
                self.name_to_rams[ram.normalized_name].append(ram)

            # Group by brand (extract from name)
            brand_key = normalize_text(ram.name.split()[0]) if ram.name else ""
            if brand_key:
                if brand_key not in self.brand_to_rams:
                    self.brand_to_rams[brand_key] = []
                self.brand_to_rams[brand_key].append(ram)

            # All keyword variants
            for kw in ram.search_keywords:
                if kw:
                    norm_kw = normalize_text(kw)
                    self.searchable_names.append(norm_kw)
                    if norm_kw not in self.name_to_rams:
                        self.name_to_rams[norm_kw] = []
                    self.name_to_rams[norm_kw].append(ram)

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

    def _extract_speed(self, text: str) -> Optional[str]:
        """Extract speed/DDR type from text."""
        # Match patterns like DDR4-3200, DDR5-6000, etc.
        patterns = [
            r'DDR(\d+)-(\d+)',
            r'DDR(\d+)[-\s]+(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ddr_version = match.group(1)
                frequency = match.group(2)
                return f"DDR{ddr_version}-{frequency}"

        # Just DDR version
        ddr_match = re.search(r'DDR(\d+)', text, re.IGNORECASE)
        if ddr_match:
            return f"DDR{ddr_match.group(1)}"

        return None

    def _extract_frequency(self, text: str) -> Optional[int]:
        """Extract frequency in MHz from text."""
        if not text:
            return None
        # Look for patterns like DDR4-3600, 3600MHz, 3600 MHz
        match = re.search(r'(\d{4})', text)
        if match:
            freq = int(match.group(1))
            # Validate reasonable RAM frequencies
            if 400 <= freq <= 10000:
                return freq
        return None

    def _extract_ram_tokens(self, title: str) -> List[str]:
        """Extract RAM-specific tokens from title."""
        tokens = set()
        normalized = normalize_text(title)

        # Brand patterns
        # NOTE: EVGA is excluded - primarily a PSU/GPU brand, RAM should only match if explicit model given
        brand_patterns = [
            r'\bcorsair\b', r'\bkingston\b', r'\bgskill\b', r'\bg\.skill\b', r'\bg\s+skill\b',
            r'\bcrucial\b', r'\bteamgroup\b', r'\badata\b', r'\bpatriot\b',
            r'\bsilicon power\b', r'\bklevv\b', r'\bnetac\b', r'\bacer\b',
            r'\bhp\b', r'\bdell\b', r'\blexar\b', r'\bapacer\b', r'\bmushkin\b',
            r'\bgeil\b', r'\bthermaltake\b', r'\bneo forza\b',
            r'\bskhynix\b', r'\bhynix\b', r'\bhyperx\b',  # Added HyperX
        ]

        for pattern in brand_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            tokens.update(matches)

        # DDR patterns
        ddr_patterns = [
            r'\bddr[\s-]*(\d+)\b',
            r'\bpc[\s-]*(\d+)\b',
            r'\bddr[\s-]*(\d+)[\s-]*(\d+)\b',
        ]

        for pattern in ddr_patterns:
            matches = re.findall(pattern, normalized, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    # Flatten tuple matches (from multiple capture groups)
                    tokens.update(m for m in match if m)
                else:
                    tokens.add(match)

        return list(tokens)

    def _extract_ddr_generation(self, text: str) -> Optional[str]:
        """Extract DDR generation (DDR3, DDR4, DDR5) from text."""
        match = re.search(r'DDR(\d+)', text, re.IGNORECASE)
        if match:
            return f"DDR{match.group(1)}"
        return None

    def _score_ram_match(self, ram: RAMReference, normalized_title: str,
                         extracted_capacity: Optional[int], extracted_speed: Optional[str],
                         extracted_manufacturer: Optional[str] = None,
                         extracted_model: Optional[str] = None) -> Tuple[float, str]:
        """
        Score how well a RAM matches the listing.
        Returns (score, method).
        """
        # Handle tuple input
        if isinstance(normalized_title, tuple):
            normalized_title = normalized_title[0] if normalized_title else ""
        if not isinstance(normalized_title, str):
            normalized_title = str(normalized_title) if normalized_title else ""

        score = 0.0
        method = ""

        # Check for exact name match
        ram_name = normalize_text(ram.name)
        if ram_name in normalized_title:
            score = 100.0
            method = "exact"
        else:
            # Fuzzy match
            score = fuzz.token_set_ratio(normalized_title, ram_name)
            method = "fuzzy"

        # Check for alphanumeric-only name match (e.g., "skhynix" vs "sk hynix")
        ram_name_nospace = re.sub(r'[^a-z0-9]', '', ram_name)
        title_nospace = re.sub(r'[^a-z0-9]', '', normalized_title)
        if ram_name_nospace in title_nospace:
            score = max(score, 100.0)
            method = "exact_nospace"
        else:
            # Partial model match - try model number without capacity
            # Extract model part (alphanumeric, usually before capacity)
            model_match = re.search(r'([a-z0-9]+(?:[a-z]*\d*)+)', ram_name_nospace)
            if model_match:
                model_core = model_match.group(1)
                # Remove trailing capacity digits if present
                model_core = re.sub(r'\d+g(b)?$', '', model_core, flags=re.IGNORECASE)
                if model_core and len(model_core) >= 8 and model_core in title_nospace:
                    score = max(score, 95.0)  # High but not perfect
                    method = "model_core_match"

        # Check for model/series match with typo handling
        model_parts = ram_name.split()
        for part in model_parts:
            if len(part) >= 3:
                if part in normalized_title:
                    score += 15  # Boost for partial model match
                    method += "+model_part"
                    break
                # Handle common typos
                elif part == 'hyperx' and 'hiperx' in normalized_title:
                    score += 12  # Slightly less for typo
                    method += "+model_hiperx_typo"
                    break
                elif part == 'fury' and 'furry' in normalized_title:
                    score += 12  # Furry instead of Fury - common typo
                    method += "+model_furry_typo"
                    break

        # Speed/DDR matching bonus + penalty for mismatch
        if extracted_speed and ram.speed:
            ram_speed_norm = normalize_text(ram.speed)
            title_speed_norm = normalize_text(extracted_speed)

            # Extract DDR generations
            ram_ddr = self._extract_ddr_generation(ram.speed)
            title_ddr = self._extract_ddr_generation(extracted_speed)

            # Extract frequencies for exact comparison
            ram_freq = self._extract_frequency(ram.speed)
            title_freq = self._extract_frequency(extracted_speed)

            if ram_speed_norm == title_speed_norm:
                score += 40
                method += "+speed_exact"
            elif ram_freq and title_freq and ram_freq == title_freq:
                # Exact frequency match (e.g., both 3600)
                score += 40
                method += "+freq_exact"
            elif ram_freq and title_freq and ram_freq != title_freq:
                # Different frequency - PENALTY (but less severe to allow model matches)
                freq_diff = abs(ram_freq - title_freq)
                if freq_diff <= 200:  # Within 200MHz (e.g., 3000 vs 3200) - small penalty
                    score -= 15  # Small penalty for close frequencies
                    method += "+freq_close"
                else:
                    # Larger frequency difference - stronger penalty
                    freq_diff_pct = freq_diff / max(ram_freq, title_freq)
                    score -= 40 * (1 + freq_diff_pct)  # -40 to -80 depending on difference
                    method += "+freq_mismatch"
            elif ram_ddr and title_ddr:
                if ram_ddr == title_ddr:
                    # Same DDR generation
                    score += 20
                    method += "+ddr_gen_match"
                else:
                    # Different DDR generation - PENALTY
                    score -= 80
                    method += "+ddr_gen_mismatch"
            else:
                # Partial match without clear DDR info
                score += 10
                method += "+speed_partial"

        # Capacity matching bonus/penalty - STRONGER penalties for mismatches
        if extracted_capacity and ram.capacity_gb:
            capacity_diff = abs(extracted_capacity - ram.capacity_gb)
            if capacity_diff == 0:
                # Perfect capacity match
                score += 40
                method += "+capacity_exact"
            else:
                # Calculate tolerance - RAM capacities are exact, so be strict
                # 2GB vs 4GB is a 100% difference - major mismatch
                capacity_diff_pct = capacity_diff / max(extracted_capacity, ram.capacity_gb)
                if capacity_diff_pct <= 0.25:  # Within 25% (e.g., 8GB vs 6GB)
                    # Close capacity
                    score += 20 * (1 - capacity_diff_pct)
                    method += "+capacity_close"
                else:
                    # Outside tolerance - STRONG penalty
                    score -= 100 * capacity_diff_pct
                    method += "+capacity_mismatch"

        # Manufacturer matching bonus - STRONGER bonus since brand is critical
        # AND penalty for wrong brand
        if extracted_manufacturer:
            # Ensure extracted_manufacturer is a string
            if isinstance(extracted_manufacturer, tuple):
                extracted_manufacturer = extracted_manufacturer[0] if extracted_manufacturer else None
            if not isinstance(extracted_manufacturer, str):
                extracted_manufacturer = str(extracted_manufacturer) if extracted_manufacturer else None

            if extracted_manufacturer:
                # Normalize extracted manufacturer
                extracted_brand_norm = normalize_text(extracted_manufacturer)
                # Get brand from RAM name (first word)
                ram_brand = normalize_text(ram.name.split()[0]) if ram.name else ""

                # Also try matching against full normalized RAM name
                ram_name_norm = normalize_text(ram.name)

                # Check for exact brand match
                brand_matched = False
                if ram_brand == extracted_brand_norm:
                    score += 60  # Strong bonus for brand match
                    method += "+brand_exact"
                    brand_matched = True
                elif extracted_brand_norm in ram_name_norm:
                    score += 40  # Partial brand match
                    method += "+brand_partial"
                    brand_matched = True
                elif 'g.skill' in ram_name_norm and extracted_brand_norm in ['gskill', 'g.skill', 'g skill']:
                    score += 50  # Special handling for G.Skill variations
                    method += "+brand_gskill"
                    brand_matched = True
                elif 'gskill' in ram_name_norm and extracted_brand_norm in ['gskill', 'g.skill', 'g skill']:
                    score += 50
                    method += "+brand_gskill"
                    brand_matched = True
                elif 'crucial' in ram_name_norm and extracted_brand_norm == 'micron':
                    # Micron owns Crucial brand
                    score += 45  # Slightly less than exact match
                    method += "+brand_micron_crucial"
                    brand_matched = True
                elif 'hynix' in ram_name_norm and extracted_brand_norm == 'skhynix':
                    # SK Hynix sometimes written as Skhynix
                    score += 45
                    method += "+brand_skhynix_hynix"
                    brand_matched = True
                elif 'adata' in ram_name_norm and extracted_brand_norm in ['a data', 'adata']:
                    # "A Data" is ADATA
                    score += 50
                    method += "+brand_adata"
                    brand_matched = True
                elif 'kingston' in ram_name_norm and extracted_brand_norm in ['kingstone', 'kingston']:
                    # "Kingstone" typo for Kingston
                    score += 45
                    method += "+brand_kingston"
                    brand_matched = True
                
                # If brand didn't match, apply penalty
                if not brand_matched:
                    score -= 100  # Strong penalty for wrong brand
                    method += "+brand_mismatch"

        # Model matching bonus
        if extracted_model:
            # Ensure extracted_model is a string
            if isinstance(extracted_model, tuple):
                extracted_model = extracted_model[0] if extracted_model else None
            if extracted_model:
                if not isinstance(extracted_model, str):
                    extracted_model = str(extracted_model)
                ram_name_norm = normalize_text(ram.name)
                model_norm = normalize_text(extracted_model)
                if model_norm in ram_name_norm:
                    score += 30
                    method += "+model_exact"

        # Special bonus for "ballistix" in title when RAM name has it
        if 'ballistix' in normalized_title and 'ballistix' in normalize_text(ram.name):
            score += 40
            method += "+ballistix_match"
        
        # Special bonus for "aegis" in title when RAM name has it
        if 'aegis' in normalized_title and 'aegis' in normalize_text(ram.name):
            score += 40
            method += "+aegis_match"
        
        # Special bonus for "trident" in title when RAM name has it
        if 'trident' in normalized_title and 'trident' in normalize_text(ram.name):
            score += 40
            method += "+trident_match"
        
        # Special handling for compound model names like "Viper Steel"
        # If both parts of the compound name are in the title, give a strong bonus
        compound_models = [
            ('viper', 'steel'),  # Viper Steel
            ('vengeance', 'lpx'),  # Vengeance LPX
            ('vengeance', 'rgb'),  # Vengeance RGB
            ('ripjaws', 'v'),  # Ripjaws V
            ('trident', 'z'),  # Trident Z
            ('dominator', 'platinum'),  # Dominator Platinum
        ]
        for part1, part2 in compound_models:
            if part1 in normalized_title and part2 in normalized_title:
                if part1 in normalize_text(ram.name) and part2 in normalize_text(ram.name):
                    score += 50  # Strong bonus for matching compound model
                    method += f"+{part1}_{part2}_match"
                elif part1 in normalize_text(ram.name):
                    # Partial match - at least part1 matches
                    score += 30
                    method += f"+{part1}_partial_match"
        
        # Special bonus for "viper" in title when RAM name has it
        if 'viper' in normalized_title and 'viper' in normalize_text(ram.name):
            score += 40
            method += "+viper_match"
        
        # Special bonus for "steel" in title when RAM name has it (for Viper Steel)
        if 'steel' in normalized_title and 'steel' in normalize_text(ram.name):
            score += 40
            method += "+steel_match"
        
        # Special handling for G.Skill model numbers like F4-3200C16D-32GTZ or F4 3200 C16D 32GTZ
        # Support both hyphenated and space-separated patterns
        gskill_patterns = [
            r'f(\d+)-(\d+)c(\d+)d-?(\d+)(\w+)',  # f4-3200c16d-32gtz or f4-3200c16d32gtz
            r'f(\d+)\s+(\d+)\s*c(\d+)d\s*-?(\d+)(\w+)',  # f4 3200 c16d 32gtz
        ]
        gskill_model_match = None
        for pattern in gskill_patterns:
            gskill_model_match = re.search(pattern, normalized_title)
            if gskill_model_match:
                break
        
        if gskill_model_match:
            # Extract components
            ddr_ver, freq, cas, capacity, variant = gskill_model_match.groups()
            ram_name_lower = ram.name.lower()
            # Check if this RAM matches the G.Skill pattern
            if 'g.skill' in ram_name_lower or 'gskill' in ram_name_lower:
                # Check frequency match (allow 200MHz tolerance for typos like 3000 vs 3200)
                ram_freq_match = re.search(r'(\d{4})', ram_name_lower)
                if ram_freq_match:
                    ram_freq = int(ram_freq_match.group(1))
                    title_freq = int(freq)
                    freq_diff = abs(ram_freq - title_freq)
                    if freq_diff == 0:
                        score += 50
                        method += "+gskill_freq_exact"
                    elif freq_diff <= 200:  # Within 200MHz tolerance
                        score += 40
                        method += "+gskill_freq_close"
                    else:
                        score -= 20
                        method += "+gskill_freq_mismatch"
                # Check capacity match - try both the extracted capacity and title capacity
                if capacity in ram_name_lower:
                    score += 30
                    method += "+gskill_cap_match"
                elif extracted_capacity and str(extracted_capacity) in ram_name_lower:
                    score += 25
                    method += "+gskill_cap_extracted_match"

        # Modules matching (e.g., "2 x 16GB")
        if ram.modules:
            modules_norm = normalize_text(ram.modules)
            # Extract module count from title
            modules_match = re.search(r'(\d+)\s*x\s*(\d+)\s*gb', normalized_title, re.IGNORECASE)
            if modules_match:
                title_modules = f"{modules_match.group(1)} x {modules_match.group(2)}GB"
                if normalize_text(title_modules) == modules_norm:
                    score += 25
                    method += "+modules_exact"
        
        # Penalty for premium variants (RGB/LED) when not explicitly mentioned
        # This prevents matching RGB/LED variants when only base model is mentioned
        ram_name_lower = ram.name.lower()
        has_variant_in_text = False
        for variant in ['lpx', 'rgb', 'led', 'pro']:
            if variant in normalized_title:
                has_variant_in_text = True
                break
        
        if not has_variant_in_text:
            # No specific variant mentioned in text
            if 'corsair' in ram_name_lower and 'vengeance' in ram_name_lower:
                # For Corsair Vengeance, prefer LPX over RGB/LED
                if 'lpx' in ram_name_lower:
                    score += 50  # Bonus for LPX (base model)
                    method += "+lpx_preferred"
                elif any(v in ram_name_lower for v in ['rgb', 'led']):
                    # RGB/LED variant but not mentioned - very strong penalty
                    score -= 200
                    method += "+rgb_not_mentioned"

        return score, method

    def match_listing(self, title: str, extracted_capacity: Optional[int] = None,
                      extracted_speed: Optional[str] = None,
                      extracted_manufacturer: Optional[str] = None,
                      extracted_model: Optional[str] = None,
                      extracted_ddr: Optional[str] = None) -> RAMMatchResult:
        """
        Match a listing title to a RAM reference.

        Args:
            title: The listing title
            extracted_capacity: Capacity extracted from specs (if available)
            extracted_speed: Speed/DDR type extracted from specs (if available)

        Returns:
            RAMMatchResult with matched RAM and confidence
        """
        # Handle tuple input (from database)
        if isinstance(title, tuple):
            title = title[0] if title else ""

        if not title or not isinstance(title, str) or len(title.strip()) < 3:
            return RAMMatchResult()

        normalized = normalize_text(title)
        
        # Remove PSU context to avoid matching PSU brands as RAM brands
        # e.g., "EVGA 1000 GQ" should not match EVGA RAM
        psu_patterns = [
            r'evga\s+\d{3,4}',  # "EVGA 1000", "EVGA 750"
            r'corsair\s+(?:cx|rm|tx|ax|sf)\d{3,4}',  # "Corsair RM750", "Corsair CX650"
            r'cooler\s*master\s+v\d{3,4}',  # "Cooler Master V750"
        ]
        for pattern in psu_patterns:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

        # Extract brand from title
        brand_tokens = self._extract_ram_tokens(title)
        brands_in_title = set()
        for token in brand_tokens:
            # Ensure token is a string (not tuple)
            if isinstance(token, tuple):
                continue
            if isinstance(token, str) and token.lower() in ['corsair', 'kingston', 'gskill', 'g.skill', 'crucial',
                                 'teamgroup', 'adata', 'patriot', 'silicon power',
                                 'klevv', 'netac', 'acer', 'hp', 'dell', 'lexar',
                                 'apacer', 'mushkin', 'geil', 'thermaltake', 'neo forza',
                                 'hynix', 'skhynix', 'sk hynix', 'hyperx']:  # Added HyperX
                brands_in_title.add(token.lower())
        
        # Special handling: For compound model names like "Viper Steel" or "Trident Z",
        # if the compound model parts are in the text, add the implied brand to candidates
        # This handles cases where "patriot" isn't in text but "viper steel" is
        compound_models = {
            ('viper', 'steel'): 'patriot',  # Viper Steel → Patriot
            ('trident', 'z'): 'gskill',     # Trident Z → G.Skill
            ('ripjaws', 'v'): 'gskill',     # Ripjaws V → G.Skill
            ('vengeance', 'lpx'): 'corsair', # Vengeance LPX → Corsair
            ('dominator', 'platinum'): 'corsair', # Dominator Platinum → Corsair
            ('ballistix', 'sport'): 'crucial', # Ballistix Sport → Crucial
        }
        for (part1, part2), implied_brand in compound_models.items():
            if part1 in normalized and part2 in normalized:
                brands_in_title.add(implied_brand)
                break

        # Get candidate RAMs by brand first
        candidates = []
        if brands_in_title:
            for brand in brands_in_title:
                # Direct brand match
                if brand in self.brand_to_rams:
                    candidates.extend(self.brand_to_rams[brand])
                # Map variant brands to index keys
                brand_mappings = {
                    'skhynix': 'sk',
                    'hynix': 'sk',
                    'hyperx': 'kingston',  # HyperX is Kingston's gaming brand
                }
                if brand in brand_mappings:
                    mapped = brand_mappings[brand]
                    if mapped in self.brand_to_rams:
                        candidates.extend(self.brand_to_rams[mapped])
        else:
            candidates = self.rams

        # If we have speed, filter candidates by DDR type
        if extracted_speed:
            ddr_match = re.search(r'DDR(\d+)', extracted_speed, re.IGNORECASE)
            if ddr_match:
                ddr_version = ddr_match.group(1)
                speed_candidates = []
                for ram in candidates:
                    if ram.speed and re.search(rf'DDR{ddr_version}', ram.speed, re.IGNORECASE):
                        speed_candidates.append(ram)
                if speed_candidates:
                    candidates = speed_candidates

        # If we have explicit DDR type, filter candidates
        if extracted_ddr:
            ddr_version = extracted_ddr.lower().replace('ddr', '')
            ddr_candidates = []
            for ram in candidates:
                if ram.speed and re.search(rf'DDR{ddr_version}', ram.speed, re.IGNORECASE):
                    ddr_candidates.append(ram)
            if ddr_candidates:
                candidates = ddr_candidates

        # Score all candidates
        best_ram = None
        best_score = -float('inf')
        best_method = ""

        for ram in candidates:
            score, method = self._score_ram_match(ram, normalized, extracted_capacity,
                                                   extracted_speed, extracted_manufacturer,
                                                   extracted_model)

            if score > best_score:
                best_score = score
                best_ram = ram
                best_method = method

        # Require minimum score of 50 for a match
        if best_ram and best_score >= 50:
            confidence = min(best_score / 100.0, 1.0)
            # Truncate method to fit in database column (100 chars)
            if len(best_method) > 95:
                best_method = best_method[:95] + "+..."
            return RAMMatchResult(
                ram=best_ram,
                confidence=confidence,
                method=best_method
            )

        return RAMMatchResult()

    def get_ram_by_id(self, ram_id: int) -> Optional[RAMReference]:
        """Get a RAM by its ID."""
        for ram in self.rams:
            if ram.id == ram_id:
                return ram
        return None
