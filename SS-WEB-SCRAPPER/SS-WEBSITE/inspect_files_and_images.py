import os, re, requests
from collections import Counter

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'

files = sorted(os.listdir(PSU_DIR))
nums = []
for f in files:
    m = re.match(r'(\d{6,10})_', f)
    if m:
        nums.append(m.group(1))

print('First 20 file numbers:', nums[:20])
print('Last 5 file numbers:', nums[-5:])
print('Unique numbers:', len(set(nums)), 'files:', len(files))
print('Counts:', Counter(nums).most_common(10))
