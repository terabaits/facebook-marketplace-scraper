#!/usr/bin/env python3
"""
Database migration script for listing versioning.

This script adds the version_number column and updates constraints
for all listing tables to support reused listing IDs.

Run: python migrate_listing_versioning.py
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import text, inspect, create_engine
from src.database.connection import init_database, get_session
from src.utils.logger import get_logger

logger = get_logger("migration")


# Global engine reference
_engine = None

def get_engine():
    """Get the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        from src.database.connection import get_db_manager
        manager = get_db_manager()
        _engine = manager._engine
    return _engine


def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    engine = get_engine()
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def check_constraint_exists(table_name: str, constraint_name: str) -> bool:
    """Check if a constraint exists on a table."""
    engine = get_engine()
    inspector = inspect(engine)
    constraints = inspector.get_unique_constraints(table_name)
    return any(c['name'] == constraint_name for c in constraints)


def migrate_table(session, table_name: str, id_column: str = "listing_id"):
    """Migrate a single table to support versioning."""
    logger.info(f"\n📋 Migrating table: {table_name}")
    
    engine = get_engine()
    inspector = inspect(engine)
    
    # Step 1: Add version_number column if not exists
    if not check_column_exists(table_name, "version_number"):
        logger.info(f"  ➕ Adding version_number column...")
        session.execute(text(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN version_number INTEGER DEFAULT 1
        """))
        logger.info(f"  ✅ Added version_number column")
    else:
        logger.info(f"  ✓ version_number column already exists")
    
    # Step 2: Set default value for existing rows
    logger.info(f"  📝 Setting version_number=1 for existing rows...")
    try:
        result = session.execute(text(f"""
            UPDATE {table_name} 
            SET version_number = 1 
            WHERE version_number IS NULL
        """))
        session.commit()  # Commit the update immediately
        if result.rowcount > 0:
            logger.info(f"  📝 Set version_number=1 for {result.rowcount} existing rows")
        else:
            logger.info(f"  ✓ No rows needed updating")
    except Exception as e:
        logger.warning(f"  ⚠️ Could not update rows: {e}")
    
    # Step 3: Make column NOT NULL after setting defaults
    logger.info(f"  🔒 Setting version_number to NOT NULL...")
    try:
        session.execute(text(f"""
            ALTER TABLE {table_name} 
            ALTER COLUMN version_number SET NOT NULL
        """))
        logger.info(f"  ✅ Set version_number to NOT NULL")
    except Exception as e:
        logger.warning(f"  ⚠️ Could not set NOT NULL: {e}")
        logger.info(f"  ℹ️  You may need to run: ALTER TABLE {table_name} ALTER COLUMN version_number SET NOT NULL")
    
    # Step 4: Add content_fingerprint column if not exists
    if not check_column_exists(table_name, "content_fingerprint"):
        logger.info(f"  ➕ Adding content_fingerprint column...")
        session.execute(text(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN content_fingerprint VARCHAR(64)
        """))
        logger.info(f"  ✅ Added content_fingerprint column")
    else:
        logger.info(f"  ✓ content_fingerprint column already exists")
    
    # Step 5: Drop old unique constraint if exists
    inspector = inspect(get_engine())
    unique_constraints = inspector.get_unique_constraints(table_name)
    
    # Check for various possible constraint names
    old_constraint_names = [
        f"{table_name}_{id_column}_key",
        f"{table_name}_pkey",
        f"idx_{table_name}_{id_column}"
    ]
    
    for constraint in unique_constraints:
        if constraint['name'] in old_constraint_names or (
            len(constraint['column_names']) == 1 and 
            constraint['column_names'][0] == id_column
        ):
            logger.info(f"  🗑️ Dropping old unique constraint: {constraint['name']}")
            try:
                session.execute(text(f"""
                    ALTER TABLE {table_name} 
                    DROP CONSTRAINT IF EXISTS {constraint['name']}
                """))
                logger.info(f"  ✅ Dropped old constraint")
            except Exception as e:
                logger.warning(f"  ⚠️ Could not drop constraint (may not exist): {e}")
    
    # Step 6: Create new composite unique constraint
    new_constraint_name = f"{table_name}_{id_column}_version_unique"
    logger.info(f"  ➕ Adding new unique constraint: {new_constraint_name}")
    try:
        session.execute(text(f"""
            ALTER TABLE {table_name} 
            ADD CONSTRAINT {new_constraint_name} 
            UNIQUE ({id_column}, version_number)
        """))
        logger.info(f"  ✅ Added new unique constraint")
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info(f"  ✓ Constraint already exists")
        else:
            raise
    
    # Step 7: Create indexes for performance
    index_name = f"idx_{table_name}_id_version"
    try:
        session.execute(text(f"""
            CREATE INDEX IF NOT EXISTS {index_name} 
            ON {table_name}({id_column}, version_number)
        """))
        logger.info(f"  ✅ Created index: {index_name}")
    except Exception as e:
        logger.warning(f"  ⚠️ Could not create index: {e}")
    
    # Step 8: Create fingerprint index
    fingerprint_index = f"idx_{table_name}_fingerprint"
    try:
        session.execute(text(f"""
            CREATE INDEX IF NOT EXISTS {fingerprint_index} 
            ON {table_name}(content_fingerprint)
        """))
        logger.info(f"  ✅ Created index: {fingerprint_index}")
    except Exception as e:
        logger.warning(f"  ⚠️ Could not create fingerprint index: {e}")
    
    logger.info(f"  ✨ Migration complete for {table_name}")


