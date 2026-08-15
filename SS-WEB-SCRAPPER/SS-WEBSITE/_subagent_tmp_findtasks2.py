import json
with open('data/project_board.json','r',encoding='utf-8') as f:
    board=json.load(f)
with open('_subagent_tmp_findtasks2_out.txt','w',encoding='utf-8') as out:
    for col in board.get('columns',[]):
        for t in col.get('tasks',[]):
            if t.get('id') in ('T156','T170','T180','T054'):
                out.write(f"COLUMN {col['id']} {t.get('id')}\n")
                for k,v in t.items():
                    out.write(f"  {k} : {v}\n")
                out.write("\n")
