"""Local API/worker supervisor. Secrets remain in memory and inherited stdin."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
for relative in ("apps/backend", "apps/worker", "apps/runtime"):
    sys.path.insert(0, str(ROOT / relative))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-only", action="store_true", help="Mostrar interface sem processar a fila existente.")
    options = parser.parse_args()
    import uvicorn
    os.chdir(ROOT)
    from app.local_pairing import pairing_authority
    from app.main import app
    from app.worker_channel import worker_channel
    worker_id = "ephemeral-" + secrets.token_hex(16)
    capability = secrets.token_urlsafe(32)
    worker_channel.configure(worker_id, capability)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(str(ROOT / p) for p in ("apps/backend", "apps/worker", "apps/runtime"))
    worker = None if options.api_only else subprocess.Popen([sys.executable, str(ROOT / "apps/worker/secure_main.py")],
        cwd=ROOT, stdin=subprocess.PIPE, text=True, env=environment)
    try:
        if worker is not None:
            worker.stdin.write(json.dumps({"worker_id": worker_id, "capability": capability,
                "url": "http://127.0.0.1:8000"}) + "\n")
            worker.stdin.close()
        capability = None
        code = pairing_authority.issue()
        print("Nexer local: http://127.0.0.1:5173")
        print("Código de pareamento (uso único, 5 minutos):", code, flush=True)
        code = None
        uvicorn.run(app, host="127.0.0.1", port=8000, access_log=False,
            proxy_headers=False, log_level="warning")
    finally:
        if worker is not None and worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=10)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()


if __name__ == "__main__":
    main()
