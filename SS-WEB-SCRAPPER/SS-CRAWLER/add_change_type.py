#!/usr/bin/env python3
"""Add change_type column to price_history"""
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

# Check if change_type column exists
cursor.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'price_history' AND column_name = 'change_type'
""")

if cursor.fetchone():
    print('change_type column already exists')
else:
    cursor.execute('ALTER TABLE price_history ADD COLUMN change_type VARCHAR(100)')
    conn.commit()
    print('Added change_type column')

cursor.close()
conn.close()
