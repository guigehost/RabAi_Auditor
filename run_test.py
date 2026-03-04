import subprocess
import sys

result = subprocess.run(
    [sys.executable, "main.py"],
    capture_output=True,
    text=True,
    cwd=r"d:\testcode\audata",
    timeout=10
)

with open("run_result.txt", "w", encoding="utf-8") as f:
    f.write("STDOUT:\n" + result.stdout + "\n\nSTDERR:\n" + result.stderr + "\n\nReturn code: " + str(result.returncode))

print("Result saved to run_result.txt")
print("Return code:", result.returncode)
if result.stderr:
    print("STDERR:", result.stderr[:500])
