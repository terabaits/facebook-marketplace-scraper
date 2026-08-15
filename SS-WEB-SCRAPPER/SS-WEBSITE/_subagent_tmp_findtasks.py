import json
with open('data/project_board.json','r',encoding='utf-8') as f:
    board=json.load(f)
for col in board.get('columns',[]):
    for t in col.get('tasks',[]):
        if t.get('id') in ('T156','T170','T180','T054'):
            print('COLUMN',col['id'],t.get('id'))
            for k,v in t.items():
                print(' ',k,':',v)
            print()
