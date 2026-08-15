# -*- coding: utf-8 -*-
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

import importlib

# Import and check
from src.scraper import computer_matcher
print(f"computer_matcher module file: {computer_matcher.__file__}")

# Read the actual file to verify the code is there
with open(computer_matcher.__file__, 'r') as f:
    content = f.read()
    if 'ssd_brand_in_ssd_context' in content:
        print("✓ ssd_brand_in_ssd_context IS in the file")
    else:
        print("✗ ssd_brand_in_ssd_context NOT in the file")
    
    if 'ssd_brand_lower' in content:
        print("✓ ssd_brand_lower IS in the file")
    else:
        print("✗ ssd_brand_lower NOT in the file")
