# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import extract_cpu_tokens, normalize_text

# Test text
text = """Procesors: AMD Ryzen r7 8700f - jauns;"""

normalized = normalize_text(text)
tokens = extract_cpu_tokens(text)

print("Text:", text)
print("Normalized:", normalized)
print("Tokens:", tokens)

# Check what tokens contain 8700
for token in tokens:
    if '8700' in token.lower():
        print(f"\nToken with 8700: '{token}'")
        token_lower = token.lower()
        print(f"  Ends with 'f': {token_lower.endswith('f')}")
        print(f"  Ends with 'g': {token_lower.endswith('g')}")
        
        # Check for G suffix in token
        if token_lower.endswith('g') and not token_lower.endswith('f'):
            print("  Would match 8700G")
        elif token_lower.endswith('f'):
            print("  Should NOT match 8700G")
