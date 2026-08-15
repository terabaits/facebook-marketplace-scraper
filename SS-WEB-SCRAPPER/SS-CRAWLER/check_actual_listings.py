# -*- coding: utf-8 -*-
"""Check actual listing data from database."""
import sys
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import ComputerListingRepository
from src.utils.config import AppConfig

config = AppConfig()
init_database(config.database)
db = get_db_manager()

with db.get_session() as session:
    # Check if listings exist in database
    for listing_id in ['gccgg', 'ixefo', 'fkffx']:
        listing = ComputerListingRepository.get_by_listing_id(session, listing_id)
        if listing:
            print(f"\n=== Listing: {listing_id} ===")
            print(f"Title: {listing.title}")
            print(f"Description: {listing.description[:200] if listing.description else 'None'}...")
            print(f"Price: {listing.price_eur}")
            print(f"Matched CPU ID: {listing.matched_cpu_id}")
            print(f"Matched GPU ID: {listing.matched_gpu_id}")
            print(f"Matched SSD ID: {listing.matched_ssd_id}")
            print(f"Matched PSU ID: {listing.matched_psu_id}")
        else:
            print(f"\nListing {listing_id}: NOT FOUND in database")
