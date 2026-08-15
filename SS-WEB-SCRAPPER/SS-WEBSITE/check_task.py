import json
with open('data/project_board.json', 'r') as f:
    board = json.load(f)
for col in board['columns']:
    for task in col['tasks']:
        if task['id'] == 'T084':
            print(f"Task T084 is in column: {col['id']}")
            print(json.dumps(task, indent=2))
            break
