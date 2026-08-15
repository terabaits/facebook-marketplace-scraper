"""Smoke test: /laptops page renders and contains the new filter/toggle elements."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

from app import app


def main():
    client = app.test_client()
    r = client.get('/laptops')
    body = r.data.decode('utf-8')
    print(f"Page status: {r.status_code}, size: {len(body)} bytes")
    print()
    checks = [
        ("city-filter dropdown", 'id="city-filter"' in body),
        ("material-filter dropdown", 'id="material-filter"' in body),
        ("refresh-rate-filter dropdown", 'id="refresh-rate-filter"' in body),
        ("ref-toggle CSS class", '.ref-toggle.t-hdmi' in body),
        ("vendor-collapse CSS", 'cpu-vendor-section.collapsed' in body),
        ("cleanLaptopTitle -Sludinājumi", 'Sludin\u0101jumi' in body),
        ("getDisplayCpu helper (unchanged)", 'getDisplayCpu' in body),
        ("CPU vendor chevron in template", 'cpu-vendor-left' in body),
        ("toggleCpuVendor function", 'toggleCpuVendor' in body),
        ("loadCityOptions function", 'loadCityOptions' in body),
        ("toggle keydown handler", 'keydown' in body and 'ref-toggle' in body),
    ]
    for name, ok in checks:
        flag = "OK  " if ok else "FAIL"
        print(f"  [{flag}] {name}")


if __name__ == "__main__":
    main()
