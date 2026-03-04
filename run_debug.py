import os
import sys
import traceback

log_file = open("debug_log.txt", "w", encoding="utf-8")

def log(msg):
    print(msg)
    log_file.write(str(msg) + "\n")
    log_file.flush()

log("Python version: " + sys.version)
log("Current directory: " + os.getcwd())
log("Files in directory: " + str(os.listdir(".")))

try:
    log("\nImporting main module...")
    import main
    log("Import successful!")
    
    log("\nStarting server...")
    import uvicorn
    log("Uvicorn imported")
    
    log("\nRunning server...")
    uvicorn.run(main.app, host="0.0.0.0", port=8000)
    
except Exception as e:
    log(f"\nError: {e}")
    log(traceback.format_exc())

log_file.close()
