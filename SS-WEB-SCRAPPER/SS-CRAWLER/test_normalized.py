# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text

text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500"""

normalized = normalize_text(text)
print(f"Original: {text[:80]}")
print(f"Normalized: {normalized[:80]}")
print(f"\n'netac' in normalized: {'netac' in normalized}")
print(f"'ssd' in normalized: {'ssd' in normalized}")
