import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from src.database.connection import get_session
from src.database.repository import MotherboardRepository
from src.scraper.motherboard_matcher import MotherboardMatcher

# Load motherboards
with get_session() as session:
    motherboards = MotherboardRepository.get_all(session)

print(f"Loaded {len(motherboards)} motherboards")

# Initialize matcher
matcher = MotherboardMatcher(motherboards)

# Check what names are in brand_model_names
print("\nChecking for H510M in brand_model_names:")
for name in sorted(matcher.brand_model_names.keys()):
    if 'h510' in name or 'h ' in name:
        mb = matcher.brand_model_names[name]
        print(f"  '{name}' -> ID {mb.id}: {mb.brand} {mb.model}")

print("\nChecking for 'gigabyte h' in brand_model_names:")
if 'gigabyte h' in matcher.brand_model_names:
    mb = matcher.brand_model_names['gigabyte h']
    print(f"  Found 'gigabyte h' -> ID {mb.id}: {mb.brand} {mb.model}")
else:
    print("  'gigabyte h' NOT found")
