#!/usr/bin/env python3
"""
Apply lens schema to database and optionally import lens data.

Usage:
    python apply_lens_schema.py [--import-data]
"""
import argparse
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database.connection import init_database, get_session
from src.utils.config import DatabaseConfig
from src.utils.logger import get_logger
from sqlalchemy import text

logger = get_logger("apply_lens_schema")


def apply_schema():
    """Create lens_reference table in database."""
    config = DatabaseConfig(
        host="localhost",
        port=5433,
        name="ss_market",
        user="crawler",
        password="crawler_pass"
    )
    
    logger.info("Connecting to database...")
    init_database(config)
    
    schema_sql = """
        CREATE TABLE IF NOT EXISTS lens_reference (
            id SERIAL PRIMARY KEY,
            system VARCHAR(50) NOT NULL,
            brand VARCHAR(50) NOT NULL,
            range_type VARCHAR(50),
            lens_type VARCHAR(50),
            mount VARCHAR(50) NOT NULL,
            lens_name VARCHAR(200) NOT NULL,
            focal_length_mm INTEGER,
            max_focal_length_mm INTEGER,
            max_aperture VARCHAR(20),
            filter_mm INTEGER,
            min_focus_distance_cm INTEGER,
            diameter_mm INTEGER,
            length_mm INTEGER,
            weight_g INTEGER,
            has_is BOOLEAN DEFAULT FALSE,
            has_wr BOOLEAN DEFAULT FALSE,
            elements INTEGER,
            blades INTEGER,
            price_new DECIMAL(10,2),
            release_date DATE,
            notes TEXT,
            search_keywords TEXT[] NOT NULL DEFAULT '{}',
            normalized_name VARCHAR(200) NOT NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_lens_brand ON lens_reference(brand);
        CREATE INDEX IF NOT EXISTS idx_lens_mount ON lens_reference(mount);
        CREATE INDEX IF NOT EXISTS idx_lens_focal ON lens_reference(focal_length_mm);
        CREATE INDEX IF NOT EXISTS idx_lens_normalized ON lens_reference(normalized_name);
        CREATE INDEX IF NOT EXISTS idx_lens_name ON lens_reference(lens_name);
        CREATE INDEX IF NOT EXISTS idx_lens_keywords ON lens_reference USING GIN(search_keywords);
    """
    
    with get_session() as session:
        logger.info("Creating lens_reference table...")
        session.execute(text(schema_sql))
        session.commit()
        
        # Verify table exists
        result = session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'lens_reference'"
        )).fetchone()
        
        if result[0] > 0:
            logger.info("[OK] lens_reference table created successfully!")
            
            # Show table info
            result = session.execute(text(
                "SELECT COUNT(*) FROM lens_reference"
            )).fetchone()
            logger.info(f"  Current lens count: {result[0]}")
            
            return True
        else:
            logger.error("[FAIL] Failed to create lens_reference table")
            return False


def main():
    parser = argparse.ArgumentParser(description='Apply lens schema to database')
    parser.add_argument('--import-data', action='store_true',
                        help='Also import lens data from lenses.csv')
    args = parser.parse_args()
    
    # Apply schema
    success = apply_schema()
    
    if not success:
        sys.exit(1)
    
    # Optionally import data
    if args.import_data:
        logger.info("\nImporting lens data from lenses.csv...")
        from import_lenses import import_lenses
        import_lenses()
    else:
        logger.info("\nTo import lens data, run: python import_lenses.py")
    
    logger.info("\nDone!")
    sys.exit(0)


if __name__ == "__main__":
    main()
