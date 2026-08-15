"""Smoke test the model split + new column in /api/laptops."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "SS-WEBSITE"))

from app import app
import json

client = app.test_client()
r = client.get('/api/laptops?limit=10')
d = json.loads(r.data)
print(f"Total listings: {d.get('total')}")
for l in d.get('listings', []):
    model = l.get('laptop_model')
    number = l.get('laptop_model_number')
    print(f"  model={model!r:35}  number={number!r}")
