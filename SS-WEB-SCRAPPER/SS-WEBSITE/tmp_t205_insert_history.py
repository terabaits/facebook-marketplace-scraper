import psycopg2
from app import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
# Find a CPU listing that already has at least one price_history entry
cur.execute(
    "SELECT l.listing_id FROM listings l "
    "WHERE l.category='cpu' AND l.listing_id IN (SELECT listing_id FROM price_history) "
    "LIMIT 1"
)
row = cur.fetchone()
if not row:
    print("No CPU listing with existing price history found")
    cur.close()
    conn.close()
    import sys
    sys.exit(0)
lid = row[0]
print("target lid", lid)
# Insert two older price points so history length > 1
cur.execute(
    "INSERT INTO price_history (listing_id, price_eur, recorded_at) VALUES (%s, %s, NOW() - INTERVAL '1 day')",
    (lid, 99.99),
)
cur.execute(
    "INSERT INTO price_history (listing_id, price_eur, recorded_at) VALUES (%s, %s, NOW() - INTERVAL '2 days')",
    (lid, 89.99),
)
conn.commit()
cur.execute("SELECT count(*) FROM price_history WHERE listing_id=%s", (lid,))
print("new history count", cur.fetchone()[0])
cur.close()
conn.close()
