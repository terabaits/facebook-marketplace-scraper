"""Import lens references from lenses.csv into PostgreSQL database."""
import csv
import sys
import re
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import init_database, get_session
from src.utils.config import DatabaseConfig
from src.utils.logger import get_logger
from sqlalchemy import text

logger = get_logger("import_lenses")


def parse_boolean(value: str) -> bool:
    """Parse boolean from various string formats."""
    if not value:
        return False
    return value.lower() in ('yes', 'true', '1', 'y', 't')


def parse_int(value: str) -> int | None:
    """Parse integer, return None if invalid."""
    if not value:
        return None
    # Remove non-digit characters except minus
    clean = re.sub(r'[^\d-]', '', value)
    try:
        return int(clean) if clean else None
    except ValueError:
        return None


def parse_decimal(value: str) -> float | None:
    """Parse decimal value, return None if invalid."""
    if not value:
        return None
    # Remove currency symbols and whitespace
    clean = value.replace('$', '').replace('€', '').replace(',', '').strip()
    try:
        return float(clean) if clean else None
    except ValueError:
        return None


def parse_date(value: str):
    """Parse date string, return None if invalid."""
    if not value:
        return None
    # Try various formats
    import datetime
    formats = ['%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d', '%d.%m.%Y']
    for fmt in formats:
        try:
            return datetime.datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            continue
    return None


def normalize_name(lens_name: str, brand: str) -> str:
    """Create normalized name for search/matching."""
    name = f"{brand} {lens_name}".lower()
    # Remove common words that don't help matching
    name = re.sub(r'\b(ef|rf|e|f|g|dg|art|sp|ex|hsm|usm|stm|is|os|vc|usd|if|ed|as|ncs|umc)\b', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def generate_search_keywords(lens: dict) -> list:
    """Generate search keywords from lens data."""
    keywords = []
    
    # Add brand
    if lens.get('brand'):
        keywords.append(lens['brand'].lower())
    
    # Add mount
    if lens.get('mount'):
        keywords.append(lens['mount'].lower())
    
    # Extract focal length numbers
    if lens.get('focal_length_mm'):
        keywords.append(str(lens['focal_length_mm']))
    if lens.get('max_focal_length_mm'):
        keywords.append(str(lens['max_focal_length_mm']))
        keywords.append(f"{lens['focal_length_mm']}-{lens['max_focal_length_mm']}")
    
    # Add aperture
    if lens.get('max_aperture'):
        keywords.append(lens['max_aperture'])
    
    # Add lens type keywords
    if lens.get('range_type'):
        keywords.append(lens['range_type'].lower())
    
    return list(set(keywords))


def import_lenses(csv_path: str = None):
    """Import lenses from CSV to database."""
    
    # Find lenses.csv
    if csv_path is None:
        csv_path = Path(__file__).parent / "lenses.csv"
    else:
        csv_path = Path(csv_path)
    
    if not csv_path.exists():
        logger.error(f"lenses.csv not found at {csv_path}")
        return False
    
    logger.info(f"Importing lenses from {csv_path}")
    
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
        # Clear existing data (optional - comment out if you want to keep existing)
        session.execute(text("TRUNCATE TABLE lens_reference RESTART IDENTITY CASCADE"))
        logger.info("Cleared existing lens references")
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                try:
                    # Extract focal length - handle formats like "24-105"
                    focal_raw = row.get('FL (mm)', '')
                    focal_min = None
                    focal_max = None
                    if focal_raw:
                        if '-' in str(focal_raw):
                            parts = str(focal_raw).split('-')
                            focal_min = parse_int(parts[0])
                            focal_max = parse_int(parts[1]) if len(parts) > 1 else None
                        else:
                            focal_min = parse_int(focal_raw)
                    
                    # Also check separate columns
                    if not focal_max and row.get('Max FL (mm)'):
                        focal_max = parse_int(row.get('Max FL (mm)'))
                    
                    lens_data = {
                        'system': row.get('System', ''),
                        'brand': row.get('Brand', ''),
                        'range_type': row.get('Range', ''),
                        'lens_type': row.get('Type', ''),
                        'mount': row.get('Mount', ''),
                        'lens_name': row.get('Lens', ''),
                        'focal_length_mm': focal_min,
                        'max_focal_length_mm': focal_max,
                        'max_aperture': row.get('Max. Aper.', ''),
                        'filter_mm': parse_int(row.get('Filter (mm)', '')),
                        'min_focus_distance_cm': parse_int(row.get('MFD (cm)', '')),
                        'diameter_mm': parse_int(row.get('Diam. (mm)', '')),
                        'length_mm': parse_int(row.get('Length (mm)', '')),
                        'weight_g': parse_int(row.get('Weight (g)', '')),
                        'has_is': parse_boolean(row.get('IS', '')),
                        'has_wr': parse_boolean(row.get('WR', '')),
                        'elements': parse_int(row.get('Elements', '')),
                        'blades': parse_int(row.get('Blades', '')),
                        'price_new': parse_decimal(row.get('Price (new)', '')),
                        'release_date': parse_date(row.get('', '')),  # Date column not clearly named
                        'notes': row.get('Notes', '')
                    }
                    
                    # Generate normalized name and keywords
                    lens_data['normalized_name'] = normalize_name(
                        lens_data['lens_name'], 
                        lens_data['brand']
                    )
                    lens_data['search_keywords'] = generate_search_keywords(lens_data)
                    
                    # Insert into database
                    session.execute(
                        text("""
                            INSERT INTO lens_reference (
                                system, brand, range_type, lens_type, mount, lens_name,
                                focal_length_mm, max_focal_length_mm, max_aperture,
                                filter_mm, min_focus_distance_cm, diameter_mm, length_mm, weight_g,
                                has_is, has_wr, elements, blades, price_new, release_date, notes,
                                search_keywords, normalized_name
                            ) VALUES (
                                :system, :brand, :range_type, :lens_type, :mount, :lens_name,
                                :focal_length_mm, :max_focal_length_mm, :max_aperture,
                                :filter_mm, :min_focus_distance_cm, :diameter_mm, :length_mm, :weight_g,
                                :has_is, :has_wr, :elements, :blades, :price_new, :release_date, :notes,
                                :search_keywords, :normalized_name
                            )
                        """),
                        lens_data
                    )
                    
                    imported += 1
                    
                    if imported % 50 == 0:
                        logger.info(f"Imported {imported} lenses...")
                        
                except Exception as e:
                    logger.warning(f"Failed to import lens: {e}")
                    failed += 1
                    continue
        
        session.commit()
    
    logger.info(f"Import complete: {imported} lenses imported, {failed} failed")
    return True


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else None
    success = import_lenses(csv_path)
    sys.exit(0 if success else 1)
