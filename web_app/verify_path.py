import sys
import os
from pathlib import Path

# Add the web_app directory to the Python path to allow imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Now import the function from the app
from app import discover_metrics_files

print("--- Running verification script ---")
found_files = discover_metrics_files()

if not found_files:
    print("❌ Verification failed: No metrics files were found.")
else:
    print(f"✅ Verification successful: Found {len(found_files)} metrics file(s).")
    for f in found_files:
        print(f"  - {f['filename']}")
print("---------------------------------")
