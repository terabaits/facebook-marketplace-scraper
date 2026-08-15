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

# Test text
text = "Proccesor Xeon e5-2680 v4 14 Cores 28 Treads"

normalized = normalize_text(text)
print(f"Text: {text}")
print(f"Normalized: {normalized}")

# Extract tokens
tokens = extract_cpu_tokens(text)
print(f"\nCPU tokens: {tokens}")

# Check each token
for token in tokens:
    print(f"\nToken: '{token}'")
    token_norm = token.replace(' ', '').lower()
    print(f"  token_norm: '{token_norm}'")
    
    # Check for v-version
    version_match = re.search(r'v(\d+)$', token_norm)
    if version_match:
        print(f"  Has v-version: v{version_match.group(1)}")
    else:
        print(f"  No v-version found")
    
    # Check what processors match
    for cpu in cpus:
        if 'e5-2680' in cpu.cpu_name.lower():
            proc_num_lower = cpu.processor_number.lower().replace(' ', '').replace('-', '')
            if proc_num_lower in token_norm:
                print(f"  Matches processor: {cpu.processor_number} (ID {cpu.id})")
                # Check v-version logic
                if version_match:
                    token_version = version_match.group(1)
                    if not proc_num_lower.endswith(f'v{token_version}'):
                        print(f"    -> Would SKIP (processor doesn't have v{token_version})")
                    else:
                        print(f"    -> Would MATCH (has v{token_version})")
                else:
                    if re.search(r'v\d+$', proc_num_lower):
                        print(f"    -> Would SKIP (token has no version but processor does)")
                    else:
                        print(f"    -> Would MATCH (neither has version)")
