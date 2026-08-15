import os, requests, re

PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
url = 'https://www.ss.com/msg/lv/electronics/computers/completing-pc/cases/bxbeio.html'
resp = requests.get(url, timeout=25, headers={'User-Agent': 'Mozilla/5.0'})
text = resp.text
imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+\.800\.jpg', text)
print('imgs', imgs)

# Also look for the .t.jpg and full size
all_imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+', text)
print('all_imgs', all_imgs)

# Download the remote 800.jpg and compare to each local file byte-by-byte
remote = requests.get(imgs[0], timeout=25, headers={'User-Agent': 'Mozilla/5.0'}).content
print('remote len', len(remote))

local_files = [f for f in os.listdir(PSU_DIR) if f.lower().endswith(('.jpg','.jpeg','.png','.webp'))]
for f in local_files:
    path = os.path.join(PSU_DIR, f)
    with open(path, 'rb') as fh:
        local = fh.read()
    if local == remote:
        print('EXACT MATCH', f, len(local))
    elif len(local) == len(remote):
        print('same size diff content', f)

# print first 200 chars of remote hex
print('remote first bytes:', remote[:20].hex())
print('local first file first bytes:', open(os.path.join(PSU_DIR, local_files[0]),'rb').read()[:20].hex())
