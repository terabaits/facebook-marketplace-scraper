import re

text = "pardod datoru. asus prime b760ma wifi intel i5 14400f ram gskill f4 3000 c16d 32gb ssd xlr8 cs3140 nvme m. 2 1tb 7500mbs hdd seagate st2000nm0011 2tb aio cougar poseidon vistek argb 240 psu xfx xtr750 80gold gpu radeon rx 9060 xt 16gb case ft418 white procesors i5 14400f procesora frekvence ghz 4.50 pamat plate asus prime b760ma wifi video radeon rx 9060 xt operativa atmina gb 32 hdd apjoms gb 2000"

# Test patterns
patterns = [
    r'f\d+[\s-]?\d+c\d+d',
    r'f\d+[\s-]+\d+\s*c\d+d',
    r'f\d+\s+\d+\s*c\d+d',
    r'f4\s+3000\s+c16d',
]

for p in patterns:
    match = re.search(p, text)
    print(f"Pattern: {p}")
    print(f"  Match: {match}")
    print()
