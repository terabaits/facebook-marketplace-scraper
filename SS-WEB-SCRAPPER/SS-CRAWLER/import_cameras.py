"""Import camera references from All_Cameras_Codecs_Fixed.xlsx into PostgreSQL database."""
import sys
import re
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.database.connection import init_database, get_session
from src.utils.config import DatabaseConfig
from src.utils.logger import get_logger
from sqlalchemy import text

logger = get_logger("import_cameras")

try:
    import pandas as pd
except ImportError:
    print("pandas required: pip install pandas openpyxl")
    sys.exit(1)


def normalize_name(brand: str, model: str) -> str:
    """Create normalized name for search/matching."""
    name = f"{brand} {model}".lower()
    # Remove common words that don't help matching
    name = re.sub(r'\b(digital|dslr|mirrorless|camera|body)\b', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def generate_search_keywords(row: dict) -> list:
    """Generate search keywords from camera data."""
    keywords = []
    
    # Add brand
    if row.get('brand'):
        keywords.append(row['brand'].lower())
        # Add common brand aliases
        if row['brand'].lower() == 'canon':
            keywords.extend(['canon', 'eos'])
        elif row['brand'].lower() == 'sony':
            keywords.extend(['sony', 'alpha', 'a7', 'a6000'])
        elif row['brand'].lower() == 'nikon':
            keywords.extend(['nikon', 'd750', 'd850'])
    
    # Add model parts
    if row.get('model'):
        model_lower = row['model'].lower()
        keywords.append(model_lower)
        # Extract model number patterns
        model_parts = re.findall(r'[a-zA-Z]+\d+[a-zA-Z]*|\d+[a-zA-Z]+', row['model'])
        for part in model_parts:
            keywords.append(part.lower())
    
    # Add mount
    if row.get('mount'):
        keywords.append(row['mount'].lower())
    
    # Add sensor type
    if row.get('sensor'):
        keywords.append(row['sensor'].lower())
    
    # Add category
    if row.get('category'):
        keywords.append(row['category'].lower())
    
    return list(set(keywords))


def parse_year(value) -> int | None:
    """Parse year from various formats."""
    if pd.isna(value):
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_boolean(value) -> bool:
    """Parse boolean from various formats."""
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).lower() in ('yes', 'true', '1', 'y', 't', 'x')


