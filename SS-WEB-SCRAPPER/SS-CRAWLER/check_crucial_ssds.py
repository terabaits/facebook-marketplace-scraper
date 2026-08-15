#!/usr/bin/env python3
"""Check what Crucial SSDs exist in the database."""

import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\src')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import SSDModel

# Connect to database
engine = create_engine('postgresql+psycopg2://crawler:crawler_pass@localhost:5433/ss_market')
Session = sessionmaker(bind=engine)
session = Session()

# Get all Crucial SSDs
crucial_ssds = session.query(SSDModel).filter(SSDModel.brand.ilike('%crucial%')).all()

print("All Crucial SSDs in database:")
print("=" * 80)
for ssd in crucial_ssds:
    print(f"ID: {ssd.id}, Brand: {ssd.brand}, Model: {ssd.model}, Capacity: {ssd.capacity_gb}GB")
    print(f"    Search keywords: {ssd.search_keywords}")
    print()

# Also check for any SSDs with 120GB capacity
print("\nAll SSDs with ~120GB capacity:")
print("=" * 80)
ssd_120s = session.query(SSDModel).filter(SSDModel.capacity_gb.between(100, 140)).all()
for ssd in ssd_120s:
    print(f"ID: {ssd.id}, Brand: {ssd.brand}, Model: {ssd.model}, Capacity: {ssd.capacity_gb}GB")
