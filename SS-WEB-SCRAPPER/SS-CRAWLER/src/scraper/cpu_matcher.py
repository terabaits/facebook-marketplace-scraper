"""CPU matching engine using rapidfuzz."""
import re
from typing import Optional, List, Tuple
from rapidfuzz import fuzz, process

from src.models.schemas import CPUReference, CPUMatchResult
from src.utils.text import normalize_text, extract_cpu_tokens
from src.utils.logger import get_logger

logger = get_logger("cpu_matcher")


class CPUMatcher:
    """
    Matches scraped listing titles to CPU reference database.
    
    Strategy:
    1. Direct token matching on CPU patterns
    2. Fuzzy ratio match for whole title
    3. Intel/AMD processor number matching
    4. Generation-based verification
    5. Confidence scoring for each match
    """
    
    def __init__(self, cpu_list: List[CPUReference]):
        """
        Initialize with CPU reference list.
        
        Args:
            cpu_list: List of CPUReference loaded from database
        """
        self.cpus = cpu_list
        self._build_index()
        logger.info(f"CPUMatcher initialized with {len(cpu_list)} CPUs")
    
    def _build_index(self):
        """Build search index from CPU references."""
        self.name_to_cpu = {}
        self.searchable_names = []
        self.processor_numbers = {}  # Map processor numbers to CPUs
        
        for cpu in self.cpus:
            # Primary name
            norm = normalize_text(cpu.cpu_name)
            self.searchable_names.append(norm)
            self.name_to_cpu[norm] = cpu
            
            # Processor number - store both with and without dash
            proc_num = cpu.processor_number.lower()
            self.processor_numbers[proc_num] = cpu
            # Also store normalized version (no dash)
            proc_num_norm = proc_num.replace('-', '').replace(' ', '')
            if proc_num_norm not in self.processor_numbers:
                self.processor_numbers[proc_num_norm] = cpu
            
            # All keyword variants
            for kw in cpu.search_keywords:
                if kw and kw not in self.name_to_cpu:
                    self.searchable_names.append(kw)
                    self.name_to_cpu[kw] = cpu
    
    def match(self, title: str, description: str = "", base_freq_mhz: Optional[int] = None) -> CPUMatchResult:
        """
        Match listing text to best CPU reference.
        
        Args:
            title: Listing title
            description: Listing description
            base_freq_mhz: Optional base frequency from listing (in MHz)
        
        Returns CPUMatchResult with:
            - cpu: matched CPUReference or None
            - confidence: 0.0-1.0 score
            - method: how the match was made
        """
        full_text = f"{title} {description}".strip()
        
        if not full_text:
            return CPUMatchResult(confidence=0.0, method="none")
        
        normalized = normalize_text(full_text)
        
        # Get candidates based on name matching
        candidates = self._get_candidates_by_name(normalized, full_text, base_freq_mhz)
        
        if not candidates:
            return CPUMatchResult(confidence=0.0, method="none")
        
        # Return best match
        cpu, score = candidates[0]
        method = "name_match"
        if base_freq_mhz and cpu.base_freq:
            method = "name+freq_match"
        
        return CPUMatchResult(
            cpu=cpu,
            confidence=score,
            method=method
        )
    
    def _get_candidates_by_name(self, normalized: str, full_text: str, base_freq_mhz: Optional[int] = None) -> List[Tuple[CPUReference, float]]:
        """Get CPU candidates sorted by name match score."""
        candidates = []
        seen = set()
        
        # Fix common typos
        full_text_fixed = full_text.lower().replace('xenon', 'xeon')
        normalized_fixed = normalized.replace('xenon', 'xeon')
        
        # Strategy 1: Exact processor number matching
        # Look for patterns like i7-14700, i9-14900K, Ryzen 7 7800X, etc.
        cpu_tokens = extract_cpu_tokens(full_text_fixed)
        
        # Sort tokens to prioritize those with version/suffix info (longer tokens first)
        # This ensures "xeone52680v4" is checked before "xeone52680"
        cpu_tokens = sorted(cpu_tokens, key=lambda x: len(x), reverse=True)
        
        for token in cpu_tokens:
            token_norm = token.replace(' ', '').lower()
            
            # Check processor number matches
            # Sort by length (descending) so longer matches are checked first
            # e.g., "ryzen53600x" should be checked before "ryzen53600"
            sorted_proc_nums = sorted(self.processor_numbers.items(), 
                                      key=lambda x: len(x[0]), reverse=True)
            
            for proc_num, cpu in sorted_proc_nums:
                if cpu.id in seen:
                    continue
                
                # Check for exact match (case insensitive)
                if token_norm == proc_num.lower():
                    candidates.append((cpu, 1.0))
                    seen.add(cpu.id)
                    continue
                
                # Check if processor number is contained in token (e.g., "xeonx5650" contains "x5650")
                # BUT: Don't match shorter processor numbers when suffixes are present
                # e.g., "5800x" should NOT match "5800x3d", "3600x" should NOT match "3600"
                proc_num_lower = proc_num.lower().replace(' ', '').replace('-', '')
                if proc_num_lower in token_norm:
                    # CRITICAL FIX: Check if this is a partial match that shouldn't count
                    # e.g., "5160" (ID 3957) should NOT match "r51600" (Ryzen 5 1600)
                    # The processor number should be complete in the token, not just a prefix
                    
                    # Only skip if this is a numeric-only processor number
                    # AND it's being matched against a longer alphanumeric token
                    # AND the processor number is purely numeric (like "5160" for Core 2 Duo E6600)
                    if proc_num_lower.isdigit():
                        # Find where the processor number appears in the token
                        pos = token_norm.find(proc_num_lower)
                        proc_len = len(proc_num_lower)
                        token_len = len(token_norm)
                        
                        # If token continues with digits after the match, it's a partial match
                        if pos + proc_len < token_len and token_norm[pos + proc_len].isdigit():
                            continue
                    
                    # Special check: if token has '3d' suffix, don't match non-3d processors
                    if '3d' in token_norm and '3d' not in proc_num_lower:
                        continue
                    
                    # Special check for Intel F suffix: if token has 'f', processor must also have it
                    # This handles "14400f" vs "14400" cases
                    if token_norm.endswith('f') and not proc_num_lower.endswith('f'):
                        # Token has F suffix but this processor doesn't - skip
                        continue
                    if proc_num_lower.endswith('f') and not token_norm.endswith('f'):
                        # Processor has F suffix but token doesn't - skip (prevents 14400 matching 14400F)
                        continue
                    
                    # Special check for Intel K suffix: if token has 'k', processor must also have it
                    # This handles "14900k" vs "14900" and "14900kf" cases
                    if token_norm.endswith('k') and not proc_num_lower.endswith('k') and not proc_num_lower.endswith('kf'):
                        # Token has K suffix but this processor doesn't - skip (KF has K so it's OK)
                        continue
                    if proc_num_lower.endswith('k') and not token_norm.endswith('k') and not token_norm.endswith('kf'):
                        # Processor has K suffix but token doesn't and token doesn't end with KF - skip
                        continue
                    
                    # Special check for Intel KF suffix: if token has 'kf', processor must also have it
                    if token_norm.endswith('kf') and not proc_num_lower.endswith('kf'):
                        continue
                    if proc_num_lower.endswith('kf') and not token_norm.endswith('kf'):
                        continue
                    
                    # Special check for Intel T suffix: if token has 't', processor must also have it
                    if token_norm.endswith('t') and not proc_num_lower.endswith('t'):
                        continue
                    if proc_num_lower.endswith('t') and not token_norm.endswith('t'):
                        continue
                    
                    # Special check for Intel KS suffix: if token has 'ks', processor must also have it
                    if token_norm.endswith('ks') and not proc_num_lower.endswith('ks'):
                        continue
                    if proc_num_lower.endswith('ks') and not token_norm.endswith('ks'):
                        continue
                    
                    # Special check for AMD G suffix (APU): if token has 'g', processor must also have it
                    # This handles "8700g" vs "8700" and "5600g" vs "5600" cases
                    if token_norm.endswith('g') and not proc_num_lower.endswith('g'):
                        # Token has G suffix but this processor doesn't - skip
                        continue
                    if proc_num_lower.endswith('g') and not token_norm.endswith('g'):
                        # Processor has G suffix but token doesn't - skip (prevents 8700 matching 8700G)
                        continue
                    
                    # Special check for AMD X suffix: if token ends with 'x', prefer processors that also end with 'x'
                    # This handles "3600x" vs "3600" and "5800x" vs "5800" cases
                    if token_norm.endswith('x') and not proc_num_lower.endswith('x'):
                        # Token has X suffix but this processor doesn't - skip unless it's XT
                        if not proc_num_lower.endswith('xt'):
                            continue
                    
                    # Also: if token DOESN'T have 'x' but processor DOES, skip (prevents 3600 from matching 3600X)
                    if not token_norm.endswith('x') and proc_num_lower.endswith('x'):
                        if not proc_num_lower.endswith('xt'):
                            continue
                    
                    # Special check for Xeon v-version: if token has 'v4'/'v3'/etc, prefer matching version
                    # This handles "e52680v4" vs "e52680" cases
                    version_match = re.search(r'v(\d+)$', token_norm)
                    if version_match:
                        # Token has version suffix (v4, v3, etc.)
                        token_version = version_match.group(1)
                        if not proc_num_lower.endswith(f'v{token_version}'):
                            # Processor doesn't have matching version - skip
                            continue
                    else:
                        # Token doesn't have version suffix - skip processors WITH version suffix
                        # to prevent "e52680" from matching "e52680v4"
                        if re.search(r'v\d+$', proc_num_lower):
                            continue
                    
                    # Special check for Intel S suffix: prefer non-S variant when token doesn't have S
                    # This handles "4460" vs "4460s" cases - prefer plain variant
                    # Skip processors with 's' suffix when token doesn't end with 's'
                    if proc_num_lower.endswith('s') and not token_norm.endswith('s'):
                        # Processor has S suffix but token doesn't - skip this processor
                        continue
                    
                    # Also skip non-S processors if token ends with S
                    if token_norm.endswith('s') and not proc_num_lower.endswith('s'):
                        # Token has S suffix but this processor doesn't - skip
                        continue
                    
                    candidates.append((cpu, 0.95))
                    seen.add(cpu.id)
                    continue
                
                # Check for close matches
                proc_num_clean = proc_num.lower().replace('-', '').replace(' ', '')
                token_clean = token_norm.replace('-', '').replace(' ', '')
                
                # SPECIAL HANDLING: Check for AMD Ryzen short form "r5" vs "ryzen5"
                # e.g., token "r51600" should match processor "ryzen51600"
                if token_clean.startswith('r') and len(token_clean) >= 5:
                    # Check if this could be a short Ryzen token
                    # r5 -> ryzen5, r7 -> ryzen7, r9 -> ryzen9
                    ryz_match = re.match(r'r([3579])(\d+)', token_clean)
                    if ryz_match:
                        tier, num = ryz_match.groups()
                        expanded_token = f"ryzen{tier}{num}"
                        if proc_num_clean == expanded_token or proc_num_clean == token_clean:
                            candidates.append((cpu, 0.9))
                            seen.add(cpu.id)
                            continue
                
                if proc_num_clean == token_clean:
                    candidates.append((cpu, 1.0))
                    seen.add(cpu.id)
                    continue
                
                # Partial match check - prioritize exact suffix matching
                if len(token_clean) >= 5:
                    # Check if base numbers match
                    base_match = False
                    
                    # Extract base number (e.g., i914900 from i914900kf)
                    # Intel pattern: i[3579] + digits
                    intel_base_match = re.match(r'(i[3579]\d+)', token_clean)
                    if intel_base_match:
                        token_base = intel_base_match.group(1)
                        proc_intel_base = re.match(r'(i[3579]\d+)', proc_num_clean)
                        if proc_intel_base:
                            proc_base = proc_intel_base.group(1)
                            if token_base == proc_base:
                                base_match = True
                    
                    if base_match:
                        # Extract suffixes
                        suffixes = ['kf', 'ks', 'f', 'k', 't']
                        token_suffix = ''
                        proc_suffix = ''
                        
                        for suffix in suffixes:
                            if token_clean.endswith(suffix):
                                token_suffix = suffix
                                break
                        
                        for suffix in suffixes:
                            if proc_num_clean.endswith(suffix):
                                proc_suffix = suffix
                                break
                        
                        # Prioritize exact suffix matches
                        if token_suffix == proc_suffix:
                            # Exact suffix match - high confidence
                            candidates.append((cpu, 0.98))
                            seen.add(cpu.id)
                        elif token_suffix and not proc_suffix:
                            # Token has suffix but processor doesn't (e.g., i9-14900KF vs i9-14900)
                            # Lower confidence
                            candidates.append((cpu, 0.70))
                            seen.add(cpu.id)
                        elif not token_suffix and proc_suffix:
                            # Token has no suffix but processor does - skip (wrong variant)
                            pass
        
        # Strategy 2: Fuzzy matching if no exact matches
        if not candidates:
            results = process.extract(
                normalized,
                self.searchable_names,
                scorer=fuzz.token_sort_ratio,
                limit=5
            )
            
            for name, score, _ in results:
                cpu = self.name_to_cpu.get(name)
                if cpu and cpu.id not in seen:
                    confidence = score / 100.0
                    if confidence >= 0.60:  # Lower threshold for CPUs
                        candidates.append((cpu, confidence))
                        seen.add(cpu.id)
        
        # Strategy 3: Pattern-based matching
        if not candidates:
            # Intel patterns
            intel_match = re.search(r'i([3579])[-]?\s*(\d{3,5})\s*(k|kf|f|t|ks)?', normalized, re.IGNORECASE)
            if intel_match:
                tier = intel_match.group(1)
                model_num = intel_match.group(2)
                suffix = intel_match.group(3) or ''
                
                for cpu in self.cpus:
                    if cpu.id in seen:
                        continue
                    
                    cpu_norm = normalize_text(cpu.cpu_name)
                    
                    # Check if CPU name contains the pattern
                    if f'i{tier}' in cpu_norm.lower() and model_num in cpu_norm:
                        score = 0.75
                        if suffix and suffix.lower() in cpu_norm.lower():
                            score = 0.90
                        candidates.append((cpu, score))
                        seen.add(cpu.id)
            
            # AMD Ryzen patterns (with series number)
            ryzen_match = re.search(r'ryzen\s*(\d)\s*(\d{4})\s*(x|xt|3d)?', normalized, re.IGNORECASE)
            if ryzen_match:
                series = ryzen_match.group(1)
                model_num = ryzen_match.group(2)
                suffix = ryzen_match.group(3) or ''
                
                for cpu in self.cpus:
                    if cpu.id in seen:
                        continue
                    
                    cpu_norm = normalize_text(cpu.cpu_name)
                    
                    if 'ryzen' in cpu_norm.lower() and model_num in cpu_norm:
                        score = 0.75
                        if suffix and suffix.lower() in cpu_norm.lower():
                            score = 0.90
                        candidates.append((cpu, score))
                        seen.add(cpu.id)
            
            # AMD Ryzen without series number (e.g., "Ryzen 3600" -> match "Ryzen 5 3600")
            ryzen_no_series = re.search(r'ryzen\s+(5|7|9)?\s*(\d{4})\s*(x|xt|3d)?', normalized, re.IGNORECASE)
            if ryzen_no_series:
                possible_series = ryzen_no_series.group(1)  # Might be None
                model_num = ryzen_no_series.group(2)
                suffix = ryzen_no_series.group(3) or ''
                
                for cpu in self.cpus:
                    if cpu.id in seen:
                        continue
                    
                    cpu_norm = normalize_text(cpu.cpu_name)
                    
                    if 'ryzen' in cpu_norm.lower() and model_num in cpu_norm:
                        score = 0.70  # Slightly lower confidence due to missing series
                        if suffix and suffix.lower() in cpu_norm.lower():
                            score = 0.85
                        candidates.append((cpu, score))
                        seen.add(cpu.id)
            
            # AMD Ryzen series-only + frequency (e.g., "Ryzen 5" with 3.60 GHz)
            if base_freq_mhz and not candidates:
                ryzen_series_only = re.search(r'ryzen\s*(\d)', normalized, re.IGNORECASE)
                if ryzen_series_only:
                    series = ryzen_series_only.group(1)
                    # Find Ryzen CPUs of this series with base frequency close to the listing
                    best_freq_cpu = None
                    best_freq_score = 0.0
                    for cpu in self.cpus:
                        if cpu.id in seen:
                            continue
                        cpu_norm = normalize_text(cpu.cpu_name)
                        if 'ryzen' in cpu_norm.lower() and f'ryzen {series}' in cpu_norm.lower():
                            if cpu.base_freq:
                                cpu_freq_mhz = int(cpu.base_freq * 1000)
                                freq_diff = abs(cpu_freq_mhz - base_freq_mhz)
                                # Score based on frequency closeness
                                if freq_diff <= 50:
                                    score = 0.85
                                elif freq_diff <= 100:
                                    score = 0.75
                                elif freq_diff <= 200:
                                    score = 0.65
                                elif freq_diff <= 300:
                                    score = 0.55
                                else:
                                    score = 0.0
                                if score > best_freq_score:
                                    best_freq_score = score
                                    best_freq_cpu = cpu
                    if best_freq_cpu:
                        candidates.append((best_freq_cpu, best_freq_score))
                        seen.add(best_freq_cpu.id)
            
            # Intel Xeon patterns (including typo "xenon")
            xeon_match = re.search(r'xeon\s*([ew])?\s*(\d)[-\s]?(\d{4})', normalized_fixed, re.IGNORECASE)
            if xeon_match:
                series = xeon_match.group(1) or ''  # E, W, or empty
                first_digit = xeon_match.group(2)
                model_num = xeon_match.group(3)
                
                for cpu in self.cpus:
                    if cpu.id in seen:
                        continue
                    
                    cpu_norm = normalize_text(cpu.cpu_name)
                    
                    if 'xeon' in cpu_norm.lower():
                        # Check for model number match
                        full_model = f"{first_digit}{model_num}"
                        if full_model in cpu_norm or model_num in cpu.processor_number.lower():
                            score = 0.75
                            candidates.append((cpu, score))
                            seen.add(cpu.id)
        
        # Sort by confidence score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Re-rank by frequency if available
        if base_freq_mhz and candidates:
            re_ranked = []
            for cpu, score in candidates:
                if cpu.base_freq:
                    # Convert CPU base_freq (GHz) to MHz for comparison
                    cpu_freq_mhz = int(cpu.base_freq * 1000)
                    freq_diff = abs(cpu_freq_mhz - base_freq_mhz)
                    
                    # Boost score based on frequency match
                    if freq_diff == 0:
                        score = min(1.0, score + 0.15)  # Perfect match
                    elif freq_diff <= 100:
                        score = min(1.0, score + 0.10)  # Within 100MHz
                    elif freq_diff <= 200:
                        score = min(1.0, score + 0.05)  # Within 200MHz
                    
                    re_ranked.append((cpu, score))
                else:
                    re_ranked.append((cpu, score))
            
            # Re-sort after boosting
            re_ranked.sort(key=lambda x: x[1], reverse=True)
            return re_ranked
        
        return candidates
    
    def get_candidates(self, text: str, limit: int = 5, base_freq_mhz: Optional[int] = None) -> List[Tuple[CPUReference, float]]:
        """Get top N candidates with scores for manual review."""
        normalized = normalize_text(text)
        candidates = self._get_candidates_by_name(normalized, text, base_freq_mhz)
        return candidates[:limit]
