import os
os.chdir(r"d:\testcode\audata")

print("Testing main.py import...")
try:
    import main
    print("Import successful!")
    print("Starting server...")
    import uvicorn
    uvicorn.run(main.app, host="0.0.0.0", port=8000)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
