#!/usr/bin/env python3
"""Add listing_versions table for full change tracking"""
import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\src')

import psycopg2
from utils.config import AppConfig

config = AppConfig.from_yaml(r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\config.yaml')
conn = psycopg2.connect(
    host=config.database.host,
    port=config.database.port,
    database=config.database.name,
    user=config.database.user,
    password=config.database.password
)
cursor = conn.cursor()

# Create listing_versions table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS listing_versions (
        id SERIAL PRIMARY KEY,
        listing_id VARCHAR(50) REFERENCES listings(listing_id) ON DELETE CASCADE,
        version_number INTEGER NOT NULL,
        title VARCHAR(500),
        description TEXT,
        price_eur DECIMAL(10,2),
        seller_location VARCHAR(200),
        matched_ssd_id INTEGER,
        ssd_confidence_score DECIMAL(4,2),
        content_hash VARCHAR(64),
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(listing_id, version_number)
    );
    
    CREATE INDEX IF NOT EXISTS idx_versions_listing ON listing_versions(listing_id);
    CREATE INDEX IF NOT EXISTS idx_versions_created ON listing_versions(created_at);
""")

conn.commit()
cursor.close()
conn.close()
print("Created listing_versions table")
