import os
import sys

os.chdir(r"d:\testcode\audata")
sys.path.insert(0, r"d:\testcode\audata")

print("Current directory:", os.getcwd())
print("Python version:", sys.version)
print("\nImporting modules...")

try:
    print("Importing fastapi...")
    from fastapi import FastAPI
    print("OK")
    
    print("Importing pandas...")
    import pandas as pd
    print("OK")
    
    print("Importing numpy...")
    import numpy as np
    print("OK")
    
    print("\nImporting main module...")
    import main
    print("OK")
    
    print("\nStarting server...")
    import uvicorn
    uvicorn.run(main.app, host="0.0.0.0", port=8002)
    
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
    input("\nPress Enter to exit...")
