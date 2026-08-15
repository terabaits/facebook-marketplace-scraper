import os, requests, re, hashlib

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
url = 'https://www.ss.com/msg/lv/electronics/computers/completing-pc/cases/bxbeio.html'
text = requests.get(url, timeout=25, headers={'User-Agent':'Mozilla/5.0'}).text
imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+\.800\.jpg', text)
print('remote size:', len(requests.get(imgs[0], timeout=25, headers={'User-Agent':'Mozilla/5.0'}).content))

for f in os.listdir(PSU_DIR):
    if os.path.getsize(os.path.join(PSU_DIR, f)) == 114003:
        print('local file with same size:', f)
