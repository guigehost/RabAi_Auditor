import subprocess
import sys
import os
import time

os.chdir(r"d:\testcode\audata")

python_exe = sys.executable
print(f"Python executable: {python_exe}")
print(f"Current directory: {os.getcwd()}")
print(f"main.py exists: {os.path.exists('main.py')}")

print("\nStarting backend server...")
process = subprocess.Popen(
    [python_exe, "main.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

print("Waiting for server to start...")
time.sleep(5)

# Check if process is still running
if process.poll() is None:
    print("Server is running!")
    print("Backend API: http://localhost:8002")
    print("Press Ctrl+C to stop")
    try:
        while True:
            line = process.stdout.readline()
            if line:
                print(line, end='')
            time.sleep(0.1)
    except KeyboardInterrupt:
        process.terminate()
        print("\nServer stopped.")
else:
    print("Server failed to start!")
    print("Output:")
    print(process.stdout.read())
