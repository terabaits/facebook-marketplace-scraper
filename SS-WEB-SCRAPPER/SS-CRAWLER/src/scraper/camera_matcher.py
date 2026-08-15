"""Camera matcher for ss.com listings."""
import re
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

from src.utils.logger import get_logger

logger = get_logger("camera_matcher")


@dataclass
class CameraMatchResult:
    """Camera matching result."""
    camera: Optional[Dict] = None
    confidence: float = 0.0
    method: str = "none"


class CameraMatcher:
    """Match camera listings to reference database."""
    
    def __init__(self, cameras: List[Dict]):
        """Initialize matcher with camera reference data."""
        self.cameras = cameras
        self.logger = logger
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        text = text.lower()
        # Remove special characters but keep alphanumeric and spaces
        text = re.sub(r'[^\w\s-]', ' ', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text
    
    def _extract_brand(self, text: str) -> Optional[str]:
        """Extract camera brand from text."""
        text_lower = text.lower()
        
        brand_patterns = [
            (r'\bcanon\b', 'Canon'),
            (r'\bsony\b', 'Sony'),
            (r'\bfujifilm\b', 'Fujifilm'),
            (r'\bfuji\b', 'Fujifilm'),
            (r'\bpanasonic\b', 'Panasonic'),
            (r'\blumix\b', 'Panasonic'),
            (r'\bnikon\b', 'Nikon'),
            (r'\bblackmagic\b', 'Blackmagic'),
            (r'\bmamiya\b', 'Mamiya'),
            (r'\bphase\s*one\b', 'Phase One'),
            (r'\bhasselblad\b', 'Hasselblad'),
            (r'\bolympus\b', 'Olympus'),
            (r'\bpentax\b', 'Pentax'),
            (r'\bleica\b', 'Leica'),
            (r'\bsigma\b', 'Sigma'),
        ]
        
        for pattern, brand in brand_patterns:
            if re.search(pattern, text_lower):
                return brand
        
        return None
    
    def _extract_model_variants(self, model_str: str) -> List[str]:
        """Extract model variants from slash-separated string."""
        # Split by common separators: /, (comma in some locales)
        variants = re.split(r'\s*/\s*', model_str)
        return [v.strip() for v in variants if v.strip()]
    
    def _calculate_match_score(self, text: str, camera: Dict) -> tuple[float, str]:
        """
        Calculate match score between text and camera.
        Returns (score, method)
        """
        text_norm = self._normalize_text(text)
        text_lower = text.lower()
        
        brand = camera.get('brand', '').lower()
        model = camera.get('model', '').lower()
        normalized_name = camera.get('normalized_name', '').lower()
        
        score = 0.0
        method = "none"
        
        # Brand matching
        if brand and brand in text_lower:
            score += 0.25
            # Bonus if brand appears at start
            if text_lower.startswith(brand):
                score += 0.1
        
        # Extract model variants (e.g., "500D / T1i / X3" -> ["500d", "t1i", "x3"])
        model_variants = self._extract_model_variants(model)
        
        # Check each model variant
        best_variant_score = 0.0
        best_variant_method = "none"
        
        # Also check for "A7II" style concatenated (for Sony cameras)
        concat_pattern = rf'([a-z]\d+)(ii|iii|iv|i+)(?:\b|i|\d)'
        concat_match = re.search(concat_pattern, text_lower)
        
        # Also check for "A7II" / "R6II" style concatenated
        mirrorless_patterns = [
            (r'\b(a7)(ii|iii|iv|i+|[1-4])(?:\b)', 'A7'),  # "a7ii", "a7iii", "a73" (not a70)
            (r'\b(a7r)(ii|iii|iv|i+|[1-4])(?:\b)', 'A7R'),  # "a7rii", "a7r3" (not a7r0)
            (r'\b(a7s)(ii|iii|iv|i+|[1-4])(?:\b)', 'A7S'),  # "a7sii", "a7s3"
            (r'\b(a7c)(ii|iii|iv|i+|[1-4])(?:\b)', 'A7C'),  # "a7cii", "a7c3"
            (r'\b(r6)(ii|iii|iv|i+|[1-4])(?:\b)', 'R6'),  # "r6ii", "r63" (not r60)
            (r'\b(r5)(ii|iii|iv|i+|[1-4])(?:\b)', 'R5'),  # "r5ii", "r53" (not r50)
            (r'\b(r3)(ii|iii|iv|i+|[1-4])(?:\b)', 'R3'),  # "r3ii", "r33" (not r30)
        ]
        
        concat_match = None
        for pattern, model_type in mirrorless_patterns:
            match = re.search(pattern, text_lower)
            if match:
                concat_match = match
                base = match.group(1)  # e.g., "a7r"
                mark = match.group(2)  # e.g., "3"
                
                # Convert digit marks to roman for comparison
                digit_to_roman = {'1': 'i', '2': 'ii', '3': 'iii', '4': 'iv'}
                mark_forms = [mark]
                if mark in digit_to_roman:
                    mark_forms.append(digit_to_roman[mark])
                
                # PRIORITY: Check mark forms FIRST (gives higher score)
                mark_matched = False
                for variant in model_variants:
                    variant_lower = variant.lower()
                    for mark_form in mark_forms:
                        if variant_lower == f"{model_type} {mark_form}".lower():
                            best_variant_score = max(best_variant_score, 1.5)  # HIGHEST for mark match
                            best_variant_method = "exact_model"
                            mark_matched = True
                            break
                    if mark_matched:
                        break
                
                # If no mark match, check base match
                if not mark_matched:
                    for variant in model_variants:
                        if variant.lower() == base.lower():
                            best_variant_score = max(best_variant_score, 0.8)
                            best_variant_method = "exact_model"
                            break
        
        for variant in model_variants:
            if not variant:
                continue
                
            # Check if this is the base model for a concatenated match
            if concat_match:
                base = concat_match.group(1)  # e.g., "a7"
                mark = concat_match.group(2)  # e.g., "ii"
                
                # If variant is the base (e.g., "a7") and model has mark
                if variant == base:
                    # Check if this camera model has this mark
                    model_lower = model.lower()
                    if mark in model_lower or f'mark {mark}' in model_lower or f'mark{mark}' in model_lower:
                        best_variant_score = max(best_variant_score, 0.8)
                        best_variant_method = "exact_model"
                        continue
            
            # Require word boundary OR eos prefix for the variant
            # Handle "eos700d" (concatenated) as well as "700d" (separated)
            variant_patterns = [
                rf'\b{re.escape(variant)}\b',  # Word boundary
                rf'eos\s*{re.escape(variant)}',  # "eos" + variant (eos700d)
                rf'eos-{re.escape(variant)}',  # "eos-" + variant
            ]
            
            for pattern in variant_patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    # Strong match - found exact model variant
                    best_variant_score = max(best_variant_score, 0.6)
                    best_variant_method = "exact_model"
                    break
            else:
                # No pattern matched, try substring
                if variant in text_lower:
                    # Partial match - variant substring found
                    best_variant_score = max(best_variant_score, 0.3)
                    best_variant_method = "partial_model"
        
        # Bonus for additional qualifiers like "Mark III", "Mark IV", "Mark 3", "mark2"
        # Check if "Mark X" or "Mark N" or "markN" is in the text and matches this camera
        mark_patterns = [
            r'\bmark\s*(ii|iii|iv|i+|\d+)\b',  # "Mark 3", "Mark III"
            r'(\d+)(mark|mk)(ii|iii|iv|i+|\d+)\b',  # "5dmark2", "5dmarkii"
            r'\b(mk)(ii|iii|iv|i+|\d+)\b',  # "mkii", "mk2"
            r'\b([a-z]\d+)(ii|iii|iv|i+)(\b|i|\d)',  # "a7ii", "a7iii" (Sony style)
        ]
        
        found_mark = None
        for pattern in mark_patterns:
            match = re.search(pattern, text_lower)
            if match:
                groups = match.groups()
                # Extract mark number from different capture groups
                if len(groups) >= 2 and groups[-1]:  # Last group often has the mark
                    last_group = groups[-1].lower()
                    if last_group in ['ii', 'iii', 'iv', 'i', '1', '2', '3', '4']:
                        found_mark = last_group
                        break
                # Check all groups
                for group in groups:
                    if group and group.lower() in ['ii', 'iii', 'iv', 'i', '1', '2', '3', '4']:
                        found_mark = group
                        break
                if found_mark:
                    break
        
        if found_mark:
            mark_variant = found_mark.lower()
            # Convert digit to roman numeral for comparison
            digit_to_roman = {'1': 'i', '2': 'ii', '3': 'iii', '4': 'iv'}
            roman_to_digit = {'i': '1', 'ii': '2', 'iii': '3', 'iv': '4'}
            
            # Check both forms
            mark_forms = [mark_variant]
            if mark_variant in digit_to_roman:
                mark_forms.append(digit_to_roman[mark_variant])
            if mark_variant in roman_to_digit:
                mark_forms.append(roman_to_digit[mark_variant])
            
            model_lower = model.lower()
            # Check if any form of this mark is in the camera model
            for form in mark_forms:
                if f'mark {form}' in model_lower or f'mark{form}' in model_lower:
                    best_variant_score += 0.5  # HIGH bonus for matching mark
                    method = "exact_model"  # Force exact model when mark matches
                    break
        
        if best_variant_score >= 0.6:
            score += best_variant_score
            method = best_variant_method
        elif best_variant_score > 0:
            score += best_variant_score
            method = best_variant_method
        
        # Check normalized name
        if normalized_name and method == "none":
            # Split normalized name and check parts
            norm_parts = normalized_name.split()
            if len(norm_parts) >= 2:
                # Require at least 2 parts to match (brand + model)
                matched_parts = 0
                for part in norm_parts:
                    if len(part) <= 2:
                        # Short parts need word boundaries
                        if re.search(rf'\b{re.escape(part)}\b', text_lower):
                            matched_parts += 1
                    else:
                        if part in text_lower:
                            matched_parts += 1
                
                norm_match_ratio = matched_parts / len(norm_parts)
                if norm_match_ratio >= 0.5:  # Lower threshold
                    score += 0.35 * norm_match_ratio
                    method = "normalized_match"
        
        # Check search keywords
        keywords = camera.get('search_keywords', [])
        if keywords:
            keyword_matches = sum(1 for kw in keywords 
                                  if kw.lower() in text_lower and len(kw) > 2)
            if len(keywords) > 0:
                keyword_score = (keyword_matches / min(len(keywords), 5)) * 0.2
                score += keyword_score
        
        # Mount mention bonus
        mount = camera.get('mount', '').lower()
        if mount and mount in text_lower:
            score += 0.1
        
        # Sensor type bonus
        sensor = camera.get('sensor', '').lower()
        if sensor and sensor in text_lower:
            score += 0.05
        
        return score, method
    
    def match(self, title: str, description: str = "") -> CameraMatchResult:
        """
        Match camera listing to reference database.
        
        Args:
            title: Listing title
            description: Optional description
            
        Returns:
            CameraMatchResult with matched camera and confidence
        """
        full_text = f"{title} {description}".strip()
        
        self.logger.debug(f"Matching camera for: {title[:80]}...")
        
        # Extract brand for pre-filtering
        detected_brand = self._extract_brand(full_text)
        
        best_match = None
        best_score = 0.0
        best_method = "none"
        
        for camera in self.cameras:
            # Skip if brands don't match (when we detected a brand)
            if detected_brand:
                camera_brand = camera.get('brand', '')
                if camera_brand and camera_brand.lower() != detected_brand.lower():
                    continue
            
            score, method = self._calculate_match_score(full_text, camera)
            
            if score > best_score:
                best_score = score
                best_match = camera
                best_method = method
        
        # Determine final confidence and result
        if best_match and best_score >= 0.5:
            self.logger.info(f"Matched camera: {best_match.get('brand')} {best_match.get('model')} (score: {best_score:.2f})")
            return CameraMatchResult(
                camera=best_match,
                confidence=min(best_score, 1.0),
                method=best_method
            )
        
        # No good match
        return CameraMatchResult(
            camera=None,
            confidence=best_score,
            method=best_method
        )
    
    def get_camera_by_id(self, camera_id: int) -> Optional[Dict]:
        """Get camera by ID."""
        for camera in self.cameras:
            if camera.get('id') == camera_id:
                return camera
        return None
    
    def get_candidates(self, title: str, limit: int = 5) -> List[tuple[Dict, float]]:
        """Get top candidate cameras for a title."""
        full_text = f"{title}".strip().lower()
        
        candidates = []
        for camera in self.cameras:
            score, _ = self._calculate_match_score(full_text, camera)
            if score > 0.2:
                candidates.append((camera, score))
        
        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:limit]
