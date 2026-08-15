import requests, hashlib, os, re

url = 'https://www.ss.com/msg/lv/electronics/computers/completing-pc/cases/bxbeio.html'
resp = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+\.800\.jpg', resp.text)
imgs = sorted(set(imgs))
print('imgs found:', imgs)

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
local_hashes = {}
for f in os.listdir(PSU_DIR):
    if f.lower().endswith(('.jpg','.jpeg','.png','.webp')):
        h = hashlib.md5()
        with open(os.path.join(PSU_DIR, f), 'rb') as fh:
            while True:
                chunk = fh.read(8192)
                if not chunk: break
                h.update(chunk)
        local_hashes[h.hexdigest()] = f
print('local hash count', len(local_hashes))

for img_url in imgs:
    r = requests.get(img_url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
    rh = hashlib.md5(r.content).hexdigest()
    print('remote hash', img_url, rh, 'match?', local_hashes.get(rh))
