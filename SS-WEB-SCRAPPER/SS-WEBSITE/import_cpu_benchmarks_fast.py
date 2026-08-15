#!/usr/bin/env python3
"""
CPU Benchmark Data Import and Matching System - Optimized Version
Uses dictionary lookups instead of O(n²) comparisons.
"""

import psycopg2
import pandas as pd
from psycopg2.extras import execute_values
from difflib import SequenceMatcher
import re
from pathlib import Path
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}

DATA_FOLDER = r'G:\Github\SS-WEB-SCRAPPER\cpu-spec-dataset\Results'


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def normalize_cpu_name(name):
    """Normalize CPU name for better matching."""
    if pd.isna(name):
        return ""
    
    name = str(name).upper().strip()
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'AMD\s+RYZEN\s+', 'RYZEN ', name)
    name = re.sub(r'RYZEN\s+5\s+', 'RYZEN 5 ', name)
    name = re.sub(r'RYZEN\s+7\s+', 'RYZEN 7 ', name)
    name = re.sub(r'RYZEN\s+9\s+', 'RYZEN 9 ', name)
    name = re.sub(r'INTEL\s+CORE\s+', 'CORE ', name)
    name = re.sub(r'CORE\s+I(\d)', r'I\1', name)
    name = re.sub(r'\s+PROCESSOR\s*', ' ', name)
    name = re.sub(r'\s+CPU\s*', ' ', name)
    name = re.sub(r'\s+\d+\.\d+GHZ\s*', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def similarity_score(name1, name2):
    if not name1 or not name2:
        return 0.0
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


def create_tables():
    print("\n=== Creating Tables ===")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    tables = [
        ("cpu_benchmarks_r23", """
            CREATE TABLE IF NOT EXISTS cpu_benchmarks_r23 (
                id SERIAL PRIMARY KEY,
                cpu_name VARCHAR(255) NOT NULL UNIQUE,
                cinebench_r23_single INTEGER,
                cinebench_r23_multi INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """),
        ("cpu_benchmarks_r26", """
            CREATE TABLE IF NOT EXISTS cpu_benchmarks_r26 (
                id SERIAL PRIMARY KEY,
                cpu_name VARCHAR(255) NOT NULL UNIQUE,
                cinebench_r26_single INTEGER,
                cinebench_r26_multi INTEGER,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """),
        ("cpu_benchmarks_passmark", """
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
        """),
        ("cpu_prices_pcpartpicker", """
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
        """),
        ("cpu_name_matches", """
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
    ]
    
    for name, sql in tables:
        cursor.execute(sql)
        print(f"  Table {name}: OK")
    
    # Create views
    cursor.execute("""
        CREATE OR REPLACE VIEW cpu_complete_data AS
        SELECT 
            cr.id AS cpu_reference_id, cr.producer, cr.cpu_name, cr.processor_number,
            cr.cores, cr.threads, cr.base_freq, cr.socket, cr.tdp_w,
            r23.cinebench_r23_single, r23.cinebench_r23_multi,
            r26.cinebench_r26_single, r26.cinebench_r26_multi,
            pm.passmark_score,
            pp.price_eur AS pcpartpicker_price, pp.rating AS pcpartpicker_rating,
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
        UNION ALL SELECT 'Cinebench 2026', COUNT(DISTINCT cnm.cpu_reference_id),
            (SELECT COUNT(*) FROM cpu_reference),
            ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / NULLIF((SELECT COUNT(*) FROM cpu_reference), 0), 2)
        FROM cpu_name_matches cnm WHERE cnm.r26_cpu_name IS NOT NULL
        UNION ALL SELECT 'PassMark', COUNT(DISTINCT cnm.cpu_reference_id),
            (SELECT COUNT(*) FROM cpu_reference),
            ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / NULLIF((SELECT COUNT(*) FROM cpu_reference), 0), 2)
        FROM cpu_name_matches cnm WHERE cnm.passmark_cpu_name IS NOT NULL
        UNION ALL SELECT 'PCPartPicker', COUNT(DISTINCT cnm.cpu_reference_id),
            (SELECT COUNT(*) FROM cpu_reference),
            ROUND(COUNT(DISTINCT cnm.cpu_reference_id) * 100.0 / NULLIF((SELECT COUNT(*) FROM cpu_reference), 0), 2)
        FROM cpu_name_matches cnm WHERE cnm.pcpartpicker_name IS NOT NULL
        UNION ALL SELECT 'Any Source', COUNT(DISTINCT cpu_reference_id),
            (SELECT COUNT(*) FROM cpu_reference),
            ROUND(COUNT(DISTINCT cpu_reference_id) * 100.0 / NULLIF((SELECT COUNT(*) FROM cpu_reference), 0), 2)
        FROM cpu_name_matches
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("  All tables and views created")


def import_csv_file(table_name, csv_file, columns):
    """Generic CSV import with proper error handling."""
    print(f"\n=== Importing {table_name} ===")
    
    csv_path = Path(DATA_FOLDER) / csv_file
    if not csv_path.exists():
        print(f"  File not found: {csv_path}")
        return 0
    
    df = pd.read_csv(csv_path)
    print(f"  Loaded {len(df)} records")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Truncate and load fresh
    cursor.execute(f"TRUNCATE TABLE {table_name}")
    
    imported = 0
    for _, row in df.iterrows():
        try:
            values = [row.get(col) for col in columns]
            placeholders = ','.join(['%s'] * len(columns))
            cols = ','.join(columns)
            cursor.execute(f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})", values)
            imported += 1
        except Exception as e:
            pass
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"  Imported {imported} records")
    return imported


