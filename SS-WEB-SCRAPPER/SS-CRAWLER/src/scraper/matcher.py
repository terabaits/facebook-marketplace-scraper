"""GPU matching engine using rapidfuzz."""
import re
from typing import Optional, List, Tuple
from rapidfuzz import fuzz, process

from src.models.schemas import GPUReference, MatchResult
from src.utils.text import normalize_text, extract_gpu_tokens
from src.utils.logger import get_logger

logger = get_logger("matcher")


class GPUMatcher:
    """
    Matches scraped listing titles to GPU reference database.
    
    Strategy:
    1. Direct token matching on GPU patterns
    2. Fuzzy ratio match for whole title
    3. Keyword matching from search_keywords
    4. VRAM-based verification for variant selection
    5. Number-based fallback matching
    6. Confidence scoring for each match
    """
    
    def __init__(self, gpu_list: List[GPUReference]):
        """
        Initialize with GPU reference list.
        
        Args:
            gpu_list: List of GPUReference loaded from database
        """
        self.gpus = gpu_list
        self._build_index()
        logger.info(f"GPUMatcher initialized with {len(gpu_list)} GPUs")
    
    def _build_index(self):
        """Build search index from GPU references."""
        self.name_to_gpu = {}
        self.searchable_names = []
        
        for gpu in self.gpus:
            # Primary name
            norm = normalize_text(gpu.model)
            self.searchable_names.append(norm)
            self.name_to_gpu[norm] = gpu
            
            # All keyword variants
            for kw in gpu.search_keywords:
                if kw and kw not in self.name_to_gpu:
                    self.searchable_names.append(kw)
                    self.name_to_gpu[kw] = gpu
    
    def _normalize_vram(self, vram_mb: Optional[int]) -> Optional[int]:
        """Normalize VRAM to nearest standard size in MB."""
        if not vram_mb:
            return None
        # Common VRAM sizes: 1GB, 2GB, 3GB, 4GB, 6GB, 8GB, 12GB, 16GB, 24GB, 32GB
        # Convert to GB, round, convert back to MB
        vram_gb = vram_mb / 1024
        if vram_gb < 1.5:
            return 1024  # 1GB
        elif vram_gb < 2.5:
            return 2048  # 2GB
        elif vram_gb < 3.5:
            return 3072  # 3GB
        elif vram_gb < 5:
            return 4096  # 4GB
        elif vram_gb < 7:
            return 6144  # 6GB
        elif vram_gb < 10:
            return 8192  # 8GB
        elif vram_gb < 14:
            return 12288  # 12GB
        elif vram_gb < 20:
            return 16384  # 16GB
        elif vram_gb < 28:
            return 24576  # 24GB
        else:
            return 32768  # 32GB
    
    def _get_vram_match_score(self, gpu_vram: Optional[int], extracted_vram: Optional[int]) -> float:
        """
        Calculate VRAM match confidence.
        Returns 1.0 for perfect match, 0.0-0.9 for partial/near match, 0.0 if unknown.
        """
        if not gpu_vram or not extracted_vram:
            return 0.5  # Unknown - neutral
        
        normalized_gpu = self._normalize_vram(gpu_vram)
        normalized_extracted = self._normalize_vram(extracted_vram)
        
        if normalized_gpu == normalized_extracted:
            return 1.0  # Perfect match
        
        # Near match (e.g., 8000 vs 8192 - 2.3% difference)
        if abs(normalized_gpu - normalized_extracted) <= 512:
            return 0.9
        
        # Moderate mismatch (e.g., 6GB vs 8GB - different tiers but still reasonable)
        if abs(normalized_gpu - normalized_extracted) <= 2048:
            return 0.5
        
        # Large mismatch (e.g., 1.2GB vs 4GB - GTX 570 vs RX 570)
        # This is a significant mismatch, should heavily penalize
        if abs(normalized_gpu - normalized_extracted) <= 4096:
            return 0.2
        
        return 0.0  # Severe mismatch - likely wrong GPU
    
    def match(self, title: str, description: str = "", vram_mb: Optional[int] = None) -> MatchResult:
        """
        Match listing text to best GPU reference.
        
        Args:
            title: Listing title
            description: Listing description
            vram_mb: Optional VRAM size from listing (in MB)
        
        Returns MatchResult with:
            - gpu: matched GPUReference or None
            - confidence: 0.0-1.0 score
            - method: how the match was made
            - vram_verified: whether VRAM matches (if provided)
        """
        # Combine and normalize text
        full_text = f"{title} {description}".strip()
        
        if not full_text:
            return MatchResult(confidence=0.0, method="none")
        
        normalized = normalize_text(full_text)
        
        # Remove price patterns to avoid false matches (e.g., "650" in "EUR 650.00" matching GTX 650)
        # Match patterns like: 650.00, 650,00, eur 650, $650, etc.
        normalized = re.sub(r'\b\d+[.,]\d{2}\b', '', normalized)  # Remove decimal prices
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Get candidates based on name matching
        candidates = self._get_candidates_by_name(normalized, full_text)
        
        if not candidates:
            return MatchResult(confidence=0.0, method="none")
        
        # If we have VRAM data, use it to select best candidate
        if vram_mb and len(candidates) > 1:
            best_candidate = None
            best_score = 0.0
            
            # Check if listing has specific suffix (XT, Ti, Super, etc.)
            has_xt = ' xt ' in f' {normalized} '
            has_ti = ' ti ' in f' {normalized} '
            has_super = 'super' in normalized
            
            for gpu, name_score in candidates:
                vram_score = self._get_vram_match_score(gpu.vram_gb, vram_mb)
                
                # Suffix matching bonus - if listing has XT/Ti/Super, prefer GPU with same suffix
                suffix_bonus = 0.0
                gpu_norm = normalize_text(gpu.model)
                if has_xt and 'xt' in gpu_norm:
                    suffix_bonus = 0.1
                elif has_ti and 'ti' in gpu_norm:
                    suffix_bonus = 0.1
                elif has_super and 'super' in gpu_norm:
                    suffix_bonus = 0.1
                
                # Weight: name match 70%, VRAM match 30%, plus suffix bonus
                combined_score = (name_score * 0.7) + (vram_score * 0.3) + suffix_bonus
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_candidate = (gpu, name_score, vram_score)
            
            if best_candidate:
                gpu, name_score, vram_score = best_candidate
                
                # Determine method based on match quality
                if name_score >= 0.95 and vram_score >= 0.9:
                    method = "exact+vram"
                    confidence = min(1.0, name_score)
                elif vram_score >= 0.9:
                    method = "name+vram_verified"
                    # Strong VRAM match - ensure minimum 75% confidence
                    # This handles "Gigabyte 3060" that matches by number only (65%) 
                    # but has correct VRAM (12GB = RTX 3060 12GB variant)
                    confidence = max(0.75, name_score * 0.95)
                elif vram_score >= 0.6:
                    method = "name+vram_approx"
                    confidence = name_score * 0.85
                else:
                    method = "name+vram_mismatch"
                    confidence = name_score * 0.7  # Penalty for VRAM mismatch
                
                logger.debug(f"VRAM-aware match: {gpu.model} (name={name_score:.2f}, vram={vram_score:.2f})")
                
                return MatchResult(
                    gpu=gpu,
                    confidence=confidence,
                    method=method
                )
        
        # No VRAM data or single candidate - return best name match
        gpu, score = candidates[0]
        return MatchResult(
            gpu=gpu,
            confidence=score,
            method="name_only"
        )
    
    def _get_candidates_by_name(self, normalized: str, full_text: str) -> List[Tuple[GPUReference, float]]:
        """Get GPU candidates sorted by name match score."""
        candidates = []
        seen = set()
        
        # Strategy 1: Exact token matching
        gpu_tokens = extract_gpu_tokens(full_text)
        suffix_pattern = re.compile(r'(\d{3,4})(ti|super|xt|xtx|s)?$')
        
        for token in gpu_tokens:
            token_norm = token.replace(' ', '')
            
            # Check exact normalized_name matches
            for gpu in self.gpus:
                if gpu.normalized_name == token_norm and gpu.id not in seen:
                    candidates.append((gpu, 1.0))
                    seen.add(gpu.id)
            
            # Check if token is contained within normalized_name (e.g., "9800gt" in "geforce9800gt")
            for gpu in self.gpus:
                if gpu.id in seen:
                    continue
                if token_norm in gpu.normalized_name:
                    # Score based on how much of the name matches
                    match_ratio = len(token_norm) / len(gpu.normalized_name)
                    if match_ratio >= 0.5:  # At least half the name matches
                        candidates.append((gpu, 0.90))
                        seen.add(gpu.id)
            
            # Check suffix matches
            suffix_match = suffix_pattern.search(token_norm)
            if suffix_match and suffix_match.group(2):
                base_num = suffix_match.group(1)
                suffix = suffix_match.group(2)
                
                for gpu in self.gpus:
                    if gpu.id in seen:
                        continue
                    gpu_norm = normalize_text(gpu.model).replace(' ', '')
                    if base_num in gpu_norm and suffix in gpu_norm:
                        candidates.append((gpu, 0.95))
                        seen.add(gpu.id)
        
        # Strategy 2: Fuzzy matching if no exact matches
        if not candidates:
            results = process.extract(
                normalized,
                self.searchable_names,
                scorer=fuzz.token_sort_ratio,
                limit=5
            )
            
            for name, score, _ in results:
                gpu = self.name_to_gpu.get(name)
                if gpu and gpu.id not in seen:
                    confidence = score / 100.0
                    if confidence >= 0.70:
                        candidates.append((gpu, confidence))
                        seen.add(gpu.id)
        
        # Strategy 3: Number + prefix matching
        if not candidates:
            # Pattern: look for 3-4 digit numbers, allowing them to follow letters (like N740)
            # and be followed by letters (like 740D) - captures numbers in part numbers
            model_matches = re.findall(r'(?:^|\D)(\d{3,4})\s*(ti|super|xt|xtx)?(?=\D|$)', normalized)
            has_rtx = 'rtx' in normalized
            has_gtx = 'gtx' in normalized
            has_rx = 'rx' in normalized and not has_rtx
            
            # Vendor detection for penalties - BUT: brands like ASUS/Gigabyte/MSI make BOTH Nvidia and AMD
            # So we should NOT penalize based on these brand names alone
            has_nvidia = 'nvidia' in normalized or 'geforce' in normalized
            has_amd = 'amd' in normalized or 'radeon' in normalized
            has_intel = 'intel' in normalized or 'arc ' in normalized
            
            # GPU brand manufacturers (make both, don't penalize)
            gpu_brand = any(v in normalized for v in ['gigabyte', 'msi', 'asrock', 'asus', 'sapphire', 'xfx', 'powercolor', 'evga', 'palit', 'zotac', 'pny'])
            
            # Check for GPU context - require at least some GPU-related keywords
            # to avoid matching price numbers like "650" in "EUR 650.00"
            gpu_context = has_rtx or has_gtx or has_rx or 'radeon' in normalized or 'geforce' in normalized or 'intel' in normalized or 'arc' in normalized
            
            for num, suffix in model_matches:
                # Skip numbers that look like prices (standalone 3-4 digit numbers
                # without GPU context or suffixes)
                if not gpu_context and not suffix:
                    # Check if number is surrounded by currency/price indicators
                    # Pattern: eur/€/$ before or .00/.99 after
                    price_pattern = re.search(r'(eur|euro|€|\$)\s*' + num + r'|\b' + num + r'[.,]\d{2}\b', full_text.lower())
                    if price_pattern:
                        logger.debug(f"Skipping potential price number: {num}")
                        continue
                
                for gpu in self.gpus:
                    if gpu.id in seen:
                        continue
                    
                    gpu_norm = normalize_text(gpu.model)
                    
                    # Check prefix match
                    prefix_match = False
                    if has_rtx and 'rtx' in gpu_norm:
                        prefix_match = True
                    elif has_gtx and 'gtx' in gpu_norm:
                        prefix_match = True
                    elif has_rx and gpu_norm.startswith('rx'):
                        prefix_match = True
                    
                    if not prefix_match or num not in gpu_norm:
                        continue
                    
                    # Check for number match (whole word OR preceded by letter like A380, B580)
                    # r'\b' + num + r'\b' fails for "a380" because "a" is not a word boundary
                    # Allow: " 380", "rtx 380", "a380" (Arc A380) - but not "3800"
                    num_match = re.search(r'(?:^|[^0-9])' + num + r'(?:[^0-9]|$)', gpu_norm)
                    if not num_match:
                        continue
                    
                    # Score based on suffix match
                    if suffix and suffix in gpu_norm:
                        score = 0.85
                    else:
                        score = 0.75
                    
                    # Apply vendor penalties
                    is_nvidia_gpu = 'rtx' in gpu_norm or 'gtx' in gpu_norm or 'gt' in gpu_norm
                    is_amd_gpu = gpu_norm.startswith('rx') or 'radeon' in gpu_norm or 'vega' in gpu_norm
                    is_intel_gpu = 'arc' in gpu_norm or gpu_norm.startswith('intel')
                    
                    if has_intel and (is_nvidia_gpu or is_amd_gpu):
                        score -= 0.3
                    elif has_nvidia and (is_amd_gpu or is_intel_gpu):
                        score -= 0.2
                    elif has_amd and (is_nvidia_gpu or is_intel_gpu):
                        score -= 0.2
                    
                    if score > 0:
                        candidates.append((gpu, score))
                        seen.add(gpu.id)
        
        # Sort by confidence score (highest first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Strategy 4: Fallback - if still no candidates, try number-only matching
        # This handles "Gigabyte 3060" or "ASUS 3080 Ti" where vendor is in title
        # but no rtx/gtx/rx prefix
        if not candidates:
            # Pattern: look for 3-4 digit numbers, allowing them to follow letters (like N740)
            # and be followed by letters (like 740D) - captures numbers in part numbers
            model_matches = re.findall(r'(?:^|\D)(\d{3,4})\s*(ti|super|xt|xtx)?(?=\D|$)', normalized)
            
            # Check for vendor hints - BUT: brands like ASUS/Gigabyte/MSI make BOTH
            has_nvidia = 'nvidia' in normalized or 'geforce' in normalized
            has_amd = 'amd' in normalized or 'radeon' in normalized
            has_intel = 'intel' in normalized or 'arc ' in normalized
            
            # GPU brand manufacturers (make both, don't use for penalties)
            gpu_brand = any(v in normalized for v in ['gigabyte', 'msi', 'asrock', 'asus', 'sapphire', 'xfx', 'powercolor', 'evga', 'palit', 'zotac', 'pny'])
            has_gpu_context = has_nvidia or has_amd or has_intel
            
            for num, suffix in model_matches:
                # Skip standalone numbers that look like prices
                # (3-4 digit numbers without GPU context, vendor hint, or suffix)
                if not has_gpu_context and not suffix:
                    # Check if this looks like a price (has decimal .00 or currency nearby)
                    price_pattern = re.search(r'(eur|euro|€|\$)\s*' + num + r'|\b' + num + r'[.,]\d{2}\b', full_text.lower())
                    if price_pattern:
                        logger.debug(f"Skipping potential price number: {num}")
                        continue
                
                for gpu in self.gpus:
                    if gpu.id in seen:
                        continue
                    
                    gpu_norm = normalize_text(gpu.model)
                    
                    # Check if number is in GPU model
                    if num not in gpu_norm:
                        continue
                    
                    # Check for number match (whole word OR preceded by letter like A380, B580)
                    # r'\b' + num + r'\b' fails for "a380" because "a" is not a word boundary
                    # Allow: " 380", "rtx 380", "a380" (Arc A380) - but not "3800"
                    num_match = re.search(r'(?:^|[^0-9])' + num + r'(?:[^0-9]|$)', gpu_norm)
                    if not num_match:
                        continue
                    
                    # Apply vendor hints
                    is_nvidia_gpu = 'rtx' in gpu_norm or 'gtx' in gpu_norm or 'gt' in gpu_norm
                    is_amd_gpu = gpu_norm.startswith('rx') or 'radeon' in gpu_norm or 'vega' in gpu_norm
                    is_intel_gpu = 'arc' in gpu_norm or gpu_norm.startswith('intel')
                    
                    # Boost if vendor hint matches
                    vendor_boost = 0.0
                    if has_nvidia and is_nvidia_gpu:
                        vendor_boost = 0.05
                    elif has_amd and is_amd_gpu:
                        vendor_boost = 0.05
                    elif has_intel and is_intel_gpu:
                        vendor_boost = 0.05
                    
                    # Penalty if vendor hint contradicts GPU
                    vendor_penalty = 0.0
                    if has_intel and (is_nvidia_gpu or is_amd_gpu):
                        vendor_penalty = -0.3  # Strong penalty - Intel in title shouldn't match AMD/Nvidia
                    elif has_nvidia and (is_amd_gpu or is_intel_gpu):
                        vendor_penalty = -0.2
                    elif has_amd and (is_nvidia_gpu or is_intel_gpu):
                        vendor_penalty = -0.2
                    
                    # Score based on suffix match
                    base_score = 0.60  # Lower base score for number-only matches
                    if suffix and suffix in gpu_norm:
                        score = base_score + 0.15 + vendor_boost + vendor_penalty  # 0.75-0.80 before penalty
                    else:
                        score = base_score + vendor_boost + vendor_penalty  # 0.60-0.65 before penalty
                    
                    # Skip candidates with negative scores (vendor mismatch)
                    if score > 0:
                        candidates.append((gpu, score))
                        seen.add(gpu.id)
            
            # Re-sort after adding fallback candidates
            candidates.sort(key=lambda x: x[1], reverse=True)
        
        return candidates
    
    def get_candidates(self, text: str, limit: int = 5, vram_mb: Optional[int] = None) -> List[Tuple[GPUReference, float]]:
        """Get top N candidates with scores for manual review."""
        normalized = normalize_text(text)
        candidates = self._get_candidates_by_name(normalized, text)
        
        if vram_mb:
            # Re-score with VRAM consideration
            rescored = []
            for gpu, name_score in candidates:
                vram_score = self._get_vram_match_score(gpu.vram_gb, vram_mb)
                combined = (name_score * 0.7) + (vram_score * 0.3)
                rescored.append((gpu, combined))
            rescored.sort(key=lambda x: x[1], reverse=True)
            return rescored[:limit]
        
        return candidates[:limit]
