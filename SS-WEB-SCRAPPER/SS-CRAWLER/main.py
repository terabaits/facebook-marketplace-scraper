#!/usr/bin/env python3
"""SS-Crawler v2 - GPU/CPU/RAM scraper for ss.com"""
import sys

# Clear any cached modules to ensure fresh imports
modules_to_clear = [k for k in sys.modules.keys() if k.startswith('src')]
for mod in modules_to_clear:
    del sys.modules[mod]

from src.cli import main

if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
