#!/usr/bin/env python3
"""Test SSD matching for fcddo listing with real database data."""

import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\src')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.scraper.ssd_matcher import SSDMatcher
from src.models.schemas import SSDReference

# Connect to database
engine = create_engine('postgresql+psycopg2://crawler:crawler_pass@localhost:5433/ss_market')
Session = sessionmaker(bind=engine)
session = Session()

# Find SSD table
result = session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
tables = [r[0] for r in result]
print("Tables:", [t for t in tables if 'ssd' in t.lower()])

# Get SSD data from database
result = session.execute(text("SELECT * FROM ssd_reference"))

ssds = []
for row in result:
    # Convert row to SSDReference
    row_dict = dict(row._mapping)
    ssd = SSDReference(
        id=row_dict.get('id'),
        brand=row_dict.get('brand', ''),
        model=row_dict.get('model', ''),
        capacity_gb=row_dict.get('capacity_gb'),
        interface=row_dict.get('interface'),
        form_factor=row_dict.get('form_factor'),
        controller=row_dict.get('controller'),
        configuration=row_dict.get('configuration'),
        has_dram=row_dict.get('has_dram'),
        hmb=row_dict.get('hmb'),
        nand_brand=row_dict.get('nand_brand'),
        nand_type=row_dict.get('nand_type'),
        layers=row_dict.get('layers'),
        read_speed_mb=row_dict.get('read_speed_mb'),
        write_speed_mb=row_dict.get('write_speed_mb'),
        category=row_dict.get('category'),
        notes=row_dict.get('notes'),
        search_keywords=row_dict.get('search_keywords', []),
        normalized_name=row_dict.get('normalized_name', f"{row_dict.get('brand', '')} {row_dict.get('model', '')}").strip()
    )
    ssds.append(ssd)

print(f"Loaded {len(ssds)} SSDs from database")

# Initialize matcher
matcher = SSDMatcher(ssds)

# Test text from the actual fcddo listing
test_text = "SSD: Crucial 120GB"

print("\n" + "="*80)
print("Testing: '%s'" % test_text)
print("="*80)

result = matcher.match_listing(test_text, extracted_capacity=120)
if result.ssd:
    print("MATCHED: %s %s (%sGB)" % (result.ssd.brand, result.ssd.model, result.ssd.capacity_gb))
    print("Confidence: %.1f%%" % (result.confidence * 100))
    print("Method: %s" % result.method)
else:
    print("NO MATCH - Would use generic fallback")

# Check what Crucial SSDs exist
print("\n" + "="*80)
print("All Crucial SSDs in database:")
print("="*80)
crucial_ssds = [s for s in ssds if s.brand.lower() == 'crucial']
for ssd in sorted(crucial_ssds, key=lambda x: (x.model, x.capacity_gb or 0)):
    print("  ID: %d, %s %s %sGB" % (ssd.id, ssd.brand, ssd.model, ssd.capacity_gb))

# Check what SSDs have 120GB capacity
print("\n" + "="*80)
print("SSDs with ~120GB capacity:")
print("="*80)
ssd_120s = [s for s in ssds if s.capacity_gb and 100 <= s.capacity_gb <= 140]
for ssd in sorted(ssd_120s, key=lambda x: (x.brand, x.model)):
    print("  ID: %d, %s %s %sGB" % (ssd.id, ssd.brand, ssd.model, ssd.capacity_gb))
