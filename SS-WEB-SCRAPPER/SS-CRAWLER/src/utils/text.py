"""Text normalization utilities for GPU and CPU matching."""
import re
import unicodedata
from typing import List


def normalize_text(text: str) -> str:
    """
    Normalize text for matching:
    1. Unicode NFKD (separate base + diacritics)
    2. Remove diacritics (Latvian ā → a, ē → e, etc.)
    3. Basic Cyrillic transliteration
    4. Lowercase
    5. Keep only alphanumeric and spaces
    6. Collapse multiple spaces
    
    Examples:
        "Nvidia RTX 3080 Ti" → "nvidia rtx 3080 ti"
        "Видеокарта GTX 1060" → "видеокарта gtx 1060"
        "Radeon RX  580 (8GB)" → "radeon rx 580 8gb"
    """
    if not text:
        return ""
    
    # Step 1: NFKD normalization
    text = unicodedata.normalize('NFKD', text)
    
    # Step 2: Remove combining marks (diacritics)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    
    # Step 3: Preserve specific patterns before removing special chars
    # G.Skill -> gskill (keep as one word)
    text = re.sub(r'g\.\s*skill', 'gskill', text, flags=re.IGNORECASE)
    
    # Step 4: Basic Cyrillic transliteration
    cyrillic_map = str.maketrans({
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
        'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
        'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
        'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
        'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch',
        'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
        'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    })
    text = text.translate(cyrillic_map)
    
    # Step 4: Lowercase
    text = text.lower()
    
    # Step 5: Keep only alphanumeric, spaces, and decimal points (for numbers like 1.38)
    # But first, replace colons with spaces to separate words like "psu:XILENCE" -> "psu XILENCE"
    text = re.sub(r':', ' ', text)
    text = re.sub(r'[^a-z0-9\s.]', '', text)
    
    # Step 6: Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def extract_gpu_tokens(text: str) -> List[str]:
    """
    Extract likely GPU model tokens from text.
    
    Returns normalized tokens like:
        ["rtx3080", "rtx 3080", "rtx3080ti", "gtx1060", ...]
    """
    if not text:
        return []
    
    normalized = normalize_text(text)
    tokens = set()
    
    # NVIDIA patterns
    patterns = [
        # RTX series
        r'rtx\s*\d{4}\s*(?:ti|super|s)?',
        # GTX series
        r'gtx\s*\d{3,4}\s*(?:ti|super)?',
        # Older NVIDIA (4-digit followed by GT/GTX like 9800 GT, 8600 GTS)
        r'\d{4}\s*gtx',
        r'\d{4}\s*gt\w*',
        # GT series
        r'gt\s*\d{3,4}',
        r'gs\s*\d{3,4}',
        # AMD patterns
        r'rx\s*7\d{3}\s*(?:xt|xtx)?',  # RX 7000 series (7900 XT/XTX)
        r'rx\s*6\d{3}\s*(?:xt|xtx)?',  # RX 6000 series (6800, 6900, etc.)
        r'rx\s*5\d{3}\s*(?:xt|xtx)?',  # RX 5000 series (5700, 5600, etc.)
        r'rx\s*\d{3,4}\s*(?:xt|xtx)?',  # RX 570, RX 5700 XT (general pattern)
        r'rx\s*vega\s*\d+',  # RX Vega 56, RX Vega 64
        r'radeon\s*(?:rx|r[0-9x]|hd|vega)\s*\d*',
        r'vega\s*\d+',
        r'rx\s*vega',
        # Intel
        r'arc\s*a\s*\d+',
        # Bare model numbers (no family prefix) — handles titles like
        # "Asus 7900Xtx" (missing "RX") and "Zotac 1660 super" (missing "GTX")
        # Real-world listings often omit the family prefix; we must still
        # recognise the variant suffix so the matcher picks the right model.
        r'\b7\d{3}\s*xtx\b',   # 7900 XTX, 7800 XTX, 7700 XTX
        r'\b7\d{3}\s*xt\b',    # 7900 XT, 7800 XT
        r'\b6\d{3}\s*xtx?\b',  # 6800 XT/XTX, 6900 XT/XTX
        r'\b5\d{3}\s*xtx?\b',  # 5700 XT/XTX, 5600 XT
        r'\b1\d{3}\s*super\b',  # 1660 super, 1650 super
        r'\b3\d{3}\s*super\b',  # 3060 super
        r'\b1\d{3}\s*ti\b',     # 1660 ti
        r'\b3\d{3}\s*ti\b',     # 3060 ti
        r'\b2\d{3}\s*ti\b',     # 2060 ti
        r'\b1\d{3}\s*xtx?\b',   # 1660 XT (rare)
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, normalized)
        for match in matches:
            # Add canonical forms
            tokens.add(match.replace(' ', ''))  # rtx3080
            tokens.add(re.sub(r'\s+', ' ', match).strip())  # rtx 3080
    
    return list(tokens)


def generate_search_variants(text: str) -> List[str]:
    """
    Generate multiple search variants for robust matching.
    
    Returns variants like:
        ["geforce rtx 3080 ti", "g rtx 3080 ti", "rtx3080ti", ...]
    """
    if not text:
        return []
    
    normalized = normalize_text(text)
    variants = {normalized}
    
    # Without spaces
    variants.add(normalized.replace(' ', ''))
    
    # With common abbreviations
    abbrev = normalized.replace('geforce', 'g').replace('radeon', 'rx')
    variants.add(abbrev)
    variants.add(abbrev.replace(' ', ''))
    
    # GPU-specific patterns (remove common filler words)
    clean = re.sub(r'\b(graphics|card|video|gpu|edition|oc)\b', '', normalized)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if clean:
        variants.add(clean)
    
    return list(variants)


def extract_cpu_tokens(text: str) -> List[str]:
    """
    Extract likely CPU model tokens from text.
    
    Returns normalized tokens like:
        ["i7-14700", "i9 14900k", "ryzen 7 7800x", "5800x3d", ...]
    """
    if not text:
        return []
    
    normalized = normalize_text(text)
    tokens = set()
    
    # Intel patterns - NOTE: after normalization, dashes are removed
    # So "i3-10105" becomes "i310105" in normalized text
    # But we also need to match the original text for suffixes like KF, KS, etc.
    
    # Try to find patterns in original text first (before normalization destroys dashes)
    original_patterns = [
        # Intel Core with dash/space and suffix (K, KF, F, T, KS, S) - case insensitive
        # Also handles cases where suffix is attached: "i5 14400f", "i5-14400F", "i5-4460S"
        r'i[3579]\s*[-]?\s*\d{3,5}(?:\s*(?:kf|ks|k|f|t|s))?\b',
        r'i[3579]\s*[-]?\s*\d{3,5}(?:kf|ks|k|f|t|s)\b',  # For attached suffixes like "14400f"
        # AMD Ryzen patterns with suffixes (X, XT, 3D, X3D, G, F for APU)
        r'ryzen\s*\d?\s*\d{3,4}\s*(?:x|xt|3d|x3d|g|f)?',
        # AMD Ryzen with 3D suffix specifically (e.g., 5800X3D, 7800X3D)
        r'ryzen\s*\d?\s*\d{4}x3d',
        # AMD without "Ryzen" word but with series + model (e.g., "AMD 5 9600X")
        r'amd\s*(?:ryzen\s*)?[3579]?\s*\d{4}\s*(?:x|xt|3d|x3d|g|f)?',
        # AMD Ryzen with G suffix (APU) like 5600G, 5700G
        r'r[3579]\s*\d{3,4}g',
        # AMD Ryzen with F suffix like 8700F
        r'r[3579]\s*\d{3,4}f',
        # Intel Xeon patterns - including v-version (e.g., E5-2680 v4)
        r'xeon\s*(?:[ew])?\d*[-]?\d{4}(?:\s*v\d+)?',
    ]
    
    # Also check for common typos
    text_fixed = text.lower().replace('xenon', 'xeon')
    # Fix common typo "phamtom" -> "phenom"
    text_fixed = text_fixed.replace('phamtom', 'phenom')
    for pattern in original_patterns:
        matches = re.findall(pattern, text_fixed, re.IGNORECASE)
        for match in matches:
            # Add original format (lowercase, no spaces)
            clean = match.lower().replace(' ', '').strip()
            tokens.add(clean)
            # Add normalized format (no spaces/dashes)
            tokens.add(clean.replace('-', ''))
            
            # For Intel patterns, extract with suffix (e.g., "14400f" from "i5 14400f")
            # Handle patterns like "i514400", "i5-14400", "i5 14400f"
            m = re.match(r'(i[3579])-?(\d{3,5})(kf|ks|k|f|t|s)?', clean)
            if m:
                tier, num, suffix = m.groups()
                # Always add the token with suffix (e.g., "i5-14400f" or "i514400f")
                if suffix:
                    tokens.add(f"{tier}-{num}{suffix}")
                    tokens.add(f"{tier}{num}{suffix}")  # Also add without dash
                else:
                    tokens.add(f"{tier}-{num}")
                    tokens.add(f"{tier}{num}")
                
                # Also add the base token without suffix for matching
                tokens.add(f"{tier}{num}")
                tokens.add(f"{tier}-{num}")
    
    # AMD Phenom II patterns (e.g., "Phenom II X6 1100T")
    phenom_patterns = [
        r'phenom\s*ii\s*x[46]\s*\d{4}\w*',
        r'phenom\s*x[46]\s*\d{4}\w*',
        r'fx\s*-\s*\d{4}',
    ]
    for pattern in phenom_patterns:
        matches = re.findall(pattern, text_fixed, re.IGNORECASE)
        for match in matches:
            clean = match.lower().replace(' ', '').strip()
            tokens.add(clean)
    
    # Also check normalized text for patterns without dashes
    patterns = [
        # Intel Core series (i3, i5, i7, i9) - after normalization no dash
        r'i[3579]\d{3,5}(?:kf|ks|k|f|t|s)?',
        # AMD Ryzen patterns
        r'ryzen\s*\d?\s*\d{3,4}\s*(?:x|xt|3d)?',
        r'r[3579]\s*\d{3,4}\s*(?:x|xt|3d)?',
        # AMD without "Ryzen" word (e.g., "amd59600x")
        r'amd[3579]?\s*\d{4}\s*(?:x|xt|3d|g|f)?',
        # AMD FX/Athlon
        r'fx\s*-\s*\d{4}',
        r'athlon\s*\w+',
        # Older Intel Core 2 Duo/Quad
        r'core\s*2\s*(?:duo|quad)',
        r'core2(?:duo|quad)',
        # Intel Q-series (Core 2 Quad Q9550, Q9650, etc.)
        r'q\d{4}',
        # Intel E-series (Core 2 Duo E8400, etc.)
        r'e\d{4}',
        # Intel i-series (e.g., "i7 10700K")
        r'i[3579]\s*\d{4,5}',
        # Pentium/Celeron
        r'pentium\s*\w*',
        r'celeron\s*\w*',
        # Xeon patterns
        r'xeon\s*\w*\d+',
        # Ryzen without series number (e.g., "Ryzen 3600" -> should be Ryzen 5 3600)
        r'ryzen\s*(?:5|7|9)?\s*\d{4}',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, normalized)
        for match in matches:
            # Add normalized forms
            tokens.add(match.replace(' ', ''))
            # Add with dash
            if match[0] == 'i' and len(match) > 2 and match[1] in '3579':
                # Insert dash after i3/i5/i7/i9 for Intel
                if match[2].isdigit():
                    # Find where the number ends and suffix begins
                    m = re.match(r'(i[3579])(\d+)(kf|ks|k|f|t|s)?', match, re.IGNORECASE)
                    if m:
                        tier, num, suffix = m.groups()
                        if suffix:
                            tokens.add(f"{tier}-{num}{suffix}")
                        else:
                            tokens.add(f"{tier}-{num}")
            # Handle Q-series (Core 2 Quad) like Q9550
            elif match[0] == 'q' and len(match) == 5 and match[1:].isdigit():
                tokens.add(match)  # q9550
                tokens.add(f"core2quad-{match}")  # core2quad-q9550
            # Handle AMD Ryzen with 3D suffix (e.g., 5800X3D)
            elif '3d' in match or 'x3d' in match:
                # Add both normalized and with suffix
                tokens.add(match.replace(' ', ''))  # ryzen75800x3d
                tokens.add(match.replace(' ', '').replace('3d', ''))  # ryzen75800x
                tokens.add(match.replace(' ', '').replace('ryzen', '').replace('3d', ''))  # 75800x
                tokens.add(match.replace(' ', '').replace('ryzen', ''))  # 75800x3d
            # Handle E-series (Core 2 Duo) like E8400
            elif match[0] == 'e' and len(match) == 5 and match[1:].isdigit():
                tokens.add(match)  # e8400
                tokens.add(f"core2duo-{match}")  # core2duo-e8400
    
    return list(tokens)


def compute_content_hash(title: str, price: float, location: str) -> str:
    """
    Compute hash for duplicate/re-list detection.
    Used to detect same GPU being re-listed multiple times.
    """
    import hashlib
    
    # Normalize inputs
    normalized_title = normalize_text(title)
    price_int = int(price) if price else 0
    normalized_location = normalize_text(location) if location else ""
    
    # Create consistent string
    content = f"{normalized_title}|{price_int}|{normalized_location}"
    
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
