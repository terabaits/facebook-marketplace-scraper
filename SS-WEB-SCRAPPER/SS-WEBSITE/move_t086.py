import json
from datetime import datetime

with open('data/project_board.json', 'r', encoding='utf-8') as f:
    board = json.load(f)

for col in board['columns']:
    if col['id'] == 'assignment':
        for task in col['tasks']:
            if task['id'] == 'T086':
                task['column'] = 'talking'
                task['completed_at'] = datetime.now().isoformat()
                task['fix'] = 'Enhanced task detail popup: Added "📨 Linked From (Incoming)" section showing all tasks that link TO this task. Task cards already show link count badge. Separated outgoing links (🔗 Linked Tasks) from incoming links (📨 Linked From).'
                task['updated'] = datetime.now().isoformat()
                col['tasks'].remove(task)
                for scol in board['columns']:
                    if scol['id'] == 'talking':
                        scol['tasks'].append(task)
                        break
                break

with open('data/project_board.json', 'w', encoding='utf-8') as f:
    json.dump(board, f, indent=2)

print('T086 moved to Review (talking)')
