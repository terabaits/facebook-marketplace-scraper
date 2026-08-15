#!/usr/bin/env python
import subprocess
import sys

# Kill any existing python processes
subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], capture_output=True)

# Start the Flask server
import app
if __name__ == '__main__':
    app.app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
