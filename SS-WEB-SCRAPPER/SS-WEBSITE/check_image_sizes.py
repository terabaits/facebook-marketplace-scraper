import os
PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
for f in sorted(os.listdir(PSU_DIR))[:5]:
    print(f, os.path.getsize(os.path.join(PSU_DIR, f)))
