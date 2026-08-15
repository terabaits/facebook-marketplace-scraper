#!/usr/bin/env python3
"""
CPU Benchmark Data Import and Matching System
Imports benchmark data from CSV files and links to CPU_REFERENCE via fuzzy matching.
"""

import psycopg2
import pandas as pd
from psycopg2.extras import execute_values
from difflib import SequenceMatcher
import re
from pathlib import Path

# Database config
DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}

DATA_FOLDER = r'G:\Github\SS-WEB-SCRAPPER\cpu-spec-dataset\Results'


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(**DB_CONFIG)


def normalize_cpu_name(name):
    """Normalize CPU name for better matching."""
    if pd.isna(name):
        return ""
    
    name = str(name).upper().strip()
    
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name)
    
    # Standardize AMD naming
    name = re.sub(r'AMD\s+RYZEN\s+', 'RYZEN ', name)
    name = re.sub(r'RYZEN\s+5\s+', 'RYZEN 5 ', name)
    name = re.sub(r'RYZEN\s+7\s+', 'RYZEN 7 ', name)
    name = re.sub(r'RYZEN\s+9\s+', 'RYZEN 9 ', name)
    
    # Standardize Intel naming
    name = re.sub(r'INTEL\s+CORE\s+', 'CORE ', name)
    name = re.sub(r'CORE\s+I(\d)', r'I\1', name)
    
    # Remove common suffixes that vary
    name = re.sub(r'\s+PROCESSOR\s*', ' ', name)
    name = re.sub(r'\s+CPU\s*', ' ', name)
    name = re.sub(r'\s+\d+\.\d+GHZ\s*', ' ', name)
    
    # Clean up
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def similarity_score(name1, name2):
    """Calculate similarity score between two names (0-1)."""
    if not name1 or not name2:
        return 0.0
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


def import_cinebench_r23():
    """Import Cinebench R23 scores."""
    print("\n=== Importing Cinebench R23 Scores ===")
    
    csv_path = Path(DATA_FOLDER) / 'cinebench_r23_scores.csv'
    if not csv_path.exists():
        print(f"  File not found: {csv_path}")
        return 0
    
    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} records from CSV")
    
    conn = get_db_connection()
    
    imported = 0
    errors = 0
    for _, row in df.iterrows():
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO cpu_benchmarks_r23 (cpu_name, cinebench_r23_single, cinebench_r23_multi)
                VALUES (%s, %s, %s)
                ON CONFLICT (cpu_name) DO UPDATE SET
                    cinebench_r23_single = EXCLUDED.cinebench_r23_single,
                    cinebench_r23_multi = EXCLUDED.cinebench_r23_multi,
                    scraped_at = CURRENT_TIMESTAMP
            """, (row['cpu_name'], row['cinebench_r23_single'], row['cinebench_r23_multi']))
            conn.commit()
            imported += 1
        except Exception as e:
            conn.rollback()
            errors += 1
        finally:
            cursor.close()
    
    conn.close()
    
    print(f"  Imported/Updated {imported} R23 records ({errors} errors)")
    return imported


def import_cinebench_r26():
    """Import Cinebench 2026 scores."""
    print("\n=== Importing Cinebench 2026 Scores ===")
    
    csv_path = Path(DATA_FOLDER) / 'cinebench_r26_scores.csv'
    if not csv_path.exists():
        print(f"  File not found: {csv_path}")
        return 0
    
    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} records from CSV")
    
    conn = get_db_connection()
    
    imported = 0
    errors = 0
    for _, row in df.iterrows():
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO cpu_benchmarks_r26 (cpu_name, cinebench_r26_single, cinebench_r26_multi)
                VALUES (%s, %s, %s)
                ON CONFLICT (cpu_name) DO UPDATE SET
                    cinebench_r26_single = EXCLUDED.cinebench_r26_single,
                    cinebench_r26_multi = EXCLUDED.cinebench_r26_multi,
                    scraped_at = CURRENT_TIMESTAMP
            """, (row['cpu_name'], row['cinebench_r26_single'], row['cinebench_r26_multi']))
            conn.commit()
            imported += 1
        except Exception as e:
            conn.rollback()
            errors += 1
        finally:
            cursor.close()
    
    conn.close()
    
    print(f"  Imported/Updated {imported} R26 records ({errors} errors)")
    return imported


