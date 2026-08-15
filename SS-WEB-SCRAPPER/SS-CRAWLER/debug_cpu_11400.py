import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

import psycopg2
from src.scraper.cpu_matcher import CPUMatcher
from src.models.schemas import CPUReference

# Connect to database and load CPUs
conn = psycopg2.connect(
    host='localhost', port=5433, database='ss_market',
    user='crawler', password='crawler_pass'
)
cur = conn.cursor()

# Load CPUs
cpu_list = []
cur.execute("SELECT id, cpu_name, processor_number, socket, cores, threads FROM cpu_reference")
for row in cur.fetchall():
    cpu_list.append(CPUReference(
        id=row[0], cpu_name=row[1], processor_number=row[2],
        socket=row[3], cores=row[4], threads=row[5]
    ))

cur.close()
conn.close()

# Initialize matcher
matcher = CPUMatcher(cpu_list)

# Test text
text = "Процессор: Intel Core i5-11400F (6 ядер / 12 потоков, до 4.4 GHz)"

# Test match
result = matcher.match(text, "")

print("CPU Match Result:")
print(f"  Matched: {result.cpu.cpu_name if result.cpu else 'None'}")
print(f"  ID: {result.cpu.id if result.cpu else 'N/A'}")
print(f"  Confidence: {result.confidence}")
print(f"  Method: {result.method}")
print()

# Check processor numbers for i5-11400 variants
print("Processor numbers for i5-11400 variants:")
for cpu_id in [88, 2888, 2889, 2890]:
    cpu = matcher.id_to_cpu.get(cpu_id)
    if cpu:
        proc_num_clean = cpu.processor_number.lower().replace('-', '').replace(' ', '')
        print(f"  ID {cpu_id}: '{cpu.processor_number}' -> '{proc_num_clean}' (len {len(proc_num_clean)})")
