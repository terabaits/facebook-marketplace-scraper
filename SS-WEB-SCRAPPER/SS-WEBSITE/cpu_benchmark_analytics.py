#!/usr/bin/env python3
"""
CPU Benchmark Analytics Dashboard
Run this to get detailed analytics on benchmark data matching.
"""

import psycopg2
from tabulate import tabulate
from datetime import datetime

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'ss_market',
    'user': 'crawler',
    'password': 'crawler_pass'
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def analyze_success_rate():
    """Analyze match success rates by source."""
    print_section("MATCH SUCCESS RATE ANALYSIS")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Overall stats
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM cpu_reference) AS total_cpus,
            (SELECT COUNT(DISTINCT cpu_reference_id) FROM cpu_name_matches) AS matched_cpus,
            (SELECT COUNT(DISTINCT cpu_reference_id) FROM cpu_name_matches WHERE r23_cpu_name IS NOT NULL) AS has_r23,
            (SELECT COUNT(DISTINCT cpu_reference_id) FROM cpu_name_matches WHERE r26_cpu_name IS NOT NULL) AS has_r26,
            (SELECT COUNT(DISTINCT cpu_reference_id) FROM cpu_name_matches WHERE passmark_cpu_name IS NOT NULL) AS has_passmark,
            (SELECT COUNT(DISTINCT cpu_reference_id) FROM cpu_name_matches WHERE pcpartpicker_name IS NOT NULL) AS has_pcpp
    """)
    row = cursor.fetchone()
    
    total = row[0]
    matched = row[1]
    
    print(f"\n📊 OVERALL STATISTICS")
    print(f"   Total CPUs in reference:     {total}")
    print(f"   CPUs with any match:         {matched} ({matched*100/total:.1f}%)")
    print(f"   CPUs unmatched:              {total - matched} ({(total-matched)*100/total:.1f}%)")
    
    print(f"\n📈 BY DATA SOURCE")
    sources = [
        ('Cinebench R23', row[2]),
        ('Cinebench 2026', row[3]),
        ('PassMark', row[4]),
        ('PCPartPicker', row[5])
    ]
    
    for name, count in sources:
        pct = count * 100 / total if total > 0 else 0
        bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
        print(f"   {name:<20} {bar} {count:>4}/{total} ({pct:>5.1f}%)")
    
    cursor.close()
    conn.close()


def analyze_completeness():
    """Analyze data completeness (how many sources per CPU)."""
    print_section("DATA COMPLETENESS ANALYSIS")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT data_completeness_score, COUNT(*) as cpu_count
        FROM cpu_complete_data
        GROUP BY data_completeness_score
        ORDER BY data_completeness_score DESC
    """)
    
    results = cursor.fetchall()
    
    print(f"\n📊 CPUs BY NUMBER OF DATA SOURCES")
    print(f"   {'Sources':<10} {'Count':<10} {'Percentage':<12} {'Visual'}")
    print(f"   {'-'*60}")
    
    total = sum(r[1] for r in results)
    for score, count in results:
        pct = count * 100 / total
        bar = '█' * score + '░' * (4 - score)
        print(f"   {score:<10} {count:<10} {pct:>6.1f}%      {bar}")
    
    cursor.execute("""
        SELECT AVG(data_completeness_score) as avg_sources
        FROM cpu_complete_data
    """)
    avg = cursor.fetchone()[0]
    print(f"\n   Average data sources per CPU: {avg:.2f}")
    
    cursor.close()
    conn.close()


