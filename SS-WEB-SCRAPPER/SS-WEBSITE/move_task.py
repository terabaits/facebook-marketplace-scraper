import json
import sys
from datetime import datetime

args = sys.argv[1:]
if len(args) < 2:
    print("Usage: python move_task.py <TASK_ID> <target_column>")
    sys.exit(1)

target_id = args[0]
target_col = args[1]

with open('data/project_board.json', 'r', encoding='utf-8') as f:
    board = json.load(f)

moved = False
for col in board['columns']:
    for task in list(col['tasks']):
        if task['id'] == target_id:
            task['column'] = target_col
            task['updated'] = datetime.now().isoformat()
            if target_col == 'progress':
                task['started_at'] = datetime.now().isoformat()
            if target_col == 'talking':
                task['completed_at'] = datetime.now().isoformat()
            col['tasks'].remove(task)
            for scol in board['columns']:
                if scol['id'] == target_col:
                    scol['tasks'].append(task)
                    break
            moved = True
            break
    if moved:
        break

with open('data/project_board.json', 'w', encoding='utf-8') as f:
    json.dump(board, f, indent=2)

if moved:
    print(f'{target_id} moved to {target_col}')
else:
    print(f'{target_id} not found')
    sys.exit(1)
