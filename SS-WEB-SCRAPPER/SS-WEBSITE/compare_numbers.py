import os, re

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
files = sorted(f for f in os.listdir(PSU_DIR) if f.lower().endswith(('.jpg','.jpeg','.png','.webp')))
file_nums = set()
for f in files:
    m = re.match(r'(\d{6,10})_', f)
    if m:
        file_nums.add(m.group(1))

# sample numbers from SS pages: 73512413, 75336357, 75331066, 75274261, 52039335, 74685910
sample_nums = ['73512413','75336357','75331066','75274261','52039335','74685910']
print('file nums count', len(file_nums))
print('sample in files?')
for n in sample_nums:
    print(n, 'YES' if n in file_nums else 'NO')

# show range
s = sorted(file_nums)
print('min', min(s), 'max', max(s))
print('first 20', s[:20])
print('last 20', s[-20:])
