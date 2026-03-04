print("Starting test...")

print("1. Testing imports...")
try:
    from fastapi import FastAPI
    print("   FastAPI OK")
except Exception as e:
    print(f"   FastAPI FAILED: {e}")

try:
    import pandas as pd
    print("   Pandas OK")
except Exception as e:
    print(f"   Pandas FAILED: {e}")

try:
    import numpy as np
    print("   NumPy OK")
except Exception as e:
    print(f"   NumPy FAILED: {e}")

try:
    import uvicorn
    print("   Uvicorn OK")
except Exception as e:
    print(f"   Uvicorn FAILED: {e}")

print("\n2. Testing main.py import...")
try:
    import main
    print("   main.py OK")
except Exception as e:
    print(f"   main.py FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\nTest complete!")
input("Press Enter to exit...")
