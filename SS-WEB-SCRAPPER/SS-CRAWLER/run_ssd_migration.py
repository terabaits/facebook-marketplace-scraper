"""Migration script to add SSD2 and SSD3 columns for multi-SSD support.
Run this script to add the new columns to the computer_listings table.
"""
import sys
import psycopg2
from psycopg2 import sql

def run_migration():
    # Database connection parameters
    db_config = {
        'host': 'localhost',
        'port': 5433,
        'database': 'ss_market',
        'user': 'crawler',
        'password': 'crawler_pass'
    }
    
    # SQL statements to add new columns
    migration_sql = """
    -- Add columns to computer_listings table
    ALTER TABLE computer_listings 
        ADD COLUMN IF NOT EXISTS matched_ssd2_id INTEGER,
        ADD COLUMN IF NOT EXISTS matched_ssd3_id INTEGER,
        ADD COLUMN IF NOT EXISTS ssd2_confidence FLOAT,
        ADD COLUMN IF NOT EXISTS ssd3_confidence FLOAT,
        ADD COLUMN IF NOT EXISTS ssd2_match_method VARCHAR(50),
        ADD COLUMN IF NOT EXISTS ssd3_match_method VARCHAR(50);
    
    -- Add columns to computer_listing_versions table (for version history)
    ALTER TABLE computer_listing_versions 
        ADD COLUMN IF NOT EXISTS matched_ssd2_id INTEGER,
        ADD COLUMN IF NOT EXISTS matched_ssd3_id INTEGER,
        ADD COLUMN IF NOT EXISTS ssd2_confidence FLOAT,
        ADD COLUMN IF NOT EXISTS ssd3_confidence FLOAT;
    
    -- Create indexes for the new columns (optional but recommended for queries)
    CREATE INDEX IF NOT EXISTS idx_computer_listings_ssd2_id ON computer_listings(matched_ssd2_id);
    CREATE INDEX IF NOT EXISTS idx_computer_listings_ssd3_id ON computer_listings(matched_ssd3_id);
    """
    
    conn = None
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        print("Running migration...")
        cursor.execute(migration_sql)
        conn.commit()
        
        print("✅ Migration completed successfully!")
        
        # Verify the columns were added
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'computer_listings' 
            AND column_name IN ('matched_ssd2_id', 'matched_ssd3_id', 'ssd2_confidence', 'ssd3_confidence', 'ssd2_match_method', 'ssd3_match_method')
            ORDER BY column_name;
        """)
        
        columns = cursor.fetchall()
        print("\n📋 Added columns:")
        for col_name, data_type in columns:
            print(f"  - {col_name}: {data_type}")
            
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("\n🔌 Database connection closed.")

if __name__ == "__main__":
    print("=" * 60)
    print("Multi-SSD Support Migration")
    print("=" * 60)
    print("\nThis script will add SSD2 and SSD3 columns to the database.\n")
    
    # Optional: add confirmation prompt
    # response = input("Proceed with migration? [y/N]: ")
    # if response.lower() != 'y':
    #     print("Migration cancelled.")
    #     sys.exit(0)
    
    run_migration()
