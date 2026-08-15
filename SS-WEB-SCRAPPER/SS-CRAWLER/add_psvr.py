#!/usr/bin/env python3
"""Add PlayStation VR and VR2 to database"""
import psycopg2

def add_psvr():
    conn = psycopg2.connect(
        host="localhost",
        port="5433",
        dbname="ss_market",
        user="crawler",
        password="crawler_pass"
    )
    
    try:
        with conn.cursor() as cur:
            # Check if PSVR already exists
            cur.execute("SELECT id FROM console_reference WHERE name IN ('PlayStation VR', 'PlayStation VR2')")
            existing = cur.fetchall()
            if existing:
                print(f"Already exists: {[r[0] for r in existing]}")
            
            # Get next available IDs
            cur.execute("SELECT MAX(id) FROM console_reference")
            max_id = cur.fetchone()[0] or 0
            
            # Add PlayStation VR
            psvr_id = max_id + 1
            cur.execute("""
                INSERT INTO console_reference (id, name, company, generation, release_date, normalized_name, search_keywords)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (psvr_id, 'PlayStation VR', 'Sony', 0, '2016', 'playstation vr', ['psvr', 'playstation vr', 'ps vr']))
            print(f"Added PlayStation VR (ID: {psvr_id})")
            
            # Add PlayStation VR2
            psvr2_id = max_id + 2
            cur.execute("""
                INSERT INTO console_reference (id, name, company, generation, release_date, normalized_name, search_keywords)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (psvr2_id, 'PlayStation VR2', 'Sony', 0, '2023', 'playstation vr2', ['psvr2', 'playstation vr2', 'ps vr2', 'vr2']))
            print(f"Added PlayStation VR2 (ID: {psvr2_id})")
            
            # Add variants
            cur.execute("SELECT MAX(id) FROM console_variants")
            max_vid = cur.fetchone()[0] or 0
            
            variants = [
                (max_vid + 1, psvr_id, 'PlayStation VR', 'PSVR', ['psvr', 'playstation vr']),
                (max_vid + 2, psvr2_id, 'PlayStation VR2', 'PSVR2', ['psvr2', 'playstation vr2', 'vr2']),
            ]
            
            for vid, cid, name, sku, kws in variants:
                norm = name.lower().replace(' ', '')
                cur.execute("""
                    INSERT INTO console_variants (id, console_id, model_name, sku, normalized_name, search_keywords)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (vid, cid, name, sku, norm, kws))
                print(f"Added variant: {name}")
            
            conn.commit()
            print("Done!")
            
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_psvr()
