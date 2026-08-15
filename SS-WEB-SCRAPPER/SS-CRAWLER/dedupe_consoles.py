#!/usr/bin/env python3
"""Remove duplicate console entries."""
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
            print("Checking for duplicates...")
            
            # Check duplicates in console_reference
            cur.execute("""
                SELECT normalized_name, COUNT(*) as cnt
                FROM console_reference
                GROUP BY normalized_name
                HAVING COUNT(*) > 1
                ORDER BY cnt DESC;
            """)
            dups = cur.fetchall()
            
            if dups:
                print(f"\nFound {len(dups)} duplicates:")
                for dup in dups[:20]:
                    print(f"  '{dup[0]}': {dup[1]} entries")
                
                # Remove duplicates, keeping lowest ID
                print("\nRemoving duplicates...")
                cur.execute("""
                    DELETE FROM console_reference
                    WHERE id NOT IN (
                        SELECT MIN(id)
                        FROM console_reference
                        GROUP BY normalized_name
                    );
                """)
                print(f"  Deleted {cur.rowcount} duplicates from console_reference")
            
            # Check duplicates in console_variants
            cur.execute("""
                SELECT normalized_name, COUNT(*) as cnt
                FROM console_variants
                GROUP BY normalized_name
                HAVING COUNT(*) > 1
                ORDER BY cnt DESC;
            """)
            dups = cur.fetchall()
            
            if dups:
                print(f"\nFound {len(dups)} duplicate variants")
                cur.execute("""
                    DELETE FROM console_variants
                    WHERE id NOT IN (
                        SELECT MIN(id)
                        FROM console_variants
                        GROUP BY normalized_name
                    );
                """)
                print(f"  Deleted {cur.rowcount} duplicates from console_variants")
            
            # Check duplicates in console_editions
            cur.execute("""
                SELECT normalized_name, COUNT(*) as cnt
                FROM console_editions
                GROUP BY normalized_name
                HAVING COUNT(*) > 1
                ORDER BY cnt DESC;
            """)
            dups = cur.fetchall()
            
            if dups:
                print(f"\nFound {len(dups)} duplicate editions")
                cur.execute("""
                    DELETE FROM console_editions
                    WHERE id NOT IN (
                        SELECT MIN(id)
                        FROM console_editions
                        GROUP BY normalized_name
                    );
                """)
                print(f"  Deleted {cur.rowcount} duplicates from console_editions")
            
            conn.commit()
            
            # Show final counts
            cur.execute("SELECT COUNT(*) FROM console_reference")
            ref_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM console_variants")
            var_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM console_editions")
            ed_count = cur.fetchone()[0]
            
            print(f"\nFinal counts:")
            print(f"  Consoles: {ref_count}")
            print(f"  Variants: {var_count}")
            print(f"  Editions: {ed_count}")
            print("\n✓ Done!")
            
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
