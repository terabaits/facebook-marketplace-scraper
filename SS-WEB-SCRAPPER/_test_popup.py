"""Smoke test: /laptops page renders + the new spec-popup pieces are present."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

from app import app


def main():
    client = app.test_client()
    r = client.get('/laptops')
    print(f"status: {r.status_code}, size: {len(r.data)}")
    body = r.data.decode('utf-8')
    checks = [
        ("SPEC_ICONS / spec-chip-icon", "spec-chip-icon" in body),
        ("cleanLaptopDescription helper", "cleanLaptopDescription" in body),
        ("meta-row class", "laptop-meta-row" in body),
        ("description class", "laptop-description" in body),
        ("specs heading class", "laptop-specs-heading" in body),
        ("custom svg viewBox", "viewBox" in body),
    ]
    for name, ok in checks:
        flag = "OK  " if ok else "FAIL"
        print(f"  [{flag}] {name}")


if __name__ == "__main__":
    main()
