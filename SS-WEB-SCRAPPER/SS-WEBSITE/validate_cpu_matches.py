#!/usr/bin/env python3
"""
Validate CPU Benchmark Match Quality
Checks for suspicious matches and potential false positives.
"""

import psycopg2
import re
from difflib import SequenceMatcher

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def normalize_for_compare(name):
    """Normalize name for comparison."""
    if not name:
        return ""
    name = str(name).upper()
    # Remove common words
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'INTEL\s+CORE\s+', '', name)
    name = re.sub(r'AMD\s+', '', name)
    name = re.sub(r'RYZEN\s+', '', name)
    name = re.sub(r'\s+@\s+\d+\.\d+.*$', '', name)  # Remove speed suffix
    return name.strip()


def extract_model_number(name):
    """Extract model number like i9-14900K or 7800X3D."""
    patterns = [
        r'I\d+-(\d{3,5}[A-Z]*)',  # Intel: i9-14900K
        r'RYZEN\s+\d+\s+(\d{3,4}[A-Z]*)',  # AMD: Ryzen 7 7800X3D
        r'\s(\d{3,4}[A-Z]*)\s',  # Generic model number
    ]
    for pattern in patterns:
        match = re.search(pattern, str(name).upper())
        if match:
            return match.group(1)
    return None


def check_match_quality():
    """Check for suspicious matches."""
    print("=" * 70)
    print("CPU MATCH QUALITY VALIDATION")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all matches
    cursor.execute("""
        SELECT 
            cr.id,
            cr.cpu_name AS ref_name,
            cr.producer,
            cnm.r23_cpu_name,
            cnm.r26_cpu_name,
            cnm.passmark_cpu_name,
            cnm.match_confidence
        FROM cpu_reference cr
        JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        LIMIT 200
    """)
    
    matches = cursor.fetchall()
    
    # Quality checks
    suspicious = []
    good_examples = []
    
    for row in matches:
        ref_id, ref_name, producer, r23, r26, pm, conf = row
        
        # Check each match
        for source_name, source_type in [(r23, 'R23'), (r26, 'R26'), (pm, 'PassMark')]:
            if not source_name:
                continue
                
            ref_norm = normalize_for_compare(ref_name)
            src_norm = normalize_for_compare(source_name)
            
            # Extract model numbers
            ref_model = extract_model_number(ref_name)
            src_model = extract_model_number(source_name)
            
            # Calculate similarity
            similarity = SequenceMatcher(None, ref_norm, src_norm).ratio()
            
            # Flag suspicious if model numbers differ significantly
            is_suspicious = False
            reasons = []
            
            if ref_model and src_model and ref_model != src_model:
                # Check if they're at least similar (e.g., 14900K vs 14900)
                if not (ref_model in src_model or src_model in ref_model):
                    is_suspicious = True
                    reasons.append(f"Model mismatch: {ref_model} vs {src_model}")
            
            if similarity < 0.5:
                is_suspicious = True
                reasons.append(f"Low similarity: {similarity:.2f}")
            
            # AMD vs Intel mismatch
            ref_is_intel = 'INTEL' in ref_name.upper() or 'CORE' in ref_name.upper()
            src_is_intel = 'INTEL' in source_name.upper() or 'CORE' in source_name.upper()
            ref_is_amd = 'AMD' in ref_name.upper() or 'RYZEN' in ref_name.upper()
            src_is_amd = 'AMD' in source_name.upper() or 'RYZEN' in source_name.upper()
            
            if (ref_is_intel and src_is_amd) or (ref_is_amd and src_is_intel):
                is_suspicious = True
                reasons.append("Vendor mismatch (Intel vs AMD)")
            
            if is_suspicious:
                suspicious.append({
                    'ref': ref_name,
                    'source': source_name,
                    'type': source_type,
                    'similarity': similarity,
                    'confidence': conf,
                    'reasons': reasons
                })
            elif len(good_examples) < 10:
                good_examples.append({
                    'ref': ref_name,
                    'source': source_name,
                    'type': source_type,
                    'similarity': similarity
                })
    
    cursor.close()
    conn.close()
    
    # Report
    print(f"\n📊 SAMPLES CHECKED: {len(matches)}")
    print(f"🚨 SUSPICIOUS MATCHES: {len(suspicious)}")
    
    if suspicious:
        print("\n" + "=" * 70)
        print("SUSPICIOUS MATCHES (Potential False Positives):")
        print("=" * 70)
        for item in suspicious[:15]:  # Show first 15
            print(f"\n❌ Reference: {item['ref'][:50]}")
            print(f"   Matched:  {item['source'][:50]} [{item['type']}]")
            print(f"   Similarity: {item['similarity']:.2f} | Confidence: {item['confidence']}")
            print(f"   Issues: {', '.join(item['reasons'])}")
    
    print("\n" + "=" * 70)
    print("GOOD MATCH EXAMPLES (High Confidence):")
    print("=" * 70)
    for item in good_examples:
        print(f"\n✅ Reference: {item['ref'][:50]}")
        print(f"   Matched:  {item['source'][:50]} [{item['type']}]")
        print(f"   Similarity: {item['similarity']:.2f}")
    
    return len(suspicious)


