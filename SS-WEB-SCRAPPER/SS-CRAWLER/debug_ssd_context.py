# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500"""

normalized = text.lower()
print(f"Normalized: {normalized}")

ssd_keywords = ['ssd', 'nvme', 'm.2', 'disk', 'cietie']
for kw in ssd_keywords:
    if kw in normalized:
        kw_pos = normalized.find(kw)
        print(f"\nKeyword '{kw}' found at position {kw_pos}")
        context_start = max(0, kw_pos - 40)
        context_end = min(len(normalized), kw_pos + 40)
        context = normalized[context_start:context_end]
        print(f"Context: '{context}'")
        if 'netac' in context:
            print("  -> 'netac' found in context!")
