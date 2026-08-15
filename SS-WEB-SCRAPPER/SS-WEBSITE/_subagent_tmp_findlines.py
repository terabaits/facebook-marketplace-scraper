import re
path='templates/pc_builder.html'
keywords=['select-container','search-dropdown','component-select','view-listings-btn','select-search','component-body','component-card']
with open(path,'r',encoding='utf-8') as f:
    lines=f.readlines()
out=[]
for i,l in enumerate(lines,1):
    low=l.lower()
    if any(k in low for k in keywords):
        out.append(f'{i:4}: {l.rstrip()}')
with open('_subagent_tmp_findlines_out.txt','w',encoding='utf-8') as f:
    f.write('\n'.join(out))
