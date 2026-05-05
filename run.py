import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("Starting SECFAOS...")
print("Backend  → http://localhost:8000")
print("Frontend → http://localhost:5173")
print("Press Ctrl+C to stop both\n")

backend  = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api.main:app", "--reload", "--port", "8000"],
    cwd=BASE_DIR
)

frontend = subprocess.Popen(
    ["npm", "run", "dev"],
    cwd=os.path.join(BASE_DIR, "frontend"),
    shell=True
)

try:
    backend.wait()
    frontend.wait()
except KeyboardInterrupt:
    print("\nShutting down...")
    backend.terminate()
    frontend.terminate()