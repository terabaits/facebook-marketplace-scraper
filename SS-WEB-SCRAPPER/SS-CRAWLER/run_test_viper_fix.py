import subprocess
import os

# Run the test command with UTF-8 encoding
result = subprocess.run(
    ["python", "main.py", "test-url", "https://www.ss.com/msg/lv/electronics/computers/pc/pbdhn.html", "--computers"],
    capture_output=True,
    encoding='utf-8',
    errors='replace'
)

# Write output to file
with open('test_output_after_viper_fix.txt', 'w', encoding='utf-8') as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write(result.stderr)
    f.write("\n\nReturn code: " + str(result.returncode))

print("Output saved to test_output_after_viper_fix.txt")
