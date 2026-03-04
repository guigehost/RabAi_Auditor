import os
import sys
import traceback

os.chdir(r"d:\testcode\audata")

log_file = open("app_log.txt", "w", encoding="utf-8")

def log(msg):
    print(msg)
    log_file.write(str(msg) + "\n")
    log_file.flush()

log("Starting application...")
log(f"Python: {sys.version}")
log(f"Directory: {os.getcwd()}")

try:
    log("Importing FastAPI...")
    from fastapi import FastAPI
    log("OK")
    
    log("Importing main module...")
    import main
    log("OK")
    
    log("Starting uvicorn...")
    import uvicorn
    log(f"App type: {type(main.app)}")
    uvicorn.run(main.app, host="0.0.0.0", port=8002)
    
except Exception as e:
    log(f"ERROR: {e}")
    log(traceback.format_exc())

log_file.close()
