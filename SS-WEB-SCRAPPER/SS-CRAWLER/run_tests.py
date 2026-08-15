#!/usr/bin/env python3
"""Run tests - Meta TDD: Fast, Deterministic, Isolated."""

import subprocess
import sys
from pathlib import Path


def run_tests(fast_only=False, with_coverage=False):
    """Execute test suite."""
    cmd = ["python", "-m", "pytest", "-v", "--tb=short"]
    
    if fast_only:
        cmd.extend(["-m", "unit"])
    
    if with_coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run tests")
    parser.add_argument("--fast", action="store_true", help="Unit tests only")
    parser.add_argument("--cov", action="store_true", help="With coverage")
    args = parser.parse_args()
    
    return run_tests(fast_only=args.fast, with_coverage=args.cov)


if __name__ == "__main__":
    sys.exit(main())
