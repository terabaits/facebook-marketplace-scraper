import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, 'src')

from src.utils.text import extract_cpu_tokens, normalize_text

text = "Процессор: Intel Core i5-11400F (6 ядер / 12 потоков, до 4.4 GHz)"

print(f"Text: {text}")
print(f"Normalized: {normalize_text(text)}")
print()

print("CPU tokens:")
tokens = extract_cpu_tokens(text)
for t in tokens:
    print(f"  {t}")

# Check specifically
print(f"\n'i511400f' in tokens: {'i511400f' in tokens}")
print(f"'i511400' in tokens: {'i511400' in tokens}")
