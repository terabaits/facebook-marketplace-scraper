# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text, extract_ssd_tokens

text = """Pardodu savu datoru. Pc sastāvs: i5-6500, gtx 1060 6gb, netac 256gb ssd, 16 gb ram, barošanas bloks - deepcool pf500

Dators vel ar garantiju līdz šā gada beigām (PC veikals).

Dators atrodas Siguldā (Rīgā pievest var)."""

normalized = normalize_text(text)
print("Normalized text:", normalized)
print()

# Check for SSD tokens
tokens = extract_ssd_tokens(text)
print("SSD tokens:", tokens)
