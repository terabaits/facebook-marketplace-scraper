# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

import subprocess

urls = [
    ("https://www.ss.com/msg/lv/electronics/computers/pc/pcneb.html", "pcneb - i5-6500, GTX 1060, Netac 256GB"),
    ("https://www.ss.com/msg/lv/electronics/computers/pc/lphjf.html", "lphjf - Ryzen 7 8700F, RX 6800 XT, Kingston NV2"),
    ("https://www.ss.com/msg/lv/electronics/computers/pc/pbdhn.html", "pbdhn - Ryzen 5 1600"),
    ("https://www.ss.com/msg/lv/electronics/computers/pc/dpfex.html", "dpfex - Xeon E5-2680 v4"),
]

print("=" * 70)
print("FINAL COMPONENT MATCHING TEST")
print("=" * 70)

for url, desc in urls:
    print(f"\n\n{desc}")
    print("-" * 70)
    
    cmd = f'python main.py test-url "{url}" --computers 2>$null | Select-String -Pattern "CPU:|GPU:|SSD:" -Context 0,2'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd='G:\\Github\\SS-WEB-SCRAPPER\\SS-CRAWLER')
    
    # Filter relevant lines
    lines = result.stdout.split('\n')
    for line in lines:
        if any(x in line for x in ['🖥️', '💿', '🎮']):
            print(line.strip())

print("\n\n" + "=" * 70)
print("DONE")
