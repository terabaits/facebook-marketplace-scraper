"""Quick API smoke test: verify the laptop listings API returns the
normalized CPU fields (cpu_brand_normalized, cpu_model_normalized) for
every listing. Logs the first 15 listings cpu_raw -> normalized mapping.
"""
import json
import sys
from pathlib import Path

# Make SS-WEBSITE importable when running this from the repo root
sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

from app import app


def main() -> None:
    client = app.test_client()
    resp = client.get("/api/laptops?limit=20")
    data = json.loads(resp.data)
    listings = data.get("listings", [])
    print(f"Fetched {len(listings)} listings from /api/laptops")
    print()
    print(f"  {'cpu_raw':35} -> {'brand':10} {'model':20}  resolved?")
    print("  " + "-" * 80)
    for l in listings:
        raw = l.get("cpu_raw") or ""
        brand = l.get("cpu_brand_normalized")
        model = l.get("cpu_model_normalized")
        resolved = "yes" if (brand and model and model != raw) else "no"
        print(f"  {raw!r:35} -> {brand!r:10} {model!r:20}  {resolved}")


if __name__ == "__main__":
    main()
