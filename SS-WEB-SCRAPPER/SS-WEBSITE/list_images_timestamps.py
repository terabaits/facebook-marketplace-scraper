import os, re, datetime
PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
for f in sorted(os.listdir(PSU_DIR), key=lambda x: os.path.getmtime(os.path.join(PSU_DIR, x))):
    m = re.match(r'(\d{6,10})_(.{8})\.', f)
    if not m:
        print('?', f)
        continue
    num, h = m.groups()
    ts = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(PSU_DIR, f)))
    print(num, h, ts.strftime('%Y-%m-%d %H:%M'), f)
