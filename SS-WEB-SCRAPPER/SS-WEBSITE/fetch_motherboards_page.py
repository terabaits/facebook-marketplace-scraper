import requests
import re
r = requests.get('http://localhost:5000/motherboards', timeout=15)
print('status', r.status_code, 'content-type', r.headers.get('content-type'))
text = r.text
imgs = re.findall(r'<img[^\u003e]+src="([^"]+)"', text)
print('img src count', len(imgs))
for src in imgs[:10]:
    print('src:', src[:200])
print('local_image_path in page:', 'local_image_path' in text)
print('rowImgUrl in page:', 'rowImgUrl' in text)
print('detailImgUrl in page:', 'detailImgUrl' in text)
# check if any literal /images/ path appears
for m in re.finditer(r'/images/[^"\s]+', text):
    print('literal /images path:', m.group(0)[:200])
