#!/usr/bin/env python3
"""Add PlayStation 5 Slim to console database"""
import psycopg2
from psycopg2.extras import execute_values

def add_ps5_slim():
    conn = psycopg2.connect(
        host="localhost",
        port="5433",
        dbname="ss_market",
        user="crawler",
        password="crawler_pass"
    )
    
    try:
        with conn.cursor() as cur:
            # Check if PS5 Slim already exists
            cur.execute("SELECT id FROM console_reference WHERE name = 'PlayStation 5 Slim'")
            if cur.fetchone():
                print("PlayStation 5 Slim already exists in database")
                return
            
            # Get next available ID
            cur.execute("SELECT MAX(id) FROM console_reference")
            max_id = cur.fetchone()[0] or 0
            new_id = max_id + 1
            
            # Add PlayStation 5 Slim to console_reference
            cur.execute("""
                INSERT INTO console_reference (id, name, company, generation, release_date, normalized_name, search_keywords)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (new_id, 'PlayStation 5 Slim', 'Sony', 9, '2023', 'playstation 5 slim', ['ps5 slim', 'playstation 5 slim']))
            
            print(f"Added console_reference: PlayStation 5 Slim (ID: {new_id})")
            
            # Add variants
            variants = [
                (new_id, 'PlayStation 5 Slim', 'Slim', 1024, 'playstation 5 slim', ['slim', 'ps5 slim', 'playstation 5 slim']),
                (new_id, 'PlayStation 5 Slim Digital', 'Slim Digital', 1024, 'playstation 5 slim digital', ['slim digital', 'ps5 slim digital']),
            ]
            
            execute_values(cur, """
                INSERT INTO console_variants (console_id, model_name, sku, storage_gb, normalized_name, search_keywords)
                VALUES %s
            """, variants)
            
            print(f"Added {len(variants)} variants to console_variants")
            
            conn.commit()
            print("✓ PlayStation 5 Slim added successfully!")
            
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_ps5_slim()