def create_version_tables(session):
    """Create version history tables if they don't exist."""
    logger.info("\n📋 Creating version history tables...")
    
    # Main listing_versions table
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS listing_versions (
            id SERIAL PRIMARY KEY,
            listing_id VARCHAR(50) NOT NULL,
            version_number INTEGER NOT NULL,
            title VARCHAR(500),
            description TEXT,
            price_eur DECIMAL(10,2),
            seller_location VARCHAR(200),
            matched_gpu_id INTEGER,
            matched_cpu_id INTEGER,
            matched_ssd_id INTEGER,
            matched_ram_id INTEGER,
            matched_case_id INTEGER,
            matched_psu_id INTEGER,
            confidence_score DECIMAL(4,2),
            cpu_confidence_score DECIMAL(4,2),
            ssd_confidence_score DECIMAL(4,2),
            ram_confidence_score DECIMAL(4,2),
            case_confidence_score DECIMAL(4,2),
            psu_confidence_score DECIMAL(4,2),
            content_hash VARCHAR(64),
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(listing_id, version_number)
        )
    """))
    logger.info("  ✅ Created/verified listing_versions table")
    
    # Index for listing_versions
    session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_listing_versions_lookup 
        ON listing_versions(listing_id, version_number)
    """))
    
    # Computer listing versions table
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS computer_listing_versions (
            id SERIAL PRIMARY KEY,
            listing_id VARCHAR(50) NOT NULL,
            version_number INTEGER NOT NULL,
            title VARCHAR(500),
            description TEXT,
            price_eur DECIMAL(10,2),
            seller_location VARCHAR(200),
            matched_cpu_id INTEGER,
            matched_gpu_id INTEGER,
            matched_ram_id INTEGER,
            matched_ssd_id INTEGER,
            matched_ssd2_id INTEGER,
            matched_ssd3_id INTEGER,
            matched_psu_id INTEGER,
            matched_case_id INTEGER,
            cpu_confidence DECIMAL(4,2),
            gpu_confidence DECIMAL(4,2),
            ram_confidence DECIMAL(4,2),
            ssd_confidence DECIMAL(4,2),
            ssd2_confidence DECIMAL(4,2),
            ssd3_confidence DECIMAL(4,2),
            psu_confidence DECIMAL(4,2),
            case_confidence DECIMAL(4,2),
            content_hash VARCHAR(64),
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(listing_id, version_number)
        )
    """))
    logger.info("  ✅ Created/verified computer_listing_versions table")
    
    # Index for computer_listing_versions
    session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_computer_listing_versions_lookup 
        ON computer_listing_versions(listing_id, version_number)
    """))
    
    # Console listing versions table
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS console_listing_versions (
            id SERIAL PRIMARY KEY,
            listing_id VARCHAR(50) NOT NULL,
            version_number INTEGER NOT NULL,
            title VARCHAR(500),
            description TEXT,
            price_eur DECIMAL(10,2),
            seller_location VARCHAR(200),
            matched_console_id INTEGER,
            matched_variant_id INTEGER,
            matched_edition_id INTEGER,
            console_confidence_score DECIMAL(4,2),
            variant_confidence_score DECIMAL(4,2),
            edition_confidence_score DECIMAL(4,2),
            content_hash VARCHAR(64),
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(listing_id, version_number)
        )
    """))
    logger.info("  ✅ Created/verified console_listing_versions table")
    
    # Index for console_listing_versions
    session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_console_listing_versions_lookup 
        ON console_listing_versions(listing_id, version_number)
    """))
    
    logger.info("  ✨ Version history tables ready")


def verify_migration(session):
    """Verify the migration was successful."""
    logger.info("\n🔍 Verifying migration...")
    
    engine = get_engine()
    inspector = inspect(engine)
    tables = ["listings", "computer_listings", "console_listings"]
    all_good = True
    
    for table in tables:
        columns = [col['name'] for col in inspector.get_columns(table)]
        constraints = inspector.get_unique_constraints(table)
        
        # Check version_number column
        has_version = "version_number" in columns
        has_fingerprint = "content_fingerprint" in columns
        
        # Check composite unique constraint
        has_composite = any(
            'version_number' in c['column_names'] and 'listing_id' in c['column_names']
            for c in constraints
        )
        
        status = "✅" if (has_version and has_fingerprint and has_composite) else "❌"
        logger.info(f"  {status} {table}: version={has_version}, fingerprint={has_fingerprint}, composite_unique={has_composite}")
        
        if not (has_version and has_fingerprint and has_composite):
            all_good = False
    
    return all_good


def main():
    """Run the migration."""
    print("=" * 60)
    print("🗄️  Listing Versioning Database Migration")
    print("=" * 60)
    print()
    print("This will add versioning support to handle reused ss.com listing IDs.")
    print("Example: gexxm -> gexxm_v2 when ID is reused for different content")
    print()
    
    confirm = input("Proceed with migration? [y/N]: ")
    if confirm.lower() not in ('y', 'yes'):
        print("❌ Migration cancelled")
        return
    
    print()
    logger.info("🚀 Starting migration...")
    
    try:
        # Initialize database connection
        from src.utils.config import AppConfig
        config = AppConfig.from_yaml(Path(__file__).parent / "config.yaml")
        init_database(config.database)
        
        with get_session() as session:
            # Migrate each table
            migrate_table(session, "listings")
            migrate_table(session, "computer_listings")
            migrate_table(session, "console_listings")
            
            # Create version history tables
            create_version_tables(session)
            
            # Commit all changes
            session.commit()
            
            # Verify
            if verify_migration(session):
                logger.info("\n" + "=" * 60)
                logger.info("✅ Migration completed successfully!")
                logger.info("=" * 60)
                logger.info("\nYour database now supports listing versioning.")
                logger.info("Run scrapers normally - versioning is automatic.")
            else:
                logger.error("\n❌ Migration verification failed!")
                sys.exit(1)
                
    except Exception as e:
        logger.error(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
