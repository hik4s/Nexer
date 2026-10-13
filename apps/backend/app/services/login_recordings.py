"""Owner-bound, bounded login target selection in an owned subprocess."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from threading import RLock, Thread
from time import monotonic
from urllib.parse import urlsplit
from app.schemas_login_profile import LoginConfiguration, LoginTarget
from app.security import resolve_session

ROOT = Path(__file__).resolve().parents[4]


def _start_process():
    return subprocess.Popen([sys.executable, str(ROOT / "scripts/pick_login.py")], cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


class LoginRecordings:
    def __init__(self, *, session_valid=lambda owner: resolve_session(owner) is not None, start_process=_start_process, clock=monotonic):
        self._session_valid = session_valid; self._start_process = start_process; self._clock = clock
        self._entries = {}; self._lock = RLock()
    def _new_entry(self, owner, profile_id, version):
        return {"id": secrets.token_urlsafe(24), "owner": owner, "profile_id": profile_id, "version": version,
            "status": "RECORDING", "targets": {}, "error": None, "expires": self._clock() + 300, "process": None, "thread": None}
    def start(self, owner, profile_id, version, configuration):
        configuration = LoginConfiguration.model_validate(configuration).model_dump()
        if urlsplit(configuration["login_url"]).hostname == "indicadoresenergisaess.scl.corp":
            raise RuntimeError("CORPORATE_AUTH_NOT_VALIDATED")
        with self._lock:
            self.sweep()
            if not self._session_valid(owner): raise RuntimeError("LOGIN_RECORDING_NOT_FOUND")
            if sum(entry["status"] == "RECORDING" for entry in self._entries.values()) >= 2:
                raise RuntimeError("LOGIN_RECORDING_CAPACITY")
            if len(self._entries) >= 32: raise RuntimeError("LOGIN_RECORDING_CAPACITY")
            entry = self._new_entry(owner, profile_id, version)
            process = self._start_process(); entry["process"] = process
            self._entries[entry["id"]] = entry
            try:
                process.stdin.write(json.dumps(configuration) + "\n"); process.stdin.flush()
                thread = Thread(target=self._read, args=(entry,), daemon=True); entry["thread"] = thread; thread.start()
            except Exception:
                self._cancel(entry); self._reap(process); self._entries.pop(entry["id"], None)
                raise RuntimeError("LOGIN_PICKER_FAILED") from None
            return self.get(entry["id"], owner)
    def _read(self, entry):
        process = entry["process"]
        try:
            while True:
                line = process.stdout.readline(16000)
                if not line: break
                if len(line) >= 16000: raise ValueError()
                message = json.loads(line)
                with self._lock:
                    if entry["status"] != "RECORDING": continue
                    if message.get("type") == "target" and message.get("field") in {"username_target", "password_target", "submit_target"}:
                        target = LoginTarget.model_validate(message["target"]).model_dump()
                        entry["targets"][message["field"]] = target
                    elif message.get("type") == "done" and len(entry["targets"]) == 3:
                        entry["status"] = "DONE"; entry["expires"] = self._clock() + 300
                        break
                    elif message.get("type") == "error":
                        entry["status"] = "FAILED"; entry["error"] = "LOGIN_PICKER_FAILED"
                        break
            with self._lock:
                if entry["status"] == "RECORDING": entry["status"] = "FAILED"; entry["error"] = "LOGIN_PICKER_FAILED"
        except Exception:
            with self._lock:
                if entry["status"] == "RECORDING": entry["status"] = "FAILED"; entry["error"] = "LOGIN_PICKER_FAILED"
        finally:
            self._reap(process)
    def _reap(self, process):
        try:
            if process.stdin and not process.stdin.closed: process.stdin.close()
            process.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            if process.poll() is None:
                if os.name == "nt": subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                else: process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=5)
        finally:
            if process.stdout: process.stdout.close()
    def _cancel(self, entry):
        if entry["status"] == "RECORDING":
            entry["status"] = "CANCELLED"
            process = entry["process"]
            if process and process.stdin and not process.stdin.closed:
                try: process.stdin.write("stop\n"); process.stdin.flush(); process.stdin.close()
                except (BrokenPipeError, OSError): pass
    def get(self, session_id, owner):
        with self._lock:
            self.sweep(); entry = self._entries.get(session_id)
            if not entry or entry["owner"] != owner or not self._session_valid(owner): raise RuntimeError("LOGIN_RECORDING_NOT_FOUND")
            return {key: json.loads(json.dumps(entry[key])) for key in ("id", "profile_id", "version", "status", "targets", "error")}
    def cancel(self, session_id, owner):
        with self._lock:
            self.get(session_id, owner); self._cancel(self._entries[session_id]); return self.get(session_id, owner)
    def sweep(self):
        with self._lock:
            for key, entry in list(self._entries.items()):
                if not self._session_valid(entry["owner"]) or self._clock() >= entry["expires"]:
                    self._cancel(entry)
                    thread = entry["thread"]
                    if thread is None or not thread.is_alive(): self._entries.pop(key, None)
    def close_all(self):
        with self._lock:
            entries = list(self._entries.values())
            for entry in entries: self._cancel(entry)
        for entry in entries:
            if entry["thread"]: entry["thread"].join(timeout=6)

login_recordings = LoginRecordings()