def analyze_unmatched():
    """Analyze unmatched CPUs."""
    print_section("UNMATCHED CPU ANALYSIS")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Count by producer
    cursor.execute("""
        SELECT producer, COUNT(*) as cnt
        FROM cpu_unmatched_analysis
        GROUP BY producer
        ORDER BY cnt DESC
    """)
    
    print(f"\n📊 UNMATCHED CPUs BY PRODUCER")
    results = cursor.fetchall()
    table_data = []
    for producer, count in results:
        cursor.execute("""
            SELECT COUNT(*) FROM cpu_reference WHERE producer = %s
        """, (producer,))
        total = cursor.fetchone()[0]
        pct = count * 100 / total if total > 0 else 0
        table_data.append([producer, count, total, f"{pct:.1f}%"])
    
    print(tabulate(table_data, 
                   headers=['Producer', 'Unmatched', 'Total', 'Unmatched %'],
                   tablefmt='simple'))
    
    # Sample unmatched
    print(f"\n📋 SAMPLE UNMATCHED CPUs")
    cursor.execute("""
        SELECT cpu_name, processor_number, socket, cores, threads
        FROM cpu_unmatched_analysis
        LIMIT 10
    """)
    
    samples = cursor.fetchall()
    table_data = []
    for row in samples:
        table_data.append(list(row))
    
    print(tabulate(table_data,
                   headers=['CPU Name', 'Processor', 'Socket', 'Cores', 'Threads'],
                   tablefmt='simple'))
    
    cursor.close()
    conn.close()


def analyze_multiple_matches():
    """Analyze CPUs with multiple potential matches."""
    print_section("MULTIPLE MATCH ANALYSIS")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM cpu_multiple_matches")
    count = cursor.fetchone()[0]
    
    print(f"\n📊 CPUs WITH AMBIGOUS MATCHES: {count}")
    
    if count > 0:
        cursor.execute("""
            SELECT cpu_name, match_count
            FROM cpu_multiple_matches
            ORDER BY match_count DESC
            LIMIT 10
        """)
        
        print("\n📋 TOP AMBIGOUS MATCHES:")
        results = cursor.fetchall()
        for name, mcount in results:
            print(f"   {name:<50} ({mcount} potential matches)")
    else:
        print("\n✅ No CPUs with multiple matches found!")
    
    cursor.close()
    conn.close()


def analyze_by_specs():
    """Analyze match rates by CPU specifications."""
    print_section("MATCH RATE BY SPECIFICATIONS")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # By core count
    print(f"\n📊 MATCH RATE BY CORE COUNT")
    cursor.execute("""
        SELECT 
            CASE 
                WHEN cores <= 4 THEN '1-4 cores'
                WHEN cores <= 8 THEN '5-8 cores'
                WHEN cores <= 16 THEN '9-16 cores'
                ELSE '17+ cores'
            END as core_group,
            COUNT(*) as total,
            SUM(CASE WHEN cpu_reference_id IN (SELECT cpu_reference_id FROM cpu_name_matches) THEN 1 ELSE 0 END) as matched
        FROM cpu_reference cr
        LEFT JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        WHERE cores IS NOT NULL
        GROUP BY core_group
        ORDER BY MIN(cores)
    """)
    
    results = cursor.fetchall()
    table_data = []
    for group, total, matched in results:
        pct = matched * 100 / total if total > 0 else 0
        table_data.append([group, total, matched, f"{pct:.1f}%", '█' * int(pct/10)])
    
    print(tabulate(table_data,
                   headers=['Core Group', 'Total', 'Matched', 'Rate', 'Chart'],
                   tablefmt='simple'))
    
    # By producer
    print(f"\n📊 MATCH RATE BY PRODUCER")
    cursor.execute("""
        SELECT 
            producer,
            COUNT(*) as total,
            SUM(CASE WHEN cnm.cpu_reference_id IS NOT NULL THEN 1 ELSE 0 END) as matched
        FROM cpu_reference cr
        LEFT JOIN cpu_name_matches cnm ON cr.id = cnm.cpu_reference_id
        GROUP BY producer
        ORDER BY total DESC
    """)
    
    results = cursor.fetchall()
    table_data = []
    for producer, total, matched in results:
        pct = matched * 100 / total if total > 0 else 0
        table_data.append([producer, total, matched, f"{pct:.1f}%", '█' * int(pct/10)])
    
    print(tabulate(table_data,
                   headers=['Producer', 'Total', 'Matched', 'Rate', 'Chart'],
                   tablefmt='simple'))
    
    cursor.close()
    conn.close()