def import_passmark():
    """Import PassMark benchmark data."""
    print("\n=== Importing PassMark Benchmarks ===")
    
    csv_path = Path(DATA_FOLDER) / 'benchmark-cpus.csv'
    if not csv_path.exists():
        print(f"  File not found: {csv_path}")
        return 0
    
    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} records from CSV")
    
    conn = get_db_connection()
    
    imported = 0
    errors = 0
    for _, row in df.iterrows():
        cursor = conn.cursor()
        try:
            # Parse cores/threads
            cores = None
            threads = None
            if 'Cores' in row and pd.notna(row['Cores']):
                cores_str = str(row['Cores'])
                if '/' in cores_str:
                    parts = cores_str.split('/')
                    cores = int(parts[0].strip()) if parts[0].strip().isdigit() else None
                    threads = int(parts[1].strip()) if parts[1].strip().isdigit() else None
                else:
                    cores = int(cores_str) if cores_str.isdigit() else None
            
            cursor.execute("""
                INSERT INTO cpu_benchmarks_passmark 
                (cpu_name, socket, clock_speed, turbo_speed, cores, threads, tdp, passmark_score, source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cpu_name) DO UPDATE SET
                    socket = EXCLUDED.socket,
                    clock_speed = EXCLUDED.clock_speed,
                    turbo_speed = EXCLUDED.turbo_speed,
                    cores = EXCLUDED.cores,
                    threads = EXCLUDED.threads,
                    tdp = EXCLUDED.tdp,
                    passmark_score = EXCLUDED.passmark_score,
                    source_url = EXCLUDED.source_url,
                    scraped_at = CURRENT_TIMESTAMP
            """, (
                row['CpuName'],
                row.get('Socket'),
                row.get('ClockSpeed'),
                row.get('TurboSpeed'),
                cores,
                threads,
                row.get('TDP'),
                row.get('PassMarkScore') if 'PassMarkScore' in row else None,
                row.get('SourceUrl')
            ))
            conn.commit()
            imported += 1
        except Exception as e:
            conn.rollback()
            errors += 1
            if errors <= 5:  # Only show first 5 errors
                print(f"  Warning: Could not import {row.get('CpuName', 'unknown')[:50]}...")
        finally:
            cursor.close()
    
    conn.close()
    
    print(f"  Imported/Updated {imported} PassMark records ({errors} errors)")
    return imported


def import_pcpartpicker():
    """Import PCPartPicker prices."""
    print("\n=== Importing PCPartPicker Prices ===")
    
    csv_path = Path(DATA_FOLDER) / 'cpu_pricesV2.csv'
    if not csv_path.exists():
        print(f"  File not found: {csv_path}")
        return 0
    
    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} records from CSV")
    
    conn = get_db_connection()
    
    imported = 0
    errors = 0
    for _, row in df.iterrows():
        cursor = conn.cursor()
        try:
            # Parse price (convert USD to EUR roughly if needed, or store as-is)
            price = None
            if 'Price' in row and pd.notna(row['Price']):
                try:
                    price = float(str(row['Price']).replace('$', '').replace(',', ''))
                    # Convert USD to EUR (approximate)
                    price = round(price * 0.92, 2)
                except:
                    pass
            
            cursor.execute("""
                INSERT INTO cpu_prices_pcpartpicker 
                (name, core_count, base_clock, boost_clock, microarchitecture, 
                 integrated_graphics, smt, tdp, rating, price_eur)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    core_count = EXCLUDED.core_count,
                    base_clock = EXCLUDED.base_clock,
                    boost_clock = EXCLUDED.boost_clock,
                    microarchitecture = EXCLUDED.microarchitecture,
                    integrated_graphics = EXCLUDED.integrated_graphics,
                    smt = EXCLUDED.smt,
                    tdp = EXCLUDED.tdp,
                    rating = EXCLUDED.rating,
                    price_eur = EXCLUDED.price_eur,
                    scraped_at = CURRENT_TIMESTAMP
            """, (
                row['Name'],
                int(row['Core Count']) if pd.notna(row.get('Core Count')) else None,
                row.get('Performance Core Clock'),
                row.get('Performance Core Boost'),
                row.get('Microarchitecture'),
                row.get('Integrated Graphics'),
                row.get('SMT') == 'Yes' if 'SMT' in row else None,
                int(row['TDP']) if pd.notna(row.get('TDP')) else None,
                int(row['Rating']) if pd.notna(row.get('Rating')) else None,
                price
            ))
            conn.commit()
            imported += 1
        except Exception as e:
            conn.rollback()
            errors += 1
        finally:
            cursor.close()
    
    conn.close()
    
    print(f"  Imported/Updated {imported} PCPartPicker records ({errors} errors)")
    return imported


