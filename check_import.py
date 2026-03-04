import subprocess
import sys

result = subprocess.run(
    [sys.executable, "-c", "import main; print('Import OK')"],
    capture_output=True,
    text=True,
    cwd=r"d:\testcode\audata"
)

with open("import_result.txt", "w", encoding="utf-8") as f:
    f.write("STDOUT:\n" + result.stdout + "\n\n")
    f.write("STDERR:\n" + result.stderr + "\n\n")
    f.write("Return code: " + str(result.returncode))

print("Result saved to import_result.txt")
