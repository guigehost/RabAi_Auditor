import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-m", "py_compile", "main.py"],
    capture_output=True,
    text=True,
    cwd=r"d:\testcode\audata"
)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)