def perform_fuzzy_matching(min_confidence=0.6):
    """Match CPU_REFERENCE names with benchmark tables."""
    print("\n=== Performing Fuzzy Matching ===")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all CPU_REFERENCE CPUs
    cursor.execute("SELECT id, cpu_name, normalized_name FROM cpu_reference")
    cpu_ref_data = cursor.fetchall()
    print(f"  Loaded {len(cpu_ref_data)} CPUs from CPU_REFERENCE")
    
    # Get benchmark names
    cursor.execute("SELECT cpu_name FROM cpu_benchmarks_r23")
    r23_names = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT cpu_name FROM cpu_benchmarks_r26")
    r26_names = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT cpu_name FROM cpu_benchmarks_passmark")
    pm_names = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT name FROM cpu_prices_pcpartpicker")
    pp_names = [row[0] for row in cursor.fetchall()]
    
    cursor.close()
    
    matches_found = 0
    errors = 0
    
    for cpu_id, cpu_name, norm_name in cpu_ref_data:
        cursor = conn.cursor()
        try:
            ref_normalized = normalize_cpu_name(norm_name or cpu_name)
            
            best_matches = {
                'r23': None,
                'r26': None,
                'passmark': None,
                'pcpartpicker': None
            }
            
            # Find best matches for each source
            for source_name in r23_names:
                score = similarity_score(ref_normalized, normalize_cpu_name(source_name))
                if score >= min_confidence:
                    if best_matches['r23'] is None or score > best_matches['r23']['score']:
                        best_matches['r23'] = {'name': source_name, 'score': score}
            
            for source_name in r26_names:
                score = similarity_score(ref_normalized, normalize_cpu_name(source_name))
                if score >= min_confidence:
                    if best_matches['r26'] is None or score > best_matches['r26']['score']:
                        best_matches['r26'] = {'name': source_name, 'score': score}
            
            for source_name in pm_names:
                score = similarity_score(ref_normalized, normalize_cpu_name(source_name))
                if score >= min_confidence:
                    if best_matches['passmark'] is None or score > best_matches['passmark']['score']:
                        best_matches['passmark'] = {'name': source_name, 'score': score}
            
            for source_name in pp_names:
                score = similarity_score(ref_normalized, normalize_cpu_name(source_name))
                if score >= min_confidence:
                    if best_matches['pcpartpicker'] is None or score > best_matches['pcpartpicker']['score']:
                        best_matches['pcpartpicker'] = {'name': source_name, 'score': score}
            
            # Insert match record if any matches found
            if any(best_matches.values()):
                avg_confidence = sum(m['score'] for m in best_matches.values() if m) / len([m for m in best_matches.values() if m])
                
                cursor.execute("""
                    INSERT INTO cpu_name_matches 
                    (cpu_reference_id, r23_cpu_name, r26_cpu_name, passmark_cpu_name, pcpartpicker_name, match_confidence)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cpu_reference_id) DO UPDATE SET
                        r23_cpu_name = EXCLUDED.r23_cpu_name,
                        r26_cpu_name = EXCLUDED.r26_cpu_name,
                        passmark_cpu_name = EXCLUDED.passmark_cpu_name,
                        pcpartpicker_name = EXCLUDED.pcpartpicker_name,
                        match_confidence = EXCLUDED.match_confidence,
                        matched_at = CURRENT_TIMESTAMP
                """, (
                    cpu_id,
                    best_matches['r23']['name'] if best_matches['r23'] else None,
                    best_matches['r26']['name'] if best_matches['r26'] else None,
                    best_matches['passmark']['name'] if best_matches['passmark'] else None,
                    best_matches['pcpartpicker']['name'] if best_matches['pcpartpicker'] else None,
                    round(avg_confidence, 2)
                ))
                conn.commit()
                matches_found += 1
        except Exception as e:
            conn.rollback()
            errors += 1
        finally:
            cursor.close()
    
    conn.close()
    
    print(f"  Found matches for {matches_found} CPUs ({errors} errors)")
    return matches_found


