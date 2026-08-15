#!/usr/bin/env python3
"""Fix Xbox 360 variant names"""
import psycopg2

def fix():
    conn = psycopg2.connect(host="localhost", port="5433", dbname="ss_market", user="crawler", password="crawler_pass")
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM console_reference WHERE name = 'Xbox 360'")
            xid = cur.fetchone()
            if not xid:
                print("Xbox 360 not found")
                return
            xid = xid[0]
            
            cur.execute("SELECT id, model_name, normalized_name FROM console_variants WHERE console_id = %s", (xid,))
            for vid, name, norm in cur.fetchall():
                if name.startswith("Xbox 360 Xbox 360"):
                    new_name = name.replace("Xbox 360 Xbox 360 ", "Xbox 360 ", 1)
                    new_norm = norm.replace("xbox 360 xbox 360 ", "xbox 360 ", 1)
                    print(f"Fix {vid}: '{name}' -> '{new_name}'")
                    cur.execute("UPDATE console_variants SET model_name = %s, normalized_name = %s WHERE id = %s", (new_name, new_norm, vid))
            conn.commit()
            print("Done")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix()
