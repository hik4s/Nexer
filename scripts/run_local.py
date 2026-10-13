"""Local API/worker supervisor. Secrets remain in memory and inherited stdin."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from threading import Event, Thread

ROOT = Path(__file__).resolve().parents[1]
for relative in ("apps/backend", "apps/worker", "apps/runtime"):
    sys.path.insert(0, str(ROOT / relative))


def stop_worker(worker, *, timeout=90):
    if not worker.stdin.closed:
        try:
            worker.stdin.close()  # EOF requests graceful worker/browser cleanup.
        except (BrokenPipeError, OSError):
            pass
    if worker.poll() is not None:
        return
    try:
        worker.wait(timeout=timeout)
        return
    except subprocess.TimeoutExpired:
        pass
    if os.name == "nt":
        # Terminate the known child tree while its root still exists. Killing
        # just Python first can orphan its driver/browser descendants.
        result = subprocess.run(["taskkill", "/PID", str(worker.pid), "/T", "/F"],
            capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0 and worker.poll() is None:
            raise RuntimeError("WORKER_SHUTDOWN_FAILED")
        worker.wait(timeout=10)
        return
    worker.terminate()
    try:
        worker.wait(timeout=10)
    except subprocess.TimeoutExpired:
        worker.kill()
        worker.wait(timeout=5)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-only", action="store_true", help="Mostrar interface sem processar a fila existente.")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=os.getenv("NEXER_WORKER_COUNT", "2"), help="Processos simultâneos, de 1 a 4; padrão 2.")
    options = parser.parse_args()
    import uvicorn
    os.chdir(ROOT)
    from app.local_pairing import pairing_authority
    from app.main import app
    from app.config import get_settings
    from app.worker_channel import worker_channel
    port = get_settings().port
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(str(ROOT / p) for p in ("apps/backend", "apps/worker", "apps/runtime"))
    environment["NEXER_WORKER_CONCURRENCY"] = "1"
    workers = []
    monitor_stop = Event()
    monitor = None
    try:
        for index in range(0 if options.api_only else options.workers):
            worker_id = "ephemeral-" + secrets.token_hex(16)
            capability = secrets.token_urlsafe(32)
            if index == 0: worker_channel.configure(worker_id, capability)
            else: worker_channel.register(worker_id, capability)
            try:
                worker = subprocess.Popen([sys.executable, str(ROOT / "apps/worker/secure_main.py")], cwd=ROOT, stdin=subprocess.PIPE, text=True, env=environment,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            except Exception:
                worker_channel.unregister(worker_id); raise
            workers.append((worker_id, worker))
            worker.stdin.write(json.dumps({"worker_id": worker_id, "capability": capability, "url": f"http://127.0.0.1:{port}"}) + "\n")
            worker.stdin.flush(); capability = None
        def watch_workers():
            while not monitor_stop.wait(0.5):
                for worker_id, worker in workers:
                    if worker.poll() is not None: worker_channel.unregister(worker_id)
        if workers:
            monitor = Thread(target=watch_workers, daemon=True); monitor.start()
        code = pairing_authority.issue()
        print("Nexer local: http://127.0.0.1:5173")
        print("Código de pareamento (uso único, 5 minutos):", code, flush=True)
        code = None
        uvicorn.run(app, host="127.0.0.1", port=port, access_log=False,
            proxy_headers=False, log_level="warning")
    finally:
        monitor_stop.set()
        if monitor is not None: monitor.join(timeout=2)
        # Signal every child before waiting, so a blocked slot cannot postpone
        # shutdown of all other owned browser contexts.
        for _, worker in workers:
            if worker.stdin and not worker.stdin.closed:
                try: worker.stdin.close()
                except (BrokenPipeError, OSError): pass
        deadline = time.monotonic() + 90
        errors = []
        for worker_id, worker in workers:
            try: stop_worker(worker, timeout=max(1, deadline - time.monotonic()))
            except Exception: errors.append("WORKER_SHUTDOWN_FAILED")
            finally: worker_channel.unregister(worker_id)
        if errors: raise RuntimeError("WORKER_SHUTDOWN_FAILED")


if __name__ == "__main__":
    main()
