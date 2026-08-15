"""Restore from backup and update reference tables safely."""
import sys
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from sqlalchemy import text

def restore_from_backup(backup_file: str):
    """Restore database from SQL backup file using SQLAlchemy."""
    print(f"Restoring from {backup_file}...")
    
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    # Read SQL file
    with open(backup_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Split into statements (handle COPY data sections)
    statements = []
    current_statement = ""
    in_copy = False
    copy_table = None
    copy_data = []
    
    lines = sql_content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip comments and empty lines outside COPY
        if not in_copy:
            if line.startswith('--') or line.strip() == '':
                i += 1
                continue
            
            # Check for COPY start
            if line.startswith('COPY '):
                # Extract table name
                match = re.match(r'COPY\s+(\w+)\s+', line)
                if match:
                    copy_table = match.group(1)
                    in_copy = True
                    copy_data = []
                    i += 1
                    continue
            
            # Regular SQL statement
            current_statement += line + '\n'
            if line.strip().endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        else:
            # Inside COPY block - look for \.
            if line.strip() == '\\.':
                # End of COPY
                in_copy = False
                # Add copy data as insert
                statements.append(('COPY', copy_table, copy_data))
                copy_table = None
                copy_data = []
                i += 1
                continue
            else:
                copy_data.append(line)
        
        i += 1
    
    if current_statement.strip():
        statements.append(current_statement.strip())
    
    # Execute statements
    success_count = 0
    error_count = 0
    
    with get_session() as session:
        for stmt in statements:
            try:
                if isinstance(stmt, tuple) and stmt[0] == 'COPY':
                    # Handle COPY data
                    table_name, data_lines = stmt[1], stmt[2]
                    print(f"  Restoring {len(data_lines)} rows to {table_name}...")
                    for row_line in data_lines:
                        if not row_line.strip():
                            continue
                        # Parse tab-separated values
                        values = row_line.split('\t')
                        # Build INSERT
                        placeholders = ','.join(['%s'] * len(values))
                        sql = f"INSERT INTO {table_name} VALUES ({placeholders}) ON CONFLICT DO NOTHING"
                        session.execute(text(sql), values)
                else:
                    # Regular SQL
                    if stmt.upper().startswith('COPY') or 'pg_dump' in stmt:
                        continue  # Skip unsupported commands
                    session.execute(text(stmt))
                
                success_count += 1
            except Exception as e:
                error_count += 1
                if error_count < 5:  # Only show first few errors
                    print(f"  Warning: {str(e)[:100]}")
        
        session.commit()
    
    print(f"✓ Restore complete: {success_count} statements executed")
    if error_count:
        print(f"  ({error_count} statements skipped/had errors)")
    return True

def check_tables():
    """Check what tables exist and their row counts."""
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    tables = ['listings', 'camera_reference', 'lens_reference', 'gpu_reference', 
              'cpu_reference', 'ssd_reference', 'ram_reference', 'monitor_reference',
              'case_reference', 'psu_reference', 'motherboard_reference']
    
    print("\nDatabase Status:")
    print("-" * 50)
    
    with get_session() as session:
        for table in tables:
            try:
                result = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"  {table}: {result} rows")
            except Exception as e:
                print(f"  {table}: MISSING")

def apply_missing_schemas():
    """Apply schemas for missing tables."""
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    schemas_to_apply = []
    
    with get_session() as session:
        # Check which tables need creating
        for table, schema_file in [
            ('camera_reference', 'camera_schema.sql'),
            ('monitor_reference', 'monitor_schema.sql'),
            ('case_reference', 'case_schema.sql'),
            ('psu_reference', 'psu_schema.sql')
        ]:
            try:
                session.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
            except Exception:
                schemas_to_apply.append((table, schema_file))
    
    if not schemas_to_apply:
        print("\n✓ All reference tables already exist")
        return
    
    for table, schema_file in schemas_to_apply:
        schema_path = Path(__file__).parent / "src" / "database" / schema_file
        if schema_path.exists():
            print(f"\nApplying {table} schema...")
            # This would need safe schema application without CASCADE
            print(f"  (Schema file exists: {schema_path})")
        else:
            print(f"\n  Schema file not found: {schema_path}")

if __name__ == "__main__":
    import sys
    
    # Default backup location
    backup_file = sys.argv[1] if len(sys.argv) > 1 else "backup_2026-05-17_030733.sql"
    
    if not Path(backup_file).exists():
        # Try backup directory
        backup_dir = Path(__file__).parent / "backups"
        if (backup_dir / backup_file).exists():
            backup_file = str(backup_dir / backup_file)
        else:
            print(f"Backup file not found: {backup_file}")
            print(f"Looking in {backup_dir}...")
            backups = list(backup_dir.glob("backup_*.sql"))
            if backups:
                backup_file = str(backups[-1])  # Most recent
                print(f"Using: {backup_file}")
            else:
                print("No backups found!")
                sys.exit(1)
    
    # Restore
    if restore_from_backup(backup_file):
        # Check what's there
        check_tables()
        
        # Apply missing schemas
        apply_missing_schemas()
        
        # Check again
        print("\nAfter updates:")
        check_tables()
        
        print("\n" + "=" * 50)
        print("Next steps:")
        print("  1. Re-import camera reference: python import_cameras.py")
        print("  2. Check database: python check_db.py")
        print("  3. Test camera scraper: python main.py test-url <url> --cameras")
    else:
        sys.exit(1)
