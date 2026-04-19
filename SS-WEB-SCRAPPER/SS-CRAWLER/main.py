#!/usr/bin/env python3
"""SS-Crawler v2 - GPU/CPU scraper for ss.com"""
import sys
import io

# Force UTF-8 for Windows console
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