def show_sample_comparisons():
    """Show side-by-side comparisons."""
    print("\n" + "=" * 70)
    print("SAMPLE CPU MATCH COMPARISONS")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cr.cpu_name AS ref_name,
            cnm.passmark_cpu_name,
            cnm.r23_cpu_name,
            cnm.match_confidence
        FROM cpu_reference cr
        JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        WHERE cnm.passmark_cpu_name IS NOT NULL
        ORDER BY cnm.match_confidence DESC
        LIMIT 20
    """)
    
    print(f"\n{'CPU_REFERENCE':<35} | {'PASSMARK MATCH':<35} | {'CONF':<6}")
    print("-" * 80)
    
    for row in cursor.fetchall():
        ref, pm, r23, conf = row
        print(f"{str(ref)[:35]:<35} | {str(pm)[:35]:<35} | {conf or 0:.2f}")
    
    cursor.close()
    conn.close()


def find_exact_matches():
    """Find CPUs that match exactly or very closely."""
    print("\n" + "=" * 70)
    print("EXACT/NEAR-EXACT MATCHES (Best Quality)")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            cr.cpu_name,
            cnm.passmark_cpu_name,
            cnm.match_confidence
        FROM cpu_reference cr
        JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        WHERE cnm.match_confidence >= 0.80
        ORDER BY cnm.match_confidence DESC
        LIMIT 15
    """)
    
    for row in cursor.fetchall():
        print(f"\n🎯 {row[0][:40]}")
        print(f"   → {row[1][:40]} (confidence: {row[2]})")
    
    cursor.close()
    conn.close()


def check_unmatched_popular():
    """Check popular CPUs that have no matches."""
    print("\n" + "=" * 70)
    print("POPULAR CPUS WITH NO BENCHMARK MATCHES")
    print("=" * 70)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT cr.cpu_name, cr.producer
        FROM cpu_reference cr
        LEFT JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        WHERE cnm.cpu_reference_id IS NULL
          AND (cr.cpu_name LIKE '%i9%' OR cr.cpu_name LIKE '%i7%' 
               OR cr.cpu_name LIKE '%Ryzen 9%' OR cr.cpu_name LIKE '%Ryzen 7%')
        LIMIT 20
    """)
    
    results = cursor.fetchall()
    if results:
        for name, producer in results:
            print(f"  ❌ {producer} {name}")
    else:
        print("  All popular CPUs have matches!")
    
    cursor.close()
    conn.close()


def main():
    """Run all validations."""
    suspicious_count = check_match_quality()
    show_sample_comparisons()
    find_exact_matches()
    check_unmatched_popular()
    
    print("\n" + "=" * 70)
    if suspicious_count == 0:
        print("✅ VALIDATION PASSED: No suspicious matches detected!")
    else:
        print(f"⚠️  VALIDATION WARNING: {suspicious_count} suspicious matches found")
        print("   Review the matches above and consider adjusting the threshold")
    print("=" * 70)


if __name__ == '__main__':
    main()
