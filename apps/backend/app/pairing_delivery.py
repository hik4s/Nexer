"""Deliver one-time codes to the local operator, never through HTTP."""
import json
import os
from pathlib import Path
import subprocess
import sys
from threading import Event, Thread


ROOT = Path(__file__).resolve().parents[3]


def deliver_pairing_code(code, settings):
    if settings.pairing_code_display == "console":
        print(f"Código de pareamento (uso único, 5 minutos): {code}", flush=True)
        return
    process = None
    try:
        process = subprocess.Popen([sys.executable, str(ROOT / "scripts/show_pairing_code.py")],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        process.stdin.write(json.dumps({"code": code}) + "\n")
        process.stdin.flush()
        process.stdin.close()
        ready = Event()
        acknowledgement = []
        def watch_window():
            try:
                acknowledgement.append(process.stdout.readline(16))
            finally:
                ready.set()
            process.wait()
            process.stdout.close()
        Thread(target=watch_window, name="nexer-pairing-window", daemon=True).start()
        if not ready.wait(5) or acknowledgement != ["READY\n"]:
            raise RuntimeError()
    except Exception:
        if process is not None:
            try:
                process.stdin.close()
            except Exception:
                pass
            try:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=5)
            except Exception:
                pass
        raise RuntimeError("PAIRING_DELIVERY_FAILED") from None
