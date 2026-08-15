#!/usr/bin/env python3
"""Debug PSU brand extraction."""
import sys
sys.path.insert(0, 'src')

import re
from src.utils.text import normalize_text

# Test the extraction
test_texts = [
    "Barošanas bloks:XILENCE 600W",
    "Barošanas bloks: XILENCE 600W",
    "psu xilence 600w",
    "Barošanas bloks:XILENCE",
]

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

for text in test_texts:
    print(f"\n{'='*60}")
    print(f"Input: '{text}'")
    normalized = normalize_text(text)
    print(f"Normalized: '{normalized}'")
    
    # Extract brands
    tokens = set()
    for pattern in brand_patterns:
        matches = re.findall(pattern, normalized, re.IGNORECASE)
        for match in matches:
            match_lower = match.lower()
            if 'bequiet' in match_lower or 'be quiet' in match_lower:
                tokens.add('be quiet')
            elif 'coolermaster' in match_lower or 'cooler master' in match_lower:
                tokens.add('cooler master')
            elif 'chieftec' in match_lower or 'chieftek' in match_lower:
                tokens.add('chieftec')
            elif 'superflower' in match_lower or 'super flower' in match_lower:
                tokens.add('super flower')
            elif 'thoughpower' in match_lower:
                tokens.add('toughpower')
            elif 'xfx' in match_lower:
                tokens.add('xfx')
            else:
                tokens.add(match_lower)
    
    print(f"Extracted tokens: {tokens}")
    
    # Check if xilence pattern matches
    xilence_match = re.search(r'\bxilence\b', normalized, re.IGNORECASE)
    if xilence_match:
        print(f"✓ Xilence pattern MATCHED at: {xilence_match.span()}")
    else:
        print(f"✗ Xilence pattern NOT found")
        # Try without word boundaries
        xilence_loose = re.search(r'xilence', normalized, re.IGNORECASE)
        if xilence_loose:
            print(f"  But 'xilence' found at: {xilence_loose.span()}")
            # Show surrounding chars
            start = max(0, xilence_loose.start() - 2)
            end = min(len(normalized), xilence_loose.end() + 2)
            print(f"  Context: '{normalized[start:end]}'")
