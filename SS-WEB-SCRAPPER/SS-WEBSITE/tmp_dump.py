from pathlib import Path
html=Path('G:/Github/SS-WEB-SCRAPPER/SS-WEBSITE/templates/monitors.html').read_text(encoding='utf-8')
idx=html.find('category-grid')
Path('G:/Github/SS-WEB-SCRAPPER/SS-WEBSITE/tmp_out.txt').write_text(html[idx-50:idx+2000], encoding='utf-8')
