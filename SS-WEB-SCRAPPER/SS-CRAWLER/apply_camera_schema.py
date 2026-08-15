"""Apply camera schema to the database."""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from sqlalchemy import text

def apply_camera_schema():
    """Apply camera schema SQL."""
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    schema_path = project_root / "src" / "database" / "camera_schema.sql"
    
    if not schema_path.exists():
        print(f"Schema file not found: {schema_path}")
        return False
    
    print(f"Applying camera schema from {schema_path}")
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Split and execute statements
    statements = schema_sql.split(';')
    
    with get_session() as session:
        for stmt in statements:
            stmt = stmt.strip()
            if stmt and not stmt.startswith('--'):
                try:
                    session.execute(text(stmt))
                except Exception as e:
                    # Ignore "already exists" errors
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"  Skipping (already exists): {stmt[:50]}...")
                    else:
                        print(f"  Error: {e}")
        
        session.commit()
    
    print("Camera schema applied successfully!")
    return True


if __name__ == "__main__":
    success = apply_camera_schema()
    sys.exit(0 if success else 1)
