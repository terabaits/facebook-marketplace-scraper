"""Test the refresh rate extractor."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "SS-CRAWLER"))
from src.scraper.laptop_reference_resolver import _extract_refresh_rate_hz

cases = [
    ('15.6" FHD 1920x1080 144Hz', 144),
    ('60 Hz refresh, 16GB RAM', 60),
    ('No Hz here', None),
    ('1000Hz audio', None),  # 1000 is the max, but could be audio
    ('2440mAh battery', None),  # mAh has no space + 'h' mid-word
    ('144HZ uppercase', 144),
    ('120Hz 144Hz panels available', 120),  # first match
    ('Display: 60Hz', 60),
    (None, None),
    ('', None),
    ('Intel i7 @ 2.6GHz', None),  # GHz not Hz
    ('2.4 GHz wifi', None),
]
for desc, expected in cases:
    actual = _extract_refresh_rate_hz(desc)
    flag = "OK" if actual == expected else "FAIL"
    print(f"  [{flag}] {desc!r:45} -> {actual}  (expected {expected})")
