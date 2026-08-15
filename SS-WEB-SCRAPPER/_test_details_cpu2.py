"""Inspect what /api/listing-details/elkbl actually returns."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

from app import app


def main() -> None:
    client = app.test_client()
    resp = client.get("/api/listing-details/elkbl")
    data = json.loads(resp.data)
    # Print all top-level keys and a small preview of values
    for k, v in sorted(data.items()):
        if isinstance(v, str) and len(v) > 60:
            v = v[:60] + "..."
        print(f"  {k}: {v!r}")


if __name__ == "__main__":
    main()
