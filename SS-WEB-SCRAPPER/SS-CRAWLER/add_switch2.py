#!/usr/bin/env python3
"""Add Nintendo Switch 2 to console database."""
import psycopg2

DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "ss_market"
DB_USER = "crawler"
DB_PASS = "crawler_pass"

def main():
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    
    try:
        with conn.cursor() as cur:
            # Check if Switch 2 exists
            cur.execute("SELECT id FROM console_reference WHERE LOWER(name) LIKE '%switch 2%'")
            if cur.fetchone():
                print("Nintendo Switch 2 already exists")
                return
            
            # Add Switch 2
            cur.execute("""
                INSERT INTO console_reference (name, company, generation, search_keywords, normalized_name)
                VALUES ('Nintendo Switch 2', 'Nintendo', 9, 
                        ARRAY['switch 2', 'nintendo switch 2', 'switch2'], 
                        'nintendo switch 2')
            """)
            print("Added Nintendo Switch 2")
            
            conn.commit()
            
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
