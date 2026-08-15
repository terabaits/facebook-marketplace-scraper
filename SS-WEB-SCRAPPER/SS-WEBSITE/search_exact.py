import os, requests, re
PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
url = 'https://www.ss.com/msg/lv/electronics/computers/completing-pc/cases/bxbeio.html'
remote = requests.get(url, timeout=25, headers={'User-Agent':'Mozilla/5.0'})
text = remote.text
imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+\.800\.jpg', text)
remote_content = requests.get(imgs[0], timeout=25, headers={'User-Agent':'Mozilla/5.0'}).content
for f in os.listdir(PSU_DIR):
    if not f.lower().endswith(('.jpg','.jpeg','.png','.webp')): continue
    path = os.path.join(PSU_DIR, f)
    with open(path,'rb') as fh:
        local = fh.read()
    if local == remote_content:
        print('EXACT', f)
    elif len(local) == len(remote_content):
        print('SAME_SIZE', f)