def generate_analytics_report():
    """Generate analytics report on matching success."""
    print("\n=== Generating Analytics Report ===")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("\n1. Match Success Rates:")
    print("-" * 50)
    cursor.execute("SELECT * FROM cpu_match_summary")
    for row in cursor.fetchall():
        print(f"   {row[0]:<25} {row[1]:>4}/{row[2]:<4} ({row[3]:>6.2f}%)")
    
    print("\n2. CPUs with No Matches:")
    print("-" * 50)
    cursor.execute("SELECT COUNT(*) FROM cpu_unmatched_analysis")
    unmatched_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cpu_reference")
    total_count = cursor.fetchone()[0]
    print(f"   Total: {unmatched_count}/{total_count} ({unmatched_count*100/total_count:.1f}%)")
    
    cursor.execute("""
        SELECT producer, COUNT(*) 
        FROM cpu_unmatched_analysis 
        GROUP BY producer 
        ORDER BY COUNT(*) DESC
    """)
    print("   By producer:")
    for row in cursor.fetchall():
        print(f"     {row[0]:<15} {row[1]:>4}")
    
    print("\n3. Sample Unmatched CPUs:")
    print("-" * 50)
    cursor.execute("""
        SELECT cpu_name, processor_number 
        FROM cpu_unmatched_analysis 
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"   - {row[0]} ({row[1]})")
    
    print("\n4. CPUs with Multiple Data Sources:")
    print("-" * 50)
    cursor.execute("""
        SELECT data_completeness_score, COUNT(*)
        FROM cpu_complete_data
        GROUP BY data_completeness_score
        ORDER BY data_completeness_score DESC
    """)
    for row in cursor.fetchall():
        sources = row[0]
        count = row[1]
        bar = "█" * sources + "░" * (4 - sources)
        print(f"   {bar} {sources} sources: {count:>4} CPUs")
    
    print("\n5. Potential Duplicates (Multiple Matches):")
    print("-" * 50)
    cursor.execute("SELECT COUNT(*) FROM cpu_multiple_matches")
    dup_count = cursor.fetchone()[0]
    print(f"   CPUs with ambiguous matches: {dup_count}")
    
    if dup_count > 0:
        cursor.execute("SELECT cpu_name, match_count FROM cpu_multiple_matches LIMIT 5")
        print("   Examples:")
        for row in cursor.fetchall():
            print(f"     - {row[0]} ({row[1]} potential matches)")
    
    cursor.close()
    conn.close()


def export_unmatched_csv():
    """Export unmatched CPUs to CSV for manual review."""
    print("\n=== Exporting Unmatched CPUs ===")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT cr.id, cr.producer, cr.cpu_name, cr.processor_number, 
               cr.cores, cr.threads, cr.socket
        FROM cpu_reference cr
        LEFT JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        WHERE cnm.cpu_reference_id IS NULL
        ORDER BY cr.producer, cr.cpu_name
    """)
    
    rows = cursor.fetchall()
    if rows:
        df = pd.DataFrame(rows, columns=[
            'id', 'producer', 'cpu_name', 'processor_number',
            'cores', 'threads', 'socket'
        ])
        output_path = Path(DATA_FOLDER) / 'unmatched_cpus.csv'
        df.to_csv(output_path, index=False)
        print(f"  Exported {len(rows)} unmatched CPUs to {output_path}")
    else:
        print("  No unmatched CPUs found!")
    
    cursor.close()
    conn.close()


