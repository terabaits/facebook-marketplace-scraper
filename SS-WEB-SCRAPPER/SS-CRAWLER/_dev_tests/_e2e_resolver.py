"""End-to-end test: simulate a new laptop listing flowing through the resolver."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import text

# Initialize the DB the way the scraper does
from src.database.connection import init_database, get_session
from src.utils.config import DatabaseConfig
from src.scraper.laptop_reference_resolver import LaptopReferenceResolver

# Use the same config the scraper uses
import yaml
with open(ROOT / "config.yaml") as f:
    cfg = yaml.safe_load(f) or {}

db_cfg = cfg.get("database", {})
init_database(DatabaseConfig(
    host=db_cfg.get("host", "localhost"),
    port=int(db_cfg.get("port", 5433)),
    name=db_cfg.get("name") or db_cfg.get("database", "ss_market"),
    user=db_cfg.get("user", "crawler"),
    password=db_cfg.get("password", "crawler_pass"),
))

conn = psycopg2.connect(host='localhost', port=5433, database='ss_market',
                        user='crawler', password='crawler_pass')
cur = conn.cursor(cursor_factory=RealDictCursor)

# Snapshot before
cur.execute('SELECT COUNT(*) AS n FROM laptop_reference')
refs_before = cur.fetchone()['n']
cur.execute("SELECT COUNT(*) AS n FROM laptop_reference WHERE brand='E2ETestBrand'")
e2e_before = cur.fetchone()['n']

print(f"Refs before: {refs_before}, E2ETestBrand refs: {e2e_before}")
print()

# Run the resolver scenarios inside one session
with get_session() as s:
    r = LaptopReferenceResolver(s)

    # Scenario A: existing model (case variant)
    rid, key = r.resolve('Apple', 'macbook air', '13"')  # lowercase
    print(f'A. existing/case-variant:  id={rid}  key={key}')

    # Scenario B: existing model (whitespace + case)
    rid, key = r.resolve('Dell', ' XPS  13 ', '13"')
    print(f'B. existing/whitespace:    id={rid}  key={key}')

    # Scenario C: brand new model
    rid, key = r.resolve('E2ETestBrand', 'NewModel-X1', '15',
                         'Some description with 2560x1440 resolution')
    print(f'C. brand new:              id={rid}  key={key}')

    # Scenario D: same new model again (idempotent)
    rid2, key2 = r.resolve('E2ETestBrand', 'NewModel-X1', '15')
    print(f'D. idempotent new model:    id={rid2}  key={key2}  same={rid==rid2}')

    # Scenario E: NULL brand (no reference)
    rid, key = r.resolve(None, 'SomeModel', '13')
    print(f'E. NULL brand:             id={rid}  key={key!r}')

    # Scenario F: NULL model (no reference)
    rid, key = r.resolve('Apple', None, '13')
    print(f'F. NULL model:             id={rid}  key={key!r}')

    # Scenario G: parens in model
    rid, key = r.resolve('Apple', 'Macbook Pro (2020)', '13')
    print(f'G. parens stripped:         id={rid}  key={key!r}')

    # Scenario H: typo stays split (admin merge later)
    rid, key = r.resolve('E2ETestBrand', 'NewModel-X1', '15')  # already created
    rid2, key2 = r.resolve('E2ETestBrand', 'NewModel-XII', '15')  # typo stays separate
    print(f'H. typo stays split:       id1={rid}  key1={key!r}')
    print(f'                            id2={rid2}  key2={key2!r}  diff={rid != rid2}')

    # Simulate inserting a laptop_listings row with the resolved FK
    s.execute(text("""
        INSERT INTO laptop_listings (
            listing_id, title, description, price_eur, seller_location,
            listing_url, image_url, date_posted,
            brand, model, display_size, cpu_raw,
            ram_gb, storage_gb, storage_type,
            seller_type, condition_state,
            content_hash, is_active, source, laptop_reference_id
        ) VALUES (
            'e2etest001', 'E2E test listing', 'desc', 100.00, 'Riga',
            'https://example.com', NULL, NOW(),
            'E2ETestBrand', 'NewModel-X1', '15', 'Test CPU',
            16, 512, 'SSD',
            'private', 'new',
            'e2e_hash', true, 'e2e', :rid
        )
    """), {"rid": rid})
    s.commit()
    print()
    print('Inserted test listing e2etest001 with FK to', rid)

# After-commit snapshot
cur.execute('SELECT COUNT(*) AS n FROM laptop_reference')
refs_after = cur.fetchone()['n']
cur.execute("SELECT COUNT(*) AS n FROM laptop_reference WHERE brand='E2ETestBrand'")
e2e_after = cur.fetchone()['n']
cur.execute("SELECT COUNT(*) AS n FROM laptop_listings WHERE listing_id='e2etest001'")
listing_count = cur.fetchone()['n']

print()
print(f"Refs after: {refs_after} (delta: +{refs_after - refs_before})")
print(f"E2ETestBrand refs: {e2e_after} (delta: +{e2e_after - e2e_before})")
print(f"Test listing rows: {listing_count}")

# Verify the resolution value was auto-extracted
cur.execute("SELECT brand, model, display_size, resolution FROM laptop_reference WHERE brand='E2ETestBrand'")
for r in cur.fetchall():
    print(f"  ref: {dict(r)}")

# Clean up the test data
print()
print("Cleaning up E2E test data...")
cur.execute("DELETE FROM laptop_listings WHERE listing_id='e2etest001'")
cur.execute("DELETE FROM laptop_reference WHERE brand='E2ETestBrand'")
conn.commit()
print("Done.")

cur.close()
conn.close()
