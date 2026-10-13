import json
import os
import subprocess
import sys
from urllib.parse import urlsplit
from site_urls import validate_site_url
from app.services.login_recordings import LoginRecordings, ROOT
from recipe import validate_recipe

def start_process():
    return subprocess.Popen([sys.executable, str(ROOT / "scripts/record_flow.py")], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
class FlowRecordings(LoginRecordings):
    def start_flow(self, owner, url):
        url = validate_site_url(url)
        with self._lock:
            self._starting_phase = "PREPARING" if urlsplit(url).scheme == "https" else "RECORDING"
            return self.start(owner, 0, 1, {"login_url": url})
    def _new_entry(self, *args):
        entry = super()._new_entry(*args)
        entry["recipe"] = None
        entry["phase"] = getattr(self, "_starting_phase", "RECORDING")
        return entry
    def _read(self, entry):
        process = entry["process"]
        try:
            while True:
                line = process.stdout.readline(1048576)
                if not line or len(line) >= 1048576: raise ValueError()
                message = json.loads(line)
                with self._lock:
                    if entry["status"] != "RECORDING": break
                    if message.get("type") == "started":
                        entry["phase"] = "RECORDING"
                        continue
                    if message.get("type") == "error":
                        allowed = {"RECORDER_CANCELLED", "RECORDER_EMPTY", "RECORDER_CONTEXT_UNSUPPORTED", "RECORDER_DOWNLOAD_UNSUPPORTED", "RECORDER_BROWSER_FAILED"}
                        entry["status"] = "FAILED"
                        entry["error"] = message.get("code") if message.get("code") in allowed else "FLOW_RECORDING_FAILED"
                        break
                    if message.get("type") != "done" or entry["phase"] != "RECORDING": raise ValueError()
                    recipe = validate_recipe(message["recipe"])
                    if len(recipe["steps"]) <= 1 or any(value.get("secret") for value in recipe.get("variables", {}).values()): raise ValueError()
                    entry["recipe"] = recipe
                    entry["status"] = "DONE"
                    entry["expires"] = self._clock() + 300
                    break
        except Exception:
            with self._lock:
                if entry["status"] == "RECORDING": entry["status"] = "FAILED"; entry["error"] = "FLOW_RECORDING_FAILED"
        finally: self._reap(process)
    def get(self, session_id, owner):
        result = super().get(session_id, owner)
        with self._lock: result["recipe"] = json.loads(json.dumps(self._entries[session_id]["recipe"])); result["phase"] = self._entries[session_id]["phase"]
        return result
    def finish(self, session_id, owner):
        with self._lock:
            result = self.get(session_id, owner)
            if result["status"] == "RECORDING":
                if result["phase"] == "PREPARING": raise RuntimeError("FLOW_RECORDING_PREPARING")
                process = self._entries[session_id]["process"]
                try: process.stdin.write("finish\n"); process.stdin.flush()
                except (BrokenPipeError, OSError): raise RuntimeError("FLOW_RECORDING_FAILED") from None
            return result
flow_recordings = FlowRecordings(start_process=start_process)