def create_tables():
    """Create benchmark tables if they don't exist."""
    print("\n=== Creating Tables ===")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Cinebench R23 table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cpu_benchmarks_r23 (
            id SERIAL PRIMARY KEY,
            cpu_name VARCHAR(255) NOT NULL UNIQUE,
            cinebench_r23_single INTEGER,
            cinebench_r23_multi INTEGER,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create Cinebench R26 table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cpu_benchmarks_r26 (
            id SERIAL PRIMARY KEY,
            cpu_name VARCHAR(255) NOT NULL UNIQUE,
            cinebench_r26_single INTEGER,
            cinebench_r26_multi INTEGER,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create PassMark table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cpu_benchmarks_passmark (
            id SERIAL PRIMARY KEY,
            cpu_name VARCHAR(255) NOT NULL UNIQUE,
            socket VARCHAR(100),
            clock_speed VARCHAR(50),
            turbo_speed VARCHAR(50),
            cores INTEGER,
            threads INTEGER,
            tdp VARCHAR(50),
            passmark_score INTEGER,
            source_url TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create PCPartPicker prices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cpu_prices_pcpartpicker (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            core_count INTEGER,
            base_clock VARCHAR(50),
            boost_clock VARCHAR(50),
            microarchitecture VARCHAR(100),
            integrated_graphics VARCHAR(100),
            smt BOOLEAN,
            tdp INTEGER,
            rating INTEGER,
            price_eur DECIMAL(10,2),
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create matches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cpu_name_matches (
            id SERIAL PRIMARY KEY,
            cpu_reference_id INTEGER REFERENCES cpu_reference(id) UNIQUE,
            r23_cpu_name VARCHAR(255),
            r26_cpu_name VARCHAR(255),
            passmark_cpu_name VARCHAR(255),
            pcpartpicker_name VARCHAR(255),
            match_confidence DECIMAL(3,2),
            matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create analytics views
    cursor.execute("""
        CREATE OR REPLACE VIEW cpu_complete_data AS
        SELECT 
            cr.id AS cpu_reference_id,
            cr.producer,
            cr.cpu_name,
            cr.processor_number,
            cr.cores,
            cr.threads,
            cr.base_freq,
            cr.socket,
            cr.tdp_w,
            r23.cinebench_r23_single,
            r23.cinebench_r23_multi,
            r26.cinebench_r26_single,
            r26.cinebench_r26_multi,
            pm.passmark_score,
            pp.price_eur AS pcpartpicker_price,
            pp.rating AS pcpartpicker_rating,
            CASE WHEN r23.id IS NOT NULL THEN TRUE ELSE FALSE END AS has_r23,
            CASE WHEN r26.id IS NOT NULL THEN TRUE ELSE FALSE END AS has_r26,
            CASE WHEN pm.id IS NOT NULL THEN TRUE ELSE FALSE END AS has_passmark,
            CASE WHEN pp.id IS NOT NULL THEN TRUE ELSE FALSE END AS has_pcpartpicker,
            (CASE WHEN r23.id IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN r26.id IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN pm.id IS NOT NULL THEN 1 ELSE 0 END +
             CASE WHEN pp.id IS NOT NULL THEN 1 ELSE 0 END) AS data_completeness_score
        FROM cpu_reference cr
        LEFT JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        LEFT JOIN cpu_benchmarks_r23 r23 ON cnm.r23_cpu_name = r23.cpu_name
        LEFT JOIN cpu_benchmarks_r26 r26 ON cnm.r26_cpu_name = r26.cpu_name  
        LEFT JOIN cpu_benchmarks_passmark pm ON cnm.passmark_cpu_name = pm.cpu_name
        LEFT JOIN cpu_prices_pcpartpicker pp ON cnm.pcpartpicker_name = pp.name
    """)
    
    cursor.execute("""
        CREATE OR REPLACE VIEW cpu_match_summary AS
        SELECT 'Cinebench R23' AS source,
            COUNT(DISTINCT cnm.cpu_reference_id) AS matched_count,
            (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
            ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / NULLIF((SELECT COUNT(*) FROM cpu_reference), 0), 2) AS match_percentage
        FROM cpu_name_matches cnm WHERE cnm.r23_cpu_name IS NOT NULL
        UNION ALL
        SELECT 'Cinebench 2026' AS source,
            COUNT(DISTINCT cnm.cpu_reference_id) AS matched_count,
            (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
            ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / NULLIF((SELECT COUNT(*) FROM cpu_reference), 0), 2) AS match_percentage
        FROM cpu_name_matches cnm WHERE cnm.r26_cpu_name IS NOT NULL
        UNION ALL
        SELECT 'PassMark' AS source,
            COUNT(DISTINCT cnm.cpu_reference_id) AS matched_count,
            (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
            ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / NULLIF((SELECT COUNT(*) FROM cpu_reference), 0), 2) AS match_percentage
        FROM cpu_name_matches cnm WHERE cnm.passmark_cpu_name IS NOT NULL
        UNION ALL
        SELECT 'PCPartPicker Prices' AS source,
            COUNT(DISTINCT cnm.cpu_reference_id) AS matched_count,
            (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
            ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / NULLIF((SELECT COUNT(*) FROM cpu_reference), 0), 2) AS match_percentage
        FROM cpu_name_matches cnm WHERE cnm.pcpartpicker_name IS NOT NULL
        UNION ALL
        SELECT 'At least one source' AS source,
            COUNT(DISTINCT cpu_reference_id) AS matched_count,
            (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
            ROUND(COUNT(DISTINCT cpu_reference_id) * 100.0 / NULLIF((SELECT COUNT(*) FROM cpu_reference), 0), 2) AS match_percentage
        FROM cpu_name_matches
    """)
    
    cursor.execute("""
        CREATE OR REPLACE VIEW cpu_unmatched_analysis AS
        SELECT 
            cr.id,
            cr.producer,
            cr.cpu_name,
            cr.processor_number,
            cr.cores,
            cr.threads,
            cr.socket,
            CASE WHEN cnm.cpu_reference_id IS NULL THEN 'No matches found' ELSE 'Partial match' END AS match_status
        FROM cpu_reference cr
        LEFT JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        WHERE cnm.cpu_reference_id IS NULL 
           OR (cnm.r23_cpu_name IS NULL AND cnm.r26_cpu_name IS NULL 
               AND cnm.passmark_cpu_name IS NULL AND cnm.pcpartpicker_name IS NULL)
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("  Tables and views created/verified")


def main():
    """Main execution."""
    print("=" * 60)
    print("CPU Benchmark Data Import and Matching System")
    print("=" * 60)
    
    # Step 0: Create tables
    create_tables()
    
    # Step 1: Import CSV data
    import_cinebench_r23()
    import_cinebench_r26()
    import_passmark()
    import_pcpartpicker()
    
    # Step 2: Perform fuzzy matching
    perform_fuzzy_matching(min_confidence=0.6)
    
    # Step 3: Generate analytics
    generate_analytics_report()
    
    # Step 4: Export unmatched
    export_unmatched_csv()
    
    print("\n" + "=" * 60)
    print("Complete! Database is ready with linked benchmark data.")
    print("=" * 60)
    print("\nYou can now query the cpu_complete_data view:")
    print("  SELECT * FROM cpu_complete_data WHERE producer = 'Intel';")
    print("  SELECT * FROM cpu_complete_data WHERE data_completeness_score = 4;")


if __name__ == '__main__':
    main()
