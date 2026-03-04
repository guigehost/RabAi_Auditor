import os
import subprocess
import shutil

possible_git_paths = [
    r"C:\Program Files\Git\bin\git.exe",
    r"C:\Program Files (x86)\Git\bin\git.exe",
    r"C:\Git\bin\git.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\Git\bin\git.exe"),
    os.path.expanduser(r"~\scoop\apps\git\current\bin\git.exe"),
]

git_path = None
for path in possible_git_paths:
    if os.path.exists(path):
        git_path = path
        print(f"Found Git at: {path}")
        break

if not git_path:
    print("Git not found in common locations. Please check your installation.")
    exit(1)

os.chdir(r"d:\testcode\audata")

def run_git(args, check=True):
    cmd = [git_path] + args
    print(f"\nRunning: {' '.join(args)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        if check and result.returncode != 0:
            print(f"Command failed with return code: {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

# Rename branch from master to main
run_git(["branch", "-M", "main"])

# Force push to overwrite remote
run_git(["push", "-u", "origin", "main", "--force"])

print("\nDone!")
