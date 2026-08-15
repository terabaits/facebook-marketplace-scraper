import sys, requests, re
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', errors='replace')
r = requests.get('http://127.0.0.1:5000/laptops')
html = r.text
start = html.find('// Laptop specs panel')
end = html.find('// Price history table', start)
block = html[start:end]
print('block length', len(block))
print('outer comparisonHtml += ` count', block.count('comparisonHtml += `'))
print('outer `; count', block.count('`;'))
print('inner map template open', 'specRows.map(row => `' in block)
print('inner map template close', '`).join' in block)
