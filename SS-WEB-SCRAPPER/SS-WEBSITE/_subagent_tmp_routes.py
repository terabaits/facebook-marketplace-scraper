import re
with open('app.py','r',encoding='utf-8') as f:
    lines=f.readlines()
for i,line in enumerate(lines,1):
    if 'project-board' in line.lower() or '/task/' in line.lower():
        print(f'{i:4}: {line.rstrip()}')
