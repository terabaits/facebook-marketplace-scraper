#!/usr/bin/env python3
"""
CPU Matching by Model Number Extraction
Matches CPUs by extracting and comparing model numbers instead of fuzzy text.
"""

import psycopg2
import re
from pathlib import Path

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def extract_intel_model(name):
    """Extract Intel model number like 14900K from various formats.
    
    Examples:
    - "Intel Core i9-14900K" → "14900K"
    - "i9-14900K" → "14900K"
    - "Core i9 14900K" → "14900K"
    - "14900K" → "14900K"
    """
    if not name:
        return None
    
    name = str(name).upper()
    
    # Pattern: iX-XXXXX or iX XXXXX or just XXXXX
    # Matches: 14900K, 14700, 13900KF, etc.
    patterns = [
        r'I\d-\s*(\d{3,5}[A-Z]*)',  # i9-14900K or i9 14900K
        r'I\d\s+(\d{3,5}[A-Z]*)',   # i9 14900K
        r'\s(\d{4,5}[A-Z]*)\s',      # standalone 14900K (4-5 digits)
        r'^(\d{4,5}[A-Z]*)$',         # just the number 14900K
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            model = match.group(1)
            # Validate: should be 4-5 digits optionally followed by letters
            if re.match(r'^\d{4,5}[A-Z]*$', model):
                return model
    
    return None


def extract_amd_model(name):
    """Extract AMD model number like 7950X or 7800X3D.
    
    Examples:
    - "AMD Ryzen 9 7950X" → "7950X"
    - "Ryzen 7 7800X3D" → "7800X3D"
    - "Ryzen 5 7600" → "7600"
    """
    if not name:
        return None
    
    name = str(name).upper()
    
    # Pattern: Ryzen X XXXX... or just XXXX...
    # AMD model numbers are typically 4 digits with optional suffix
    patterns = [
        r'RYZEN\s+\d+\s+(\d{3,4}[A-Z]*\d*)',  # Ryzen 9 7950X or Ryzen 7 7800X3D
        r'RYZEN\s+(\d{3,4}[A-Z]*\d*)',         # Ryzen 7950X
        r'\s(\d{4}[A-Z]*\d*)\s',               # standalone 7950X
        r'^(\d{4}[A-Z]*\d*)$',                  # just 7950X
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            model = match.group(1)
            # Validate: should be 4 digits with optional letters
            if re.match(r'^\d{4}[A-Z]*\d*$', model):
                return model
    
    return None


def extract_arm_model(name):
    """Extract ARM/mobile chip model (Snapdragon, MediaTek, etc.)."""
    if not name:
        return None
    
    name = str(name).upper()
    
    # Snapdragon: 888, 8 Gen 1, 865, etc.
    snapdragon = re.search(r'SNAPDRAGON\s*(\d+[A-Z]*|\d+\s+GEN\s+\d+)', name)
    if snapdragon:
        return f"SD_{snapdragon.group(1).replace(' ', '_')}"
    
    # MediaTek: MT6737, MT8781, etc.
    mediatek = re.search(r'MEDIATEK\s*(MT\d+[A-Z]*)', name)
    if mediatek:
        return mediatek.group(1)
    
    # Qualcomm: MSM8974, SA8255P, etc.
    qualcomm = re.search(r'QUALCOMM\s*(MSM\d+|SA\d+[A-Z]*|QSD\d+)', name)
    if qualcomm:
        return qualcomm.group(1)
    
    return None


def extract_base_model(model):
    """Extract base model without suffixes for variant matching.
    
    14900K → 14900
    14900KF → 14900
    7800X3D → 7800
    7950X → 7950
    """
    if not model:
        return None
    
    # Remove common suffixes
    base = re.sub(r'[KFTX]$', '', model)  # Remove K, F, T, X at end
    base = re.sub(r'X3D$', '', base)       # Remove X3D
    base = re.sub(r'G$', '', base)         # Remove G (integrated graphics)
    base = re.sub(r'P$', '', base)         # Remove P (power optimized)
    base = re.sub(r'E$', '', base)         # Remove E (embedded)
    base = re.sub(r'U$', '', base)         # Remove U (ultra low power)
    base = re.sub(r'H$', '', base)         # Remove H (high performance mobile)
    base = re.sub(r'HK$', '', base)        # Remove HK
    base = re.sub(r'HX$', '', base)        # Remove HX
    
    return base if base != model else model


def is_variant_match(model1, model2):
    """Check if two models are variants of each other.
    
    14900K and 14900KF → True (same base)
    14900K and 14700K → False (different models)
    """
    if not model1 or not model2:
        return False
    
    base1 = extract_base_model(model1)
    base2 = extract_base_model(model2)
    
    return base1 == base2


def match_cpus():
    """Match CPUs by model number extraction."""
    print("=" * 70)
    print("CPU Matching by Model Number Extraction")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clear existing matches
    cursor.execute("TRUNCATE cpu_name_matches")
    conn.commit()
    print("\nCleared existing matches")
    
    # Load CPU_REFERENCE
    cursor.execute("SELECT id, cpu_name, producer FROM cpu_reference")
    cpu_refs = cursor.fetchall()
    print(f"Loaded {len(cpu_refs)} CPUs from reference")
    
    # Extract models from reference
    ref_models = {}
    for cpu_id, cpu_name, producer in cpu_refs:
        model = None
        if 'INTEL' in producer.upper():
            model = extract_intel_model(cpu_name)
        elif 'AMD' in producer.upper():
            model = extract_amd_model(cpu_name)
        
        if model:
            ref_models[cpu_id] = {
                'name': cpu_name,
                'model': model,
                'base': extract_base_model(model),
                'producer': producer
            }
    
    print(f"Extracted model numbers from {len(ref_models)} reference CPUs")
    
    # Load benchmark data
    cursor.execute("SELECT cpu_name FROM cpu_benchmarks_r23")
    r23_data = [(row[0], extract_intel_model(row[0]) or extract_amd_model(row[0]) or extract_arm_model(row[0])) for row in cursor.fetchall()]
    r23_dict = {model: name for name, model in r23_data if model}
    
    cursor.execute("SELECT cpu_name FROM cpu_benchmarks_r26")
    r26_data = [(row[0], extract_intel_model(row[0]) or extract_amd_model(row[0]) or extract_arm_model(row[0])) for row in cursor.fetchall()]
    r26_dict = {model: name for name, model in r26_data if model}
    
    cursor.execute("SELECT cpu_name FROM cpu_benchmarks_passmark")
    pm_data = [(row[0], extract_intel_model(row[0]) or extract_amd_model(row[0]) or extract_arm_model(row[0])) for row in cursor.fetchall()]
    pm_dict = {model: name for name, model in pm_data if model}
    
    print(f"Loaded benchmark data: {len(r23_dict)} R23, {len(r26_dict)} R26, {len(pm_dict)} PassMark")
    
    # Match by model number
    matches = []
    exact_matches = 0
    variant_matches = 0
    
    for cpu_id, ref_data in ref_models.items():
        ref_model = ref_data['model']
        ref_base = ref_data['base']
        
        match_record = {
            'cpu_id': cpu_id,
            'r23': None,
            'r26': None,
            'passmark': None,
            'confidence': 0.0
        }
        
        conf_scores = []
        
        # Try exact model match first
        if ref_model in r23_dict:
            match_record['r23'] = r23_dict[ref_model]
            conf_scores.append(0.95)
            exact_matches += 1
        elif ref_base in r23_dict:
            # Variant match (e.g., 14900K matched to 14900)
            match_record['r23'] = r23_dict[ref_base]
            conf_scores.append(0.90)
            variant_matches += 1
        
        if ref_model in r26_dict:
            match_record['r26'] = r26_dict[ref_model]
            conf_scores.append(0.95)
            exact_matches += 1
        elif ref_base in r26_dict:
            match_record['r26'] = r26_dict[ref_base]
            conf_scores.append(0.90)
            variant_matches += 1
        
        if ref_model in pm_dict:
            match_record['passmark'] = pm_dict[ref_model]
            conf_scores.append(0.95)
            exact_matches += 1
        elif ref_base in pm_dict:
            match_record['passmark'] = pm_dict[ref_base]
            conf_scores.append(0.90)
            variant_matches += 1
        
        if conf_scores:
            match_record['confidence'] = sum(conf_scores) / len(conf_scores)
            matches.append(match_record)
    
    print(f"\nFound {len(matches)} matches:")
    print(f"  - Exact model matches: {exact_matches}")
    print(f"  - Variant matches (K/F/T): {variant_matches}")
    
    # Insert matches
    print("\nInserting matches...")
    batch = []
    for match in matches:
        batch.append((
            match['cpu_id'],
            match['r23'],
            match['r26'],
            match['passmark'],
            None,  # pcpartpicker
            round(match['confidence'], 2)
        ))
        
        if len(batch) >= 100:
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
    
    # Show sample matches
    print("\n" + "=" * 70)
    print("SAMPLE MATCHES")
    print("=" * 70)
    
    cursor.execute("""
        SELECT cr.cpu_name, cnm.passmark_cpu_name, cnm.r23_cpu_name, cnm.match_confidence
        FROM cpu_reference cr
        JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        WHERE cnm.match_confidence >= 0.90
        ORDER BY cnm.match_confidence DESC
        LIMIT 15
    """)
    
    for row in cursor.fetchall():
        ref, pm, r23, conf = row
        pm_str = f"PM:{pm[:25]}" if pm else ""
        r23_str = f"R23:{r23[:25]}" if r23 else ""
        print(f"✅ {ref[:35]:<35} → {pm_str or r23_str} (conf: {conf})")
    
    # Show unmatched popular CPUs
    print("\n" + "=" * 70)
    print("POPULAR CPUS WITH NO MATCH (Need Manual Review)")
    print("=" * 70)
    
    cursor.execute("""
        SELECT cr.cpu_name
        FROM cpu_reference cr
        LEFT JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        WHERE cnm.cpu_reference_id IS NULL
          AND (cr.cpu_name ~* 'i[579]-' OR cr.cpu_name ~* 'ryzen [79]')
        LIMIT 20
    """)
    
    unmatched = cursor.fetchall()
    if unmatched:
        for row in unmatched:
            print(f"❌ {row[0]}")
    else:
        print("All popular CPUs matched!")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print(f"COMPLETE: {len(matches)} CPUs matched by model number")
    print("=" * 70)


def validate_new_matches():
    """Quick validation of new matches."""
    print("\n" + "=" * 70)
    print("VALIDATING NEW MATCHES")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check for suspicious matches
    cursor.execute("""
        SELECT cr.cpu_name, cnm.passmark_cpu_name, cnm.match_confidence
        FROM cpu_reference cr
        JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        WHERE cnm.passmark_cpu_name IS NOT NULL
        LIMIT 50
    """)
    
    suspicious = 0
    for row in cursor.fetchall():
        ref, pm, conf = row
        ref_model = extract_intel_model(ref) or extract_amd_model(ref)
        pm_model = extract_intel_model(pm) or extract_amd_model(pm)
        
        if ref_model and pm_model:
            if not is_variant_match(ref_model, pm_model):
                suspicious += 1
                if suspicious <= 5:
                    print(f"⚠️  {ref[:40]} → {pm[:40]}")
                    print(f"    Model mismatch: {ref_model} vs {pm_model}")
    
    if suspicious == 0:
        print("✅ No suspicious matches found!")
    else:
        print(f"\n⚠️  Found {suspicious} potential mismatches (showed first 5)")
    
    cursor.close()
    conn.close()


if __name__ == '__main__':
    match_cpus()
    validate_new_matches()
