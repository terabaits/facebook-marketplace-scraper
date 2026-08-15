import re
with open('G:/Github/SS-WEB-SCRAPPER/SS-WEBSITE/templates/ssd.html', 'r', encoding='utf-8') as f:
    content = f.read()
    
# Find the capacity filter select element
match = re.search(r'<select[^>]*id=["\']capacity-filter["\'][^>]*>(.*?)</select>', content, re.DOTALL)
if match:
    print('Capacity filter dropdown found:')
    print(match.group(0))
else:
    print('Looking for capacity-filter...')
    # Try to find any capacity related select
    for i, line in enumerate(content.split('\n')):
        if 'capacity' in line.lower() and ('select' in line.lower() or 'option' in line.lower()):
            print(f'{i+1}: {line}')
