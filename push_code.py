import subprocess
import os

os.chdir(r"d:\testcode\audata")

git_path = r"C:\Program Files\Git\bin\git.exe"

commands = [
    [git_path, "add", "."],
    [git_path, "commit", "-m", "Fix: Update API port, improve frontend UI, fix JSON serialization"],
    [git_path, "push", "origin", "main", "--force"]
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
