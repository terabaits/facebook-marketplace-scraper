"""Simple restore using pg_restore logic - just execute the SQL file."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from sqlalchemy import text

def restore_backup(backup_file: str):
    """Restore database by parsing SQL file manually."""
    print(f"Restoring from {backup_file}...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    # Read the SQL file
    with open(backup_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Parse COPY sections
    import re
    
    # Find COPY section for listings
    copy_match = re.search(
        r'COPY public\.listings \([^)]+\) FROM stdin;\n(.*?)\\\.',
        content,
        re.DOTALL
    )
    
    if not copy_match:
        print("No listings COPY section found!")
        return False
    
    data_section = copy_match.group(1).strip()
    lines = data_section.split('\n')
    
    print(f"Found {len(lines)} listing rows in backup")
    
    # Parse column names from the COPY header
    header_match = re.search(r'COPY public\.listings \(([^)]+)\) FROM', content)
    columns = [c.strip() for c in header_match.group(1).split(',')]
    print(f"Columns: {len(columns)}")
    
    # Clear current listings first (safely)
    with get_session() as session:
        print("Clearing current listings...")
        session.execute(text("DELETE FROM listing_versions"))
        session.execute(text("DELETE FROM listings"))
        session.commit()
        print("Cleared existing listings")
    
    # Insert data
    inserted = 0
    failed = 0
    
    with get_session() as session:
        for line in lines:
            if not line.strip():
                continue
            
            # Split by tab
            values = line.split('\t')
            
            if len(values) != len(columns):
                failed += 1
                if failed < 3:
                    print(f"  Skipping row with {len(values)} values (expected {len(columns)})")
                continue
            
            try:
                # Build INSERT
                col_names = ', '.join(columns)
                placeholders = ', '.join([f':{c}' for c in columns])
                
                # Create params dict
                params = {}
                for i, col in enumerate(columns):
                    val = values[i]
                    if val == '\\N':
                        params[col] = None
                    else:
                        params[col] = val
                
                sql = f"INSERT INTO listings ({col_names}) VALUES ({placeholders})"
                session.execute(text(sql), params)
                inserted += 1
                
                if inserted % 100 == 0:
                    print(f"  Inserted {inserted} rows...")
                    session.commit()
                    
            except Exception as e:
                failed += 1
                if failed < 3:
                    print(f"  Error: {e}")
        
        session.commit()
    
    print(f"\n✓ Restore complete: {inserted} listings inserted, {failed} failed")
    return True

if __name__ == "__main__":
    backup = sys.argv[1] if len(sys.argv) > 1 else "backup_2026-05-16_215707.sql"
    restore_backup(backup)
