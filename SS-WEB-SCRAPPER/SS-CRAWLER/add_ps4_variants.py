#!/usr/bin/env python3
"""Add PS4 variants to database"""
import psycopg2
from psycopg2.extras import execute_values

def add_ps4_variants():
    conn = psycopg2.connect(
        host="localhost",
        port="5433",
        dbname="ss_market",
        user="crawler",
        password="crawler_pass"
    )
    
    try:
        with conn.cursor() as cur:
            # Find PlayStation 4 ID
            cur.execute("SELECT id FROM console_reference WHERE name = 'PlayStation 4'")
            ps4_id = cur.fetchone()
            if not ps4_id:
                print("PlayStation 4 not found!")
                return
            ps4_id = ps4_id[0]
            
            print(f"Found PlayStation 4 (ID: {ps4_id})")
            
            # Check existing variants
            cur.execute("SELECT COUNT(*) FROM console_variants WHERE console_id = %s", (ps4_id,))
            existing = cur.fetchone()[0]
            print(f"Existing variants: {existing}")
            
            if existing > 0:
                print("Variants already exist, skipping")
                return
            
            # Add variants
            variants = [
                (ps4_id, 'PlayStation 4', 'Standard', 500, 'playstation 4', ['ps4', 'playstation 4']),
                (ps4_id, 'PlayStation 4 Slim', 'Slim', 500, 'playstation 4 slim', ['ps4 slim', 'playstation 4 slim']),
                (ps4_id, 'PlayStation 4 Pro', 'Pro', 1000, 'playstation 4 pro', ['ps4 pro', 'playstation 4 pro']),
            ]
            
            execute_values(cur, """
                INSERT INTO console_variants (console_id, model_name, sku, storage_gb, normalized_name, search_keywords)
                VALUES %s
            """, variants)
            
            print(f"Added {len(variants)} variants")
            conn.commit()
            print("Done!")
            
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_ps4_variants()
