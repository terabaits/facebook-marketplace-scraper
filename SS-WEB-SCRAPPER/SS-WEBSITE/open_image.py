import os
from PIL import Image
PSU_DIR = 'G:/Github/SS-WEB-SCRAPPER/SS-CRAWLER/images/psu'
path = os.path.join(PSU_DIR, '11216122_69d36d4f.jpg')
img = Image.open(path)
print(img.size, img.format, img.mode)
