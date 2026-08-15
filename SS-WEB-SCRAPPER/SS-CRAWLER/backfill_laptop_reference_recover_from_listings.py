"""
Recover model from laptop_listings.model for laptop_reference rows that have
empty/unknown model. This restores the lost data when the model column
was corrupted or set to empty.
"""
import psycopg2

DB_DSN = dict(host="localhost", port=5433, dbname="ss_market", user="crawler", password="crawler_pass")

conn = psycopg2.connect(**DB_DSN)
cur = conn.cursor()

# Find the most common non-empty model from the listings for each empty-model ref
cur.execute("""
    SELECT lr.id, lr.brand, lr.model_number,
           ll.model as listing_model, COUNT(*) as cnt
    FROM laptop_reference lr
    JOIN laptop_listings ll ON ll.laptop_reference_id = lr.id
    WHERE (lr.model = '' OR lr.model IS NULL OR lr.model = 'Unknown')
      AND lr.brand NOT IN ('Cits', '(unknown)')
      AND ll.model IS NOT NULL AND ll.model <> ''
    GROUP BY lr.id, lr.brand, lr.model_number, ll.model
    ORDER BY lr.id, cnt DESC
""")

# Aggregate per ref_id, taking the most common listing model
from collections import defaultdict
ref_candidates = defaultdict(list)  # ref_id -> [(listing_model, count)]
for r in cur.fetchall():
    ref_candidates[r[0]].append((r[3], r[4]))

# For each ref, pick the most common candidate
recovered = []
for ref_id, cands in ref_candidates.items():
    cands.sort(key=lambda x: -x[1])
    best_model, _cnt = cands[0]
    if not best_model.strip():
        continue
    recovered.append((ref_id, best_model))

print(f"Recoverable refs: {len(recovered)}")
for ref_id, m in recovered:
    print(f"  [{ref_id}] -> {m!r}")

# Update
if recovered and "--apply" in __import__("sys").argv:
    for ref_id, m in recovered:
        cur.execute(
            "UPDATE laptop_reference SET model = %s, updated_at = NOW() WHERE id = %s",
            (m, ref_id),
        )
    conn.commit()
    print(f"\nRecovered {len(recovered)} models")
else:
    print("\n(Dry run, no changes. Use --apply to actually update.)")

cur.close()
conn.close()
