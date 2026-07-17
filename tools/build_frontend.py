"""Build rwmod frontend via Vite — used when shell npm is unavailable."""

import os
import subprocess
import sys
from pathlib import Path

frontend_dir = Path(r"D:\1233344\rwmod\frontend")
os.chdir(str(frontend_dir))

# Locate npx
npx = r"D:\DevTools\links\npx.cmd"

# Ensure deps
print("[1/2] Installing dependencies...")
subprocess.run([npx, "--version"], capture_output=True)

# Build
print("[2/2] Building frontend...")
result = subprocess.run(
    [npx, "vite", "build", "--outDir", "../static", "--emptyOutDir"],
    capture_output=True,
    text=True,
)
print(result.stdout)
if result.returncode != 0:
    print("STDERR:", result.stderr, file=sys.stderr)
    sys.exit(1)
print("✅ Build complete")
