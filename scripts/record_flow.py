"""Private wizard recorder protocol; temporary output is parameterized only."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
from threading import Event, Thread
from record_recipe import main as record

def main():
    stop, finish = Event(), Event()
    protocol_stdout = sys.stdout
    def started():
        print(json.dumps({"type": "started"}), file=protocol_stdout, flush=True)
    try:
        configuration = json.loads(sys.stdin.readline())
        def monitor():
            command = sys.stdin.readline().strip()
            (finish if command == "finish" else stop).set()
        Thread(target=monitor, daemon=True).start()
        with tempfile.TemporaryDirectory(prefix="nexer-record-") as directory:
            target = Path(directory) / "recipe.json"
            sys.argv = [sys.argv[0], "--url", configuration["login_url"], "--name", "Fluxo gravado", "--output", str(target), "--smart-waits"]
            with contextlib.redirect_stdout(io.StringIO()): record(stop_event=stop, finish_event=finish, on_started=started)
            recipe = json.loads(target.read_text(encoding="utf-8"))
            print(json.dumps({"type": "done", "recipe": recipe}), flush=True)
    except BaseException as exc:
        allowed = {"RECORDER_CANCELLED", "RECORDER_EMPTY", "RECORDER_CONTEXT_UNSUPPORTED", "RECORDER_DOWNLOAD_UNSUPPORTED", "RECORDER_BROWSER_FAILED"}
        code = str(exc) if isinstance(exc, RuntimeError) and str(exc) in allowed else "FLOW_RECORDING_FAILED"
        print(json.dumps({"type": "error", "code": code}), file=protocol_stdout, flush=True)
if __name__ == "__main__": main()