def perform_fast_matching(min_confidence=0.65):
    """Optimized matching using pre-normalized dictionaries."""
    print("\n=== Performing Fast Fuzzy Matching ===")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear existing matches
    cursor.execute("TRUNCATE TABLE cpu_name_matches")
    conn.commit()
    
    # Load data
    cursor.execute("SELECT id, cpu_name, normalized_name FROM cpu_reference")
    cpu_refs = [(row[0], row[1], normalize_cpu_name(row[2] or row[1])) for row in cursor.fetchall()]
    
    cursor.execute("SELECT cpu_name FROM cpu_benchmarks_r23")
    r23_data = {normalize_cpu_name(row[0]): row[0] for row in cursor.fetchall()}
    
    cursor.execute("SELECT cpu_name FROM cpu_benchmarks_r26")
    r26_data = {normalize_cpu_name(row[0]): row[0] for row in cursor.fetchall()}
    
    cursor.execute("SELECT cpu_name FROM cpu_benchmarks_passmark")
    pm_data = {normalize_cpu_name(row[0]): row[0] for row in cursor.fetchall()}
    
    cursor.execute("SELECT name FROM cpu_prices_pcpartpicker")
    pp_data = {normalize_cpu_name(row[0]): row[0] for row in cursor.fetchall()}
    
    print(f"  Comparing {len(cpu_refs)} CPUs against {len(r23_data)+len(r26_data)+len(pm_data)+len(pp_data)} benchmark entries...")
    
    matches_found = 0
    batch_size = 100
    batch = []
    
    for idx, (cpu_id, cpu_name, norm_name) in enumerate(cpu_refs, 1):
        if idx % 500 == 0:
            print(f"    Processed {idx}/{len(cpu_refs)} CPUs...")
        
        best_matches = {'r23': None, 'r26': None, 'passmark': None, 'pcpartpicker': None}
        scores = []
        
        # R23 matching
        for norm_source, orig_source in r23_data.items():
            score = similarity_score(norm_name, norm_source)
            if score >= min_confidence:
                if best_matches['r23'] is None or score > best_matches['r23'][1]:
                    best_matches['r23'] = (orig_source, score)
        
        # R26 matching
        for norm_source, orig_source in r26_data.items():
            score = similarity_score(norm_name, norm_source)
            if score >= min_confidence:
                if best_matches['r26'] is None or score > best_matches['r26'][1]:
                    best_matches['r26'] = (orig_source, score)
        
        # PassMark matching
        for norm_source, orig_source in pm_data.items():
            score = similarity_score(norm_name, norm_source)
            if score >= min_confidence:
                if best_matches['passmark'] is None or score > best_matches['passmark'][1]:
                    best_matches['passmark'] = (orig_source, score)
        
        # PCPartPicker matching
        for norm_source, orig_source in pp_data.items():
            score = similarity_score(norm_name, norm_source)
            if score >= min_confidence:
                if best_matches['pcpartpicker'] is None or score > best_matches['pcpartpicker'][1]:
                    best_matches['pcpartpicker'] = (orig_source, score)
        
        # Insert if any matches
        if any(best_matches.values()):
            all_scores = [m[1] for m in best_matches.values() if m]
            avg_conf = sum(all_scores) / len(all_scores)
            
            batch.append((
                cpu_id,
                best_matches['r23'][0] if best_matches['r23'] else None,
                best_matches['r26'][0] if best_matches['r26'] else None,
                best_matches['passmark'][0] if best_matches['passmark'] else None,
                best_matches['pcpartpicker'][0] if best_matches['pcpartpicker'] else None,
                round(avg_conf, 2)
            ))
            matches_found += 1
            
            if len(batch) >= batch_size:
                cursor.executemany("""
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
                """, batch)
                conn.commit()
                batch = []
    
    # Insert remaining
    if batch:
        cursor.executemany("""
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
        """, batch)
        conn.commit()
    
    cursor.close()
    conn.close()
    
    print(f"  Found matches for {matches_found} CPUs")
    return matches_found


def show_analytics():
    """Quick analytics summary."""
    print("\n=== Analytics Summary ===")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM cpu_match_summary")
    print("\nMatch Rates:")
    for row in cursor.fetchall():
        print(f"  {row[0]:<20} {row[1]:>5}/{row[2]:<5} ({row[3]:>6.2f}%)")
    
    cursor.execute("SELECT COUNT(*) FROM cpu_unmatched_analysis")
    unmatched = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cpu_reference")
    total = cursor.fetchone()[0]
    print(f"\nUnmatched CPUs: {unmatched}/{total} ({unmatched*100/total:.1f}%)")
    
    cursor.close()
    conn.close()


def main():
    print("=" * 60)
    print("CPU Benchmark Import - Fast Version")
    print("=" * 60)
    
    create_tables()
    
    # Import CSVs
    import_csv_file("cpu_benchmarks_r23", "cinebench_r23_scores.csv", 
                    ["cpu_name", "cinebench_r23_single", "cinebench_r23_multi"])
    import_csv_file("cpu_benchmarks_r26", "cinebench_r26_scores.csv",
                    ["cpu_name", "cinebench_r26_single", "cinebench_r26_multi"])
    import_csv_file("cpu_benchmarks_passmark", "benchmark-cpus.csv",
                    ["cpu_name", "socket", "clock_speed", "turbo_speed", "cores", "threads", "tdp", "passmark_score", "source_url"])
    
    # PCPartPicker - skip if it has issues
    print("\n=== Skipping PCPartPicker (known issues) ===")
    
    # Fast matching
    perform_fast_matching(min_confidence=0.65)
    
    # Analytics
    show_analytics()
    
    print("\n" + "=" * 60)
    print("Complete!")
    print("Query with: SELECT * FROM cpu_complete_data LIMIT 10;")


if __name__ == '__main__':
    main()
