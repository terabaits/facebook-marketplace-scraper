#!/usr/bin/env python3
"""Apply database schema updates."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import psycopg2
from src.utils.config import AppConfig

import os
os.chdir(str(Path(__file__).parent))

config = AppConfig.from_yaml("config.yaml")

# Read schema file
schema_path = Path(__file__).parent / "src" / "database" / "schema.sql"
with open(schema_path, 'r', encoding='utf-8') as f:
    schema_sql = f.read()

# Connect and execute
conn = psycopg2.connect(
    host=config.database.host,
    port=config.database.port,
    database=config.database.name,
    user=config.database.user,
    password=config.database.password
)

cursor = conn.cursor()

# Split and execute statements
statements = [s.strip() for s in schema_sql.split(';') if s.strip()]

for stmt in statements:
    try:
        cursor.execute(stmt)
        print(f"OK: {stmt[:50]}...")
    except Exception as e:
        # Skip if already exists
        if "already exists" in str(e).lower():
            print(f"SKIP (exists): {stmt[:40]}...")
        else:
            print(f"ERROR: {e}")
            print(f"  Statement: {stmt[:80]}...")

conn.commit()
cursor.close()
conn.close()

print("\nSchema applied!")
