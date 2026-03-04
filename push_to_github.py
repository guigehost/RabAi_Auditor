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

# Try to remove .git directory, but continue if it fails
if os.path.exists(".git"):
    try:
        # Change permissions first
        subprocess.run(["icacls", ".git", "/grant", "Everyone:(OI)(CI)F", "/T"], capture_output=True)
        shutil.rmtree(".git", onerror=lambda func, path, exc: os.chmod(path, 0o777) or func(path))
        print("Removed existing .git directory")
    except Exception as e:
        print(f"Could not remove .git: {e}")
        print("Continuing with existing repository...")

# Initialize new repository
run_git(["init"])

# Configure git user if not set
run_git(["config", "user.email", "auditor@example.com"], check=False)
run_git(["config", "user.name", "Auditor"], check=False)

# Add all files
run_git(["add", "."])

# Commit
run_git(["commit", "-m", "Initial commit: Intelligent Audit Tool with Mistral-7B integration"])

# Remove existing remote if any
run_git(["remote", "remove", "origin"], check=False)

# Add remote
run_git(["remote", "add", "origin", "https://github.com/guigehost/RabAi_Auditor.git"])

# Force push to overwrite remote
run_git(["push", "-u", "origin", "main", "--force"])

print("\nDone!")
