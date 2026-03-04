import subprocess
import sys
import os

os.chdir(r"d:\testcode\audata")

print("Starting backend server on port 9001...")
backend = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9001"],
    cwd=r"d:\testcode\audata"
)

print("Backend started. Press Ctrl+C to stop.")
try:
    backend.wait()
except KeyboardInterrupt:
    backend.terminate()
    print("Server stopped.")