def show_top_benchmarks():
    """Show top CPUs by benchmark scores."""
    print_section("TOP CPUs BY BENCHMARK")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Top R23 Multi-Core
    print(f"\n🏆 TOP 10 - CINEBENCH R23 MULTI-CORE")
    cursor.execute("""
        SELECT cr.cpu_name, r23.cinebench_r23_multi
        FROM cpu_complete_data cr
        JOIN cpu_benchmarks_r23 r23 ON cr.cinebench_r23_multi = r23.cinebench_r23_multi
        WHERE r23.cinebench_r23_multi IS NOT NULL
        ORDER BY r23.cinebench_r23_multi DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    for i, (name, score) in enumerate(results, 1):
        print(f"   {i:>2}. {name:<45} {score:>8,} pts")
    
    # Top R23 Single-Core
    print(f"\n🏆 TOP 10 - CINEBENCH R23 SINGLE-CORE")
    cursor.execute("""
        SELECT cr.cpu_name, r23.cinebench_r23_single
        FROM cpu_complete_data cr
        JOIN cpu_benchmarks_r23 r23 ON cr.cinebench_r23_single = r23.cinebench_r23_single
        WHERE r23.cinebench_r23_single IS NOT NULL
        ORDER BY r23.cinebench_r23_single DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    for i, (name, score) in enumerate(results, 1):
        print(f"   {i:>2}. {name:<45} {score:>8,} pts")
    
    cursor.close()
    conn.close()


def show_value_analysis():
    """Analyze price-to-performance ratios."""
    print_section("PRICE-TO-PERFORMANCE ANALYSIS")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Best value (price per R23 point)
    print(f"\n💰 BEST VALUE - LOWEST PRICE PER R23 MULTI-CORE POINT")
    cursor.execute("""
        SELECT 
            cr.cpu_name,
            cr.pcpartpicker_price,
            cr.cinebench_r23_multi,
            ROUND(cr.pcpartpicker_price / NULLIF(cr.cinebench_r23_multi, 0) * 100, 2) as eur_per_100pts
        FROM cpu_complete_data cr
        WHERE cr.pcpartpicker_price IS NOT NULL 
          AND cr.pcpartpicker_price > 0
          AND cr.cinebench_r23_multi IS NOT NULL
          AND cr.cinebench_r23_multi > 0
        ORDER BY eur_per_100pts ASC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    if results:
        table_data = []
        for name, price, score, ratio in results:
            table_data.append([name[:40], f"€{price}", f"{score:,}", f"€{ratio:.2f}"])
        
        print(tabulate(table_data,
                       headers=['CPU', 'Price', 'R23 Multi', '€/100pts'],
                       tablefmt='simple'))
    else:
        print("   No data available (need both price and benchmark)")
    
    cursor.close()
    conn.close()


def export_report():
    """Export full report to file."""
    report_file = f"cpu_benchmark_report_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
    
    print(f"\n\nSaving report to {report_file}...")
    
    # Redirect stdout to file
    import sys
    original_stdout = sys.stdout
    
    with open(report_file, 'w', encoding='utf-8') as f:
        sys.stdout = f
        main()
    
    sys.stdout = original_stdout
    print(f"Report saved!")


def main():
    """Run all analytics."""
    print("=" * 70)
    print("  CPU BENCHMARK DATA ANALYTICS REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    try:
        analyze_success_rate()
        analyze_completeness()
        analyze_unmatched()
        analyze_multiple_matches()
        analyze_by_specs()
        show_top_benchmarks()
        show_value_analysis()
        
        print("\n" + "=" * 70)
        print("  ANALYTICS COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
    
    # Ask to save report
    print("\n")
    response = input("Save this report to file? (y/n): ").lower()
    if response == 'y':
        export_report()
