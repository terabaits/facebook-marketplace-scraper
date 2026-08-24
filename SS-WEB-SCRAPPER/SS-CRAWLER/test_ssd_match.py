"""Quick test of SSD matcher on Andele titles - using the matcher module from current cwd."""
import os
os.environ.setdefault('PGHOST', 'localhost')
os.environ.setdefault('PGPORT', '5433')
os.environ.setdefault('PGUSER', 'crawler')
os.environ.setdefault('PGPASSWORD', 'crawler_pass')
os.environ.setdefault('PGDATABASE', 'ss_market')

import psycopg2
from psycopg2.extras import RealDictCursor
from src.scraper.ssd_matcher import SSDMatcher

conn = psycopg2.connect(host='localhost', port=5433, user='crawler', password='crawler_pass', dbname='ss_market')
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute('SELECT id, brand, model, capacity_gb, normalized_name FROM ssd_reference')
ssds_raw = cur.fetchall()
conn.close()
# Use SSDReference pydantic objects (the matcher needs .brand/.model attrs)
from src.models.schemas import SSDReference
from src.scraper.matcher import normalize_text
ssds = []
for r in ssds_raw:
    norm = normalize_text(f"{r['brand']} {r['model']}")
    ssds.append(SSDReference(
        id=r['id'], brand=r['brand'], model=r['model'],
        capacity_gb=r['capacity_gb'], normalized_name=norm
    ))

print(f'Loaded {len(ssds)} SSDs')

matcher = SSDMatcher(ssds)
test_cases = [
    ('Intel S3610 800Gb SSD disks', 'Intel S3610 800Gb SSD disks, servera SSD, datacenteriem. 2.5 inch SATA. 80PBW endurance.'),
    ('Samsung PM883 1,92TB serveru SSD', 'Samsung PM883 1,92TB serveru SSD disks, SATA 2.5 inch. Modelis MZILH1T9HCHP-000H7.'),
    ('Samsung 850 EVO 1Tb SSD 96%', 'Samsung 850 EVO 1Tb SSD 96% veseliba. Stavoklis labs.'),
    ('KingDian 120Gb Sata m.2 2242 SSD disks', 'KingDian 120Gb Sata m.2 2242 SSD disks'),
    ('Adata SU720 1Tb SSD', 'Adata SU720 1Tb SSD. Stavoklis jauns.'),
]
for title, full in test_cases:
    r = matcher.match(title, full)
    ssd_str = f"{r.ssd.brand} {r.ssd.model} {r.ssd.capacity_gb}GB" if r.ssd else 'NONE'
    print(f'TITLE: {title[:60]}')
    print(f'  -> ssd: {ssd_str}, conf: {r.confidence:.3f}, method: {r.method}')
