import requests, hashlib, re
url = 'https://www.ss.com/msg/lv/electronics/computers/completing-pc/cases/bxbeio.html'
text = requests.get(url, timeout=25, headers={'User-Agent':'Mozilla/5.0'}).text
imgs = re.findall(r'https://i\.ss\.com/gallery/[^"\'\s]+', text)
print('page imgs:', imgs)
for img in imgs[:2]:
    for suffix in ['.800.jpg', '.t.jpg', '.jpg']:
        base = img
        if base.endswith('.t.jpg'):
            base = base[:-6]
        elif base.endswith('.800.jpg'):
            base = base[:-9]
        test_url = base + suffix
        r = requests.get(test_url, timeout=25, headers={'User-Agent':'Mozilla/5.0'})
        print(test_url, r.status_code, len(r.content), hashlib.md5(r.content).hexdigest())
