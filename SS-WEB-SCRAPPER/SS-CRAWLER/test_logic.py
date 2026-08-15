# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text
import re

# Simulate the logic
title = "Pārdodu PC"
description = """Proccesor Xeon e5-2680 v4 14 Cores 28 Treads

Video - Rx580 8gb

Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz

SSD - 1x SSD 128gb / 1x SSD 500gb

Līdzi dodu HDD 1-Tb

Var dabūt nedaudz lētak ar RAM 1x 16Gb

Monitors HP 24 collas dāvana

Atrodās Salaspilī

Lat/Rus/Eng"""

full_text = f"{title} {description}".lower()

# Simulate _detect_monitor_mentioned
text_lower = full_text.lower()
inclusion_patterns = [
    r'monitors?\s+(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)',
    r'(?:hp|dell|asus|lg|samsung|acer|philips|benq|viewsonic|aoc)\s+monitors?',
    r'(?i)hp\s+(?:\d{2,3})\s+collas',
]

is_included = False
detection_method = "none"
for pattern in inclusion_patterns:
    if re.search(pattern, text_lower):
        is_included = True
        detection_method = "monitor_mentioned"
        break

# Simple keyword check
monitor_keywords = ['monitors', 'ekrans', 'displejs', 'displays', 'screen']
for kw in monitor_keywords:
    if kw in text_lower:
        is_included = True
        detection_method = f"keyword_{kw}"
        break

print("is_included:", is_included)
print("detection_method:", detection_method)

# Extract monitor context
monitor_context_parts = []
lines = text_lower.split('\n')
for line in lines:
    line_lower = line.lower()
    if any(kw in line_lower for kw in monitor_keywords):
        monitor_context_parts.append(line_lower)

monitor_context = ' '.join(monitor_context_parts)
print("monitor_context:", repr(monitor_context))

# Check if HP is in monitor context
has_brand = 'hp' in monitor_context
print("has_brand (hp in monitor_context):", has_brand)

# Extract size
size_patterns = [
    r'\bmonitors?\s+(?:\w+\s+)?(\d{2,3})\b',
    r'ekrans\w*\s+(?:\w+\s+)?(\d{2,3})\b',
]

extracted_size = None
for pattern in size_patterns:
    match = re.search(pattern, monitor_context)
    if match:
        size = match.group(1)
        try:
            size_num = float(size)
            if 21 <= size_num <= 49:
                extracted_size = str(int(size_num))
                break
        except ValueError:
            pass

print("extracted_size:", extracted_size)

# What would happen?
print("\n--- Logic Check ---")
has_monitor_context = is_included
print(f"has_monitor_context: {has_monitor_context}")

# has_model is False in this case because no model matched
has_model = False  # This is what we determined earlier

print(f"has_model: {has_model}")
print(f"has_monitor_context and not has_model: {has_monitor_context and not has_model}")

if has_monitor_context and not has_model:
    print("Would return generic monitor!")
else:
    print("Would NOT return generic monitor")
