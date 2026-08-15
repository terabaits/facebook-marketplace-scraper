#!/usr/bin/env python3
"""
Fix import issues - properly import all CSV data.
"""

import psycopg2
import pandas as pd
from pathlib import Path

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}

DATA_FOLDER = r'G:\Github\SS-WEB-SCRAPPER\cpu-spec-dataset\Results'


def fix_r23_import():
    """Re-import R23 with correct columns."""
    print("=== Fixing Cinebench R23 Import ===")
    
    df = pd.read_csv(Path(DATA_FOLDER) / 'cinebench_r23_scores.csv')
    print(f"CSV has {len(df)} rows, columns: {list(df.columns)}")
    print(df.head(2))
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("TRUNCATE cpu_benchmarks_r23")
    
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO cpu_benchmarks_r23 (cpu_name, cinebench_r23_single, cinebench_r23_multi)
                VALUES (%s, %s, %s)
            """, (
                row['cpu_name'],
                int(row['cinebench_r23_single']) if pd.notna(row['cinebench_r23_single']) else None,
                int(row['cinebench_r23_multi']) if pd.notna(row['cinebench_r23_multi']) else None
            ))
        except Exception as e:
            print(f"Error on {row['cpu_name']}: {e}")
    
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM cpu_benchmarks_r23")
    count = cursor.fetchone()[0]
    print(f"Now have {count} R23 records")
    
    cursor.close()
    conn.close()


def fix_passmark_import():
    """Re-import PassMark with correct columns."""
    print("\n=== Fixing PassMark Import ===")
    
    df = pd.read_csv(Path(DATA_FOLDER) / 'benchmark-cpus.csv')
    print(f"CSV has {len(df)} rows, columns: {list(df.columns)}")
    print(df.head(2))
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("TRUNCATE cpu_benchmarks_passmark")
    
    success = 0
    for _, row in df.iterrows():
        try:
            # Parse cores/threads
            cores = None
            threads = None
            if 'Cores' in row and pd.notna(row['Cores']):
                cores_str = str(row['Cores'])
                if '/' in cores_str:
                    parts = cores_str.split('/')
                    cores = int(parts[0]) if parts[0].strip().isdigit() else None
                    threads = int(parts[1]) if len(parts) > 1 and parts[1].strip().isdigit() else None
                else:
                    cores = int(cores_str) if cores_str.isdigit() else None
            
            cursor.execute("""
                INSERT INTO cpu_benchmarks_passmark 
                (cpu_name, socket, clock_speed, turbo_speed, cores, threads, tdp, passmark_score, source_url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row['CpuName'],
                row.get('Socket'),
                row.get('ClockSpeed'),
                row.get('TurboSpeed'),
                cores,
                threads,
                row.get('TDP'),
                int(row['PassMarkScore']) if 'PassMarkScore' in row and pd.notna(row['PassMarkScore']) else None,
                row.get('SourceUrl')
            ))
            success += 1
        except Exception as e:
            pass  # Skip errors silently
    
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM cpu_benchmarks_passmark")
    count = cursor.fetchone()[0]
    print(f"Successfully imported {success} records, table now has {count}")
    
    cursor.close()
    conn.close()


if __name__ == '__main__':
    fix_r23_import()
    fix_passmark_import()
    print("\nDone! Now re-run: python import_cpu_benchmarks_fast.py")
