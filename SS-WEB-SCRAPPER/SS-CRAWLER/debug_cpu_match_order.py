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

# Test with token
token = "xeone52680v4"
token_norm = token.lower().replace(' ', '').replace('-', '')

print(f"Token: '{token}'")
print(f"token_norm: '{token_norm}'")
print()

# Sort by length (descending)
sorted_proc_nums = sorted(processor_numbers.items(), key=lambda x: len(x[0]), reverse=True)

# Find matches
for proc_num, cpu in sorted_proc_nums:
    if 'e5-2680' in cpu.cpu_name.lower():
        proc_num_lower = proc_num.lower().replace(' ', '').replace('-', '')
        if proc_num_lower in token_norm:
            print(f"Processor: {proc_num} (ID {cpu.id})")
            print(f"  proc_num_lower: '{proc_num_lower}'")
            
            # Simulate the v-version check
            version_match = re.search(r'v(\d+)$', token_norm)
            if version_match:
                print(f"  Token has v-version: v{version_match.group(1)}")
                token_version = version_match.group(1)
                if not proc_num_lower.endswith(f'v{token_version}'):
                    print(f"  -> SKIP: processor doesn't have v{token_version}")
                else:
                    print(f"  -> MATCH: has v{token_version}")
            else:
                print(f"  Token has no v-version")
                if re.search(r'v\d+$', proc_num_lower):
                    print(f"  -> SKIP: processor has v-version but token doesn't")
                else:
                    print(f"  -> MATCH: neither has v-version")
            print()
