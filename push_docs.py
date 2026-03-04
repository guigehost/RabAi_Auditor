import subprocess
import os

os.chdir(r"d:\testcode\audata")

git_path = r"C:\Program Files\Git\bin\git.exe"

commands = [
    [git_path, "add", "."],
    [git_path, "commit", "-m", "Docs: Update rule engine documentation with 18 comprehensive rules"],
    [git_path, "push", "origin", "main"]
]

for cmd in commands:
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    print(f"Return code: {result.returncode}")
    print("---")

print("Done!")
