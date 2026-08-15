#!/usr/bin/env python3
"""Force fresh imports and run RAM test"""
import sys
import os
import io

# Force UTF-8
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Change to correct directory
os.chdir(r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER')
sys.path.insert(0, r'G:\Github\SS-WEB-SCRAPPER\SS-CRAWLER\src')

# CRITICAL: Clear ALL cached modules before importing anything
modules_to_remove = [k for k in list(sys.modules.keys()) if k.startswith('src')]
for mod in modules_to_remove:
    del sys.modules[mod]

# Now import fresh
from src.cli import main
from src.utils.config import AppConfig

# Load config and verify
config = AppConfig.from_yaml()
print(f"Loaded config - Database port: {config.database.port}")
print(f"Connection string: {config.database.connection_string}")
print()

# Run the test
sys.argv = ['main.py', 'test-url', 'https://www.ss.com/msg/lv/electronics/computers/completing-pc/ram/cglblb.html', '--ram']
sys.exit(main())
