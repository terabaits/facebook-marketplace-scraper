"""Apply camera schema to the database - FIXED VERSION."""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.database.connection import init_database, get_session
from src.utils.config import AppConfig
from sqlalchemy import text

def apply_camera_schema():
    """Apply camera schema SQL properly."""
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    print("Applying camera schema...")
    
    with get_session() as session:
        # Check if camera_reference table exists
        result = session.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'camera_reference'
            )
        """)).scalar()
        
        if result:
            print("Camera schema already applied (camera_reference exists)")
            return True
        
        # Create table and related objects
        session.execute(text("""
            CREATE TABLE camera_reference (
                id SERIAL PRIMARY KEY,
                brand VARCHAR(100) NOT NULL,
                model VARCHAR(200) NOT NULL,
                model_original VARCHAR(200),
                mount VARCHAR(100),
                sensor VARCHAR(100),
                camera_type VARCHAR(100),
                category VARCHAR(100),
                release_year INTEGER,
                resolution VARCHAR(100),
                fps VARCHAR(50),
                iso VARCHAR(100),
                focus_points VARCHAR(50),
                video_specs TEXT,
                battery VARCHAR(50),
                storage VARCHAR(100),
                screen VARCHAR(100),
                evf VARCHAR(100),
                has_raw BOOLEAN DEFAULT FALSE,
                has_clog BOOLEAN DEFAULT FALSE,
                has_clog2 BOOLEAN DEFAULT FALSE,
                has_clog3 BOOLEAN DEFAULT FALSE,
                has_slog BOOLEAN DEFAULT FALSE,
                has_slog2 BOOLEAN DEFAULT FALSE,
                has_slog3 BOOLEAN DEFAULT FALSE,
                has_4k BOOLEAN DEFAULT FALSE,
                has_8k BOOLEAN DEFAULT FALSE,
                sd_type VARCHAR(100),
                search_keywords TEXT[] NOT NULL DEFAULT '{}',
                normalized_name VARCHAR(300) NOT NULL
            )
        """))
        
        # Create indexes
        session.execute(text("CREATE INDEX idx_camera_brand ON camera_reference(brand)"))
        session.execute(text("CREATE INDEX idx_camera_mount ON camera_reference(mount)"))
        session.execute(text("CREATE INDEX idx_camera_type ON camera_reference(camera_type)"))
        session.execute(text("CREATE INDEX idx_camera_category ON camera_reference(category)"))
        session.execute(text("CREATE INDEX idx_camera_keywords ON camera_reference USING GIN(search_keywords)"))
        
        # Add columns to listings table if not exist
        cols = session.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='listings' 
            AND column_name IN ('matched_camera_id', 'camera_confidence_score', 'camera_match_method')
        """)).fetchall()
        existing = {c[0] for c in cols}
        
        if 'matched_camera_id' not in existing:
            session.execute(text("ALTER TABLE listings ADD COLUMN matched_camera_id INTEGER REFERENCES camera_reference(id)"))
        if 'camera_confidence_score' not in existing:
            session.execute(text("ALTER TABLE listings ADD COLUMN camera_confidence_score DECIMAL(4,2)"))
        if 'camera_match_method' not in existing:
            session.execute(text("ALTER TABLE listings ADD COLUMN camera_match_method VARCHAR(50)"))
        
        # Create view
        session.execute(text("""
            CREATE OR REPLACE VIEW camera_listings_view AS
            SELECT 
                l.listing_id,
                l.title,
                l.description,
                l.price_eur,
                l.seller_location,
                l.date_posted,
                l.is_active,
                l.camera_confidence_score,
                l.camera_match_method,
                c.brand,
                c.model,
                c.model_original,
                c.mount,
                c.sensor,
                c.camera_type,
                c.category,
                c.release_year,
                c.resolution,
                c.has_4k,
                c.has_8k
            FROM listings l
            LEFT JOIN camera_reference c ON l.matched_camera_id = c.id
            WHERE l.category = 'camera'
        """))
        
        session.commit()
        print("Camera schema applied successfully!")
        return True

if __name__ == "__main__":
    success = apply_camera_schema()
    sys.exit(0 if success else 1)