def import_cameras(excel_path: str = None):
    """Import cameras from Excel to database."""
    
    # Find Excel file
    if excel_path is None:
        excel_path = Path(__file__).parent / "All_Cameras_Codecs_Fixed.xlsx"
    else:
        excel_path = Path(excel_path)
    
    if not excel_path.exists():
        logger.error(f"Excel file not found at {excel_path}")
        return False
    
    logger.info(f"Importing cameras from {excel_path}")
    
    # Read Excel file
    try:
        df = pd.read_excel(excel_path)
        logger.info(f"Loaded {len(df)} cameras from Excel")
    except Exception as e:
        logger.error(f"Failed to read Excel file: {e}")
        return False
    
    # Initialize database
    config = DatabaseConfig(
        host="localhost",
        port=5433,
        name="ss_market",
        user="crawler",
        password="crawler_pass"
    )
    init_database(config)
    
    imported = 0
    failed = 0
    
    with get_session() as session:
        # Clear existing camera data (DELETE instead of TRUNCATE to avoid CASCADE dropping listings)
        # First unlink any listings that reference cameras
        session.execute(text("UPDATE listings SET matched_camera_id = NULL WHERE matched_camera_id IS NOT NULL"))
        session.execute(text("DELETE FROM camera_reference"))
        session.execute(text("ALTER SEQUENCE camera_reference_id_seq RESTART WITH 1"))
        logger.info("Cleared existing camera references")
        
        for idx, row in df.iterrows():
            try:
                # Build camera data dict
                camera_data = {
                    'brand': str(row.get('Brand', '')).strip() if pd.notna(row.get('Brand')) else '',
                    'model': str(row.get('Model', '')).strip() if pd.notna(row.get('Model')) else '',
                    'model_original': str(row.get('Model_Original', '')).strip() if pd.notna(row.get('Model_Original')) else None,
                    'mount': str(row.get('Mount', '')).strip() if pd.notna(row.get('Mount')) else None,
                    'sensor': str(row.get('Sensor', '')).strip() if pd.notna(row.get('Sensor')) else None,
                    'camera_type': str(row.get('Type', '')).strip() if pd.notna(row.get('Type')) else None,
                    'category': str(row.get('Category', '')).strip() if pd.notna(row.get('Category')) else None,
                    'release_year': parse_year(row.get('Release Year')),
                    'resolution': str(row.get('Resolution', '')).strip() if pd.notna(row.get('Resolution')) else None,
                    'fps': str(row.get('FPS', '')).strip() if pd.notna(row.get('FPS')) else None,
                    'iso': str(row.get('ISO', '')).strip() if pd.notna(row.get('ISO')) else None,
                    'focus_points': str(row.get('Focus Points', '')).strip() if pd.notna(row.get('Focus Points')) else None,
                    'video_specs': str(row.get('Video', '')).strip() if pd.notna(row.get('Video')) else None,
                    'battery': str(row.get('Battery', '')).strip() if pd.notna(row.get('Battery')) else None,
                    'storage': str(row.get('Storage', '')).strip() if pd.notna(row.get('Storage')) else None,
                    'screen': str(row.get('Screen', '')).strip() if pd.notna(row.get('Screen')) else None,
                    'evf': str(row.get('EVF', '')).strip() if pd.notna(row.get('EVF')) else None,
                    'has_raw': parse_boolean(row.get('RAW')),
                    'has_clog': parse_boolean(row.get('C_Log')),
                    'has_clog2': parse_boolean(row.get('C_Log2')),
                    'has_clog3': parse_boolean(row.get('C_Log3')),
                    'has_slog': parse_boolean(row.get('S_Log')),
                    'has_slog2': parse_boolean(row.get('S_Log2')),
                    'has_slog3': parse_boolean(row.get('S_Log3')),
                    'has_4k': parse_boolean(row.get('4K')),
                    'has_8k': parse_boolean(row.get('8K')),
                    'sd_type': str(row.get('SD_Type', '')).strip() if pd.notna(row.get('SD_Type')) else None,
                }
                
                # Generate normalized name and keywords
                camera_data['normalized_name'] = normalize_name(
                    camera_data['brand'], 
                    camera_data['model']
                )
                camera_data['search_keywords'] = generate_search_keywords(camera_data)
                
                # Insert into database
                session.execute(
                    text("""
                        INSERT INTO camera_reference (
                            brand, model, model_original, mount, sensor, camera_type, category,
                            release_year, resolution, fps, iso, focus_points, video_specs,
                            battery, storage, screen, evf, has_raw, has_clog, has_clog2, has_clog3,
                            has_slog, has_slog2, has_slog3, has_4k, has_8k, sd_type,
                            search_keywords, normalized_name
                        ) VALUES (
                            :brand, :model, :model_original, :mount, :sensor, :camera_type, :category,
                            :release_year, :resolution, :fps, :iso, :focus_points, :video_specs,
                            :battery, :storage, :screen, :evf, :has_raw, :has_clog, :has_clog2, :has_clog3,
                            :has_slog, :has_slog2, :has_slog3, :has_4k, :has_8k, :sd_type,
                            :search_keywords, :normalized_name
                        )
                    """),
                    camera_data
                )
                
                imported += 1
                
                if imported % 20 == 0:
                    logger.info(f"Imported {imported} cameras...")
                    
            except Exception as e:
                logger.warning(f"Failed to import camera at row {idx}: {e}")
                failed += 1
                continue
        
        session.commit()
    
    logger.info(f"Import complete: {imported} cameras imported, {failed} failed")
    return True


if __name__ == "__main__":
    excel_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Default path
    if excel_path is None:
        excel_path = "G:\\Github\\SS-WEB-SCRAPPER\\All_Cameras_Codecs_Fixed.xlsx"
    
    success = import_cameras(excel_path)
    sys.exit(0 if success else 1)
