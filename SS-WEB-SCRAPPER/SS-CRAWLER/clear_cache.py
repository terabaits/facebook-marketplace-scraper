#!/usr/bin/env python3
"""Clear ALL Python cache including system-level."""
import sys
import os
import shutil
from pathlib import Path

cwd = Path(__file__).parent

# Clear all __pycache__ directories
for cache_dir in cwd.rglob('__pycache__'):
    if cache_dir.is_dir():
        print(f"Removing: {cache_dir}")
        shutil.rmtree(cache_dir, ignore_errors=True)

# Clear all .pyc files
for pyc_file in cwd.rglob('*.pyc'):
    print(f"Removing: {pyc_file}")
    pyc_file.unlink()

# Also clear .pyo files
for pyo_file in cwd.rglob('*.pyo'):
    print(f"Removing: {pyo_file}")
    pyo_file.unlink()

# Clear importlib cache if any
cache_files = list(cwd.rglob('*.cpython-*.pyc'))
for f in cache_files:
    print(f"Removing: {f}")
    f.unlink()

print("\n✅ All cache cleared. Now run your test command.")
print("python main.py test-url \"https://www.ss.com/msg/lv/electronics/computers/completing-pc/cases/bplhmk.html\" --psu")
