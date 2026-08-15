"""Show lens_reference table details."""
import sys
sys.path.insert(0, '.')
from src.database.connection import init_database, get_session
from src.utils.config import DatabaseConfig
from sqlalchemy import text

config = DatabaseConfig(
    host='localhost',
    port=5433,
    name='ss_market',
    user='crawler',
    password='crawler_pass'
)
init_database(config)

with get_session() as session:
    # Show table structure
    print("=== lens_reference TABLE STRUCTURE ===")
    result = session.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'lens_reference'
        ORDER BY ordinal_position
    """)).fetchall()
    for col in result:
        print(f"  {col[0]}: {col[1]} (nullable: {col[2]})")
    
    print("\n=== SAMPLE DATA (first 10 lenses) ===")
    result = session.execute(text("""
        SELECT id, brand, mount, lens_name, focal_length_mm, max_aperture
        FROM lens_reference
        ORDER BY id
        LIMIT 10
    """)).fetchall()
    for row in result:
        print(f"  {row[0]}: {row[1]} {row[3]} ({row[4]}mm f/{row[5]}) [{row[2]} mount]")
    
    print("\n=== TOTAL COUNT ===")
    result = session.execute(text("SELECT COUNT(*) FROM lens_reference")).fetchone()
    print(f"  Total lenses: {result[0]}")
    
    # Count by brand
    print("\n=== LENSES BY BRAND ===")
    result = session.execute(text("""
        SELECT brand, COUNT(*) 
        FROM lens_reference 
        GROUP BY brand 
        ORDER BY COUNT(*) DESC
    """)).fetchall()
    for row in result:
        print(f"  {row[0]}: {row[1]}")
