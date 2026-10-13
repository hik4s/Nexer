import json
import os
import subprocess
import sys
from urllib.parse import urlsplit
from app.services.login_recordings import LoginRecordings, ROOT
from recipe import validate_recipe

def start_process():
    return subprocess.Popen([sys.executable, str(ROOT / "scripts/record_flow.py")], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
class FlowRecordings(LoginRecordings):
    def start_flow(self, owner, url):
        parsed = urlsplit(url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.query or parsed.fragment or parsed.username or parsed.password: raise RuntimeError("FLOW_RECORDING_LOCAL_ONLY")
        return self.start(owner, 0, 1, {"login_url": url})
    def _new_entry(self, *args):
        entry = super()._new_entry(*args); entry["recipe"] = None; return entry
    def _read(self, entry):
        process = entry["process"]
        try:
            message = json.loads(process.stdout.readline(1048576))
            if message.get("type") != "done": raise ValueError()
            recipe = validate_recipe(message["recipe"])
            if any(value.get("secret") for value in recipe.get("variables", {}).values()): raise ValueError()
            with self._lock:
                if entry["status"] == "RECORDING": entry["recipe"] = recipe; entry["status"] = "DONE"; entry["expires"] = self._clock() + 300
        except Exception:
            with self._lock:
                if entry["status"] == "RECORDING": entry["status"] = "FAILED"; entry["error"] = "FLOW_RECORDING_FAILED"
        finally: self._reap(process)
    def get(self, session_id, owner):
        result = super().get(session_id, owner)
        with self._lock: result["recipe"] = json.loads(json.dumps(self._entries[session_id]["recipe"]))
        return result
    def finish(self, session_id, owner):
        with self._lock:
            result = self.get(session_id, owner)
            if result["status"] == "RECORDING":
                process = self._entries[session_id]["process"]
                try: process.stdin.write("finish\n"); process.stdin.flush()
                except (BrokenPipeError, OSError): raise RuntimeError("FLOW_RECORDING_FAILED") from None
            return result
flow_recordings = FlowRecordings(start_process=start_process)
