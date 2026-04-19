"""Import CPUs from cpus.csv into the database."""
import sys
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER')

from src.database.connection import get_session, init_database
from src.utils.config import AppConfig
from src.utils.text import normalize_text
from sqlalchemy import text
import csv
import re


def parse_cpus_csv(filepath: str) -> list:
    """Parse CPUs from CSV file."""
    cpus = []
    
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        
        for idx, row in enumerate(reader, 1):
            try:
                producer = row.get('Producer', '').strip()
                cpu_name = row.get('CPU Name', '').strip()
                processor_number = row.get('Processor Number', '').strip()
                
                if not cpu_name or not processor_number:
                    continue
                
                # Parse cores
                cores = row.get('# of Cores', '').strip()
                cores_int = int(cores) if cores.isdigit() else None
                
                # Parse threads
                threads = row.get('# of Threads', '').strip()
                threads_int = int(threads) if threads.isdigit() else None
                
                # Parse TDP
                tdp = row.get('Processor Base Power (previously Thermal Design Power (TDP)) \n(W)', '').strip()
                tdp_int = int(tdp) if tdp.isdigit() else None
                
                # Parse base frequency
                base_freq = row.get('Processor Base Frequency (GHz)', '').strip()
                base_freq_float = None
                if base_freq:
                    try:
                        base_freq_float = float(base_freq.replace(',', '.'))
                    except ValueError:
                        pass
                
                # Parse year
                year = None
                
                # Parse cache
                cache = row.get('Cache (MB)', '').strip()
                cache_int = int(cache) if cache.isdigit() else None
                
                # Parse socket
                socket = row.get('Supported Socket', '').strip() or None
                
                # Parse integrated graphics
                igpu = row.get('Processor Graphics', '').strip()
                integrated_graphics = igpu if igpu and igpu != 'No' else None
                
                # Generate normalized name
                normalized = normalize_text(cpu_name).replace(' ', '')
                
                # Generate search keywords
                search_keywords = [normalized, normalize_text(processor_number).replace(' ', '')]
                
                # Add variant without brand
                name_no_brand = cpu_name.replace('Intel ', '').replace('AMD ', '').strip()
                search_keywords.append(normalize_text(name_no_brand).replace(' ', ''))
                
                # Extract processor number parts (e.g., "i7-14700" -> ["i7", "14700"])
                proc_parts = re.findall(r'([a-zA-Z]+)([0-9-]+)', processor_number)
                for part in proc_parts:
                    search_keywords.append(''.join(part).lower())
                
                cpus.append({
                    'id': idx,
                    'producer': producer,
                    'cpu_name': cpu_name,
                    'processor_number': processor_number,
                    'cores': cores_int,
                    'threads': threads_int,
                    'base_freq': base_freq_float,
                    'tdp_w': tdp_int,
                    'socket': socket,
                    'cache_mb': cache_int,
                    'integrated_graphics': integrated_graphics,
                    'year_released': year,
                    'normalized_name': normalized,
                    'search_keywords': list(set(search_keywords))  # Remove duplicates
                })
                
            except Exception as e:
                print(f"Error parsing row {idx}: {e}")
                continue
    
    return cpus


def import_cpus_to_db(cpus: list, session) -> tuple:
    """Import CPUs to database."""
    added = 0
    skipped = 0
    
    for cpu in cpus:
        # Check if already exists
        result = session.execute(
            text("SELECT id FROM cpu_reference WHERE processor_number = :proc_num"),
            {"proc_num": cpu['processor_number']}
        ).fetchone()
        
        if result:
            skipped += 1
            continue
        
        # Insert new CPU
        session.execute(text("""
            INSERT INTO cpu_reference (
                producer, cpu_name, processor_number, cores, threads, 
                base_freq, tdp_w, socket, cache_mb, integrated_graphics, year_released,
                normalized_name, search_keywords
            ) VALUES (
                :producer, :cpu_name, :processor_number, :cores, :threads,
                :base_freq, :tdp_w, :socket, :cache_mb, :integrated_graphics, :year_released,
                :normalized_name, :search_keywords
            )
        """), {
            "producer": cpu['producer'],
            "cpu_name": cpu['cpu_name'],
            "processor_number": cpu['processor_number'],
            "cores": cpu['cores'],
            "threads": cpu['threads'],
            "base_freq": cpu['base_freq'],
            "tdp_w": cpu['tdp_w'],
            "socket": cpu['socket'],
            "cache_mb": cpu['cache_mb'],
            "integrated_graphics": cpu['integrated_graphics'],
            "year_released": cpu['year_released'],
            "normalized_name": cpu['normalized_name'],
            "search_keywords": cpu['search_keywords']
        })
        
        added += 1
    
    return added, skipped


def main():
    """Main import function."""
    print("Importing CPUs from cpus.csv...")
    
    # Parse CSV
    cpus = parse_cpus_csv('cpus.csv')
    print(f"Found {len(cpus)} CPUs in CSV file")
    
    # Initialize database
    config = AppConfig.from_yaml()
    init_database(config.database)
    
    # Import to database
    with get_session() as session:
        added, skipped = import_cpus_to_db(cpus, session)
        session.commit()
    
    print(f"\nImport complete!")
    print(f"  Added: {added}")
    print(f"  Skipped (already exists): {skipped}")
    
    # Show total count
    with get_session() as session:
        result = session.execute(text("SELECT COUNT(*) FROM cpu_reference"))
        count = result.fetchone()[0]
        print(f"Total CPUs in database: {count}")


if __name__ == "__main__":
    main()
