"""Minimal frontend build — runs vite via subprocess."""

import os
import subprocess
import sys

frontend = r"D:\1233344\rwmod\frontend"
os.chdir(frontend)

# Use the wrapper at D:\DevTools\links
npx = r"D:\DevTools\links\npx.cmd"

print("Building frontend...")
result = subprocess.run(
    [npx, "vite", "build", "--outDir", "../static", "--emptyOutDir"],
    capture_output=True,
    text=True,
    timeout=120,
)
print(result.stdout[-1000:] if result.stdout else "(no stdout)")
if result.returncode != 0:
    print("FAILED:", result.stderr[-500:], file=sys.stderr)
    sys.exit(1)
print("DONE")
