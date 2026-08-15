# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text

# Test text from lphjf.html
text = """Videokarte: Powercolor red devil RX6800XT 16gb - lietota;"""

normalized = normalize_text(text)
print("Text:", text)
print("Normalized:", normalized)
print()

# Check for RX6800XT
print(f"'rx6800xt' in normalized: {'rx6800xt' in normalized}")
print(f"'rx6800' in normalized: {'rx6800' in normalized}")
print(f"'6800xt' in normalized: {'6800xt' in normalized}")
print(f"'6800' in normalized: {'6800' in normalized}")

# Check GPU tokens
from src.scraper.matcher import extract_gpu_tokens
tokens = extract_gpu_tokens(text)
print(f"\nGPU tokens: {tokens}")
