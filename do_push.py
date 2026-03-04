import os
import subprocess

git_path = r"C:\Program Files\Git\bin\git.exe"
os.chdir(r"d:\testcode\audata")

print("Pushing to GitHub...")

# First check if we need to login
result = subprocess.run([git_path, "remote", "-v"], capture_output=True, text=True)
print("Remote:", result.stdout)

# Push
result = subprocess.run([git_path, "push", "-u", "origin", "main", "--force"], capture_output=True, text=True, timeout=300)
print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)

if result.returncode == 0:
    print("\nSUCCESS! Repository pushed to: https://github.com/guigehost/RabAi_Auditor")
else:
    print("\nPush failed. You may need to authenticate with GitHub.")
    print("Try running: git push -u origin main --force")
