# -*- coding: utf-8 -*-
import sys
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port="5433",
    database="ss_market",
    user="crawler",
    password="crawler_pass"
)

cursor = conn.cursor()

# Create flagged_listings table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS flagged_listings (
        id SERIAL PRIMARY KEY,
        listing_id VARCHAR(255) NOT NULL UNIQUE,
        console_name VARCHAR(255),
        reason TEXT,
        flagged_at TIMESTAMP DEFAULT NOW(),
        is_active BOOLEAN DEFAULT TRUE
    )
""")

# Create indexes
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_flagged_listing_id ON flagged_listings(listing_id)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_flagged_console ON flagged_listings(console_name)
""")

conn.commit()
cursor.close()
conn.close()

print("Flagged listings table created successfully!")
