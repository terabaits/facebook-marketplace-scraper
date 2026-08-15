import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from src.database.connection import get_db_manager, init_database
from src.database.repository import CPUReferenceRepository
from src.utils.config import AppConfig
from src.utils.text import normalize_text, extract_cpu_tokens
import re

# Initialize database
config = AppConfig()
init_database(config.database)

db = get_db_manager()
with db.get_session() as session:
    cpus = CPUReferenceRepository.get_all(session)

# Build processor_numbers dict
processor_numbers = {}
for cpu in cpus:
    if cpu.processor_number:
        processor_numbers[cpu.processor_number] = cpu

# Test text from actual listing
text = """Proccesor Xeon e5-2680 v4 14 Cores 28 Treads

Video - Rx580 8gb

Ram - 32 Gb 2x16 gb Ddr4 2400 Mhz

SSD - 1x SSD 128gb / 1x SSD 500gb

Līdzi dodu HDD 1-Tb

Var dabūt nedaudz lētak ar RAM 1x 16Gb

Monitors HP 24 collas dāvana

Atrodās Salaspilī

Lat/Rus/Eng

 Procesors:

 E5-2680 v4"""

print("Extracting CPU tokens from actual text...")
tokens = extract_cpu_tokens(text)
print(f"Tokens: {tokens}")

# Simulate what cpu_matcher does
seen = set()
candidates = []

for token in tokens:
    token_norm = token.replace(' ', '').lower()
    print(f"\nToken: '{token}' -> token_norm: '{token_norm}'")
    
    # Sort by length (descending)
    sorted_proc_nums = sorted(processor_numbers.items(), key=lambda x: len(x[0]), reverse=True)
    
    for proc_num, cpu in sorted_proc_nums:
        if cpu.id in seen:
            continue
        
        proc_num_lower = proc_num.lower().replace(' ', '').replace('-', '')
        
        # Check if processor number is contained in token
        if proc_num_lower in token_norm:
            print(f"  Found proc_num '{proc_num}' in token")
            
            # Check v-version
            version_match = re.search(r'v(\d+)$', token_norm)
            if version_match:
                token_version = version_match.group(1)
                if not proc_num_lower.endswith(f'v{token_version}'):
                    print(f"    SKIP: token has v{token_version} but processor doesn't")
                    continue
            else:
                if re.search(r'v\d+$', proc_num_lower):
                    print(f"    SKIP: processor has v-version but token doesn't")
                    continue
            
            print(f"    MATCH: Adding ID {cpu.id} ({cpu.cpu_name}) to candidates")
            candidates.append((cpu, 0.95))
            seen.add(cpu.id)
            break

print(f"\nCandidates found: {len(candidates)}")
for cpu, score in candidates:
    print(f"  ID {cpu.id}: {cpu.cpu_name} (score {score})")
