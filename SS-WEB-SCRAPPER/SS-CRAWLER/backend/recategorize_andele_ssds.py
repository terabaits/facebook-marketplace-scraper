"""Re-categorize Andele Mandele rows currently stored as 'general' that
the SSD matcher now identifies as SSDs.

Background: the Andele scraper was failing with
`'SSDMatcher' object has no attribute 'match'` so every Andele SSD was
saved as `category='general'`. After we added a `match()` method to
SSDMatcher, the scraper no longer errors — but the existing `general`
rows are matched-by-fingerprint and the repository returns 'unchanged',
so the rows never get re-categorized.

This script runs the SSD matcher over every Andele `general` row and
flips the category to 'ssd' (with matched_ssd_id) where confidence is
>= 0.5. Safe to run multiple times.
"""
import os
os.environ.setdefault('PGHOST', 'localhost')
os.environ.setdefault('PGPORT', '5433')
os.environ.setdefault('PGUSER', 'crawler')
os.environ.setdefault('PGPASSWORD', 'crawler_pass')
os.environ.setdefault('PGDATABASE', 'ss_market')

import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import psycopg2
from psycopg2.extras import RealDictCursor
from src.scraper.ssd_matcher import SSDMatcher
from src.scraper.matcher import normalize_text
from src.models.schemas import SSDReference

conn = psycopg2.connect(host='localhost', port=5433, user='crawler', password='crawler_pass', dbname='ss_market')
cur = conn.cursor(cursor_factory=RealDictCursor)

# Load all SSD reference rows
cur.execute('SELECT id, brand, model, capacity_gb, normalized_name FROM ssd_reference')
ssd_refs = cur.fetchall()
ssds = [
    SSDReference(
        id=r['id'], brand=r['brand'], model=r['model'],
        capacity_gb=r['capacity_gb'],
        normalized_name=r.get('normalized_name') or normalize_text(f"{r['brand']} {r['model']}")
    )
    for r in ssd_refs
]
print(f'Loaded {len(ssds)} SSD reference rows')
matcher = SSDMatcher(ssds)

# Find Andele rows still tagged as 'general'
cur.execute("""
    SELECT listing_id, title, description
    FROM listings
    WHERE source = 'andelemandele' AND category = 'general'
    ORDER BY listing_id
""")
rows = cur.fetchall()
print(f'Found {len(rows)} Andele rows in category=general')

# Match each
updates = []
skipped = []
for row in rows:
    title = row['title'] or ''
    desc = row['description'] or ''
    r = matcher.match(title, desc)
    if r and r.ssd and r.confidence >= 0.5:
        updates.append({
            'listing_id': row['listing_id'],
            'ssd_id': r.ssd.id,
            'ssd_brand': r.ssd.brand,
            'ssd_model': r.ssd.model,
            'ssd_capacity_gb': r.ssd.capacity_gb,
            'confidence': round(r.confidence, 3),
            'method': r.method,
        })
    else:
        skipped.append({
            'listing_id': row['listing_id'],
            'title': title[:50],
            'confidence': round(r.confidence, 3) if r else 0,
            'method': r.method if r else 'none',
        })

print(f'\n=== Would update {len(updates)} rows to category=ssd ===')
for u in updates[:10]:
    print(f"  {u['listing_id']}: {u['ssd_brand']} {u['ssd_model']} {u['ssd_capacity_gb']}GB "
          f"(conf={u['confidence']}, method={u['method']})")
if len(updates) > 10:
    print(f"  ... and {len(updates) - 10} more")

print(f'\n=== Would leave {len(skipped)} rows as general (no high-confidence SSD match) ===')
for s in skipped[:5]:
    print(f"  {s['listing_id']}: conf={s['confidence']}, method={s['method']} - {s['title']}")
if len(skipped) > 5:
    print(f"  ... and {len(skipped) - 5} more")

# Apply (use a non-RealDictCursor for the UPDATE because of the
# RealDictCursor.execute monkey-patch workaround in app.py:134 that
# doesn't always play well with multi-statement UPDATEs).
# ssd_match_method is VARCHAR(50) so we truncate to be safe.
if updates:
    raw = conn.cursor()
    for u in updates:
        method = (u['method'] or '')[:50]
        raw.execute("""
            UPDATE listings
            SET category = 'ssd',
                matched_ssd_id = %s,
                ssd_confidence_score = %s,
                ssd_match_method = %s
            WHERE listing_id = %s AND category = 'general'
        """, (u['ssd_id'], u['confidence'], method, u['listing_id']))
    conn.commit()
    print(f'\n[OK] Updated {len(updates)} rows')

conn.close()
