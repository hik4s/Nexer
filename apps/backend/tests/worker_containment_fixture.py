"""Synthetic worker deliberately blocked with a child that ignores pipe shutdown."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
for relative in ("apps/backend", "apps/worker", "apps/runtime"):
    sys.path.insert(0, str(ROOT / relative))
import secure_main


def blocked_worker(**kwargs):
    child = subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-Command", "Start-Sleep -Seconds 60"],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps({"worker_pid": os.getpid(), "child_pid": child.pid}), flush=True)
    time.sleep(60)


secure_main.main = blocked_worker
secure_main.entrypoint()
