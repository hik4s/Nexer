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
    try:
        configuration = json.loads(sys.stdin.readline())
        def monitor():
            command = sys.stdin.readline().strip()
            (finish if command == "finish" else stop).set()
        Thread(target=monitor, daemon=True).start()
        with tempfile.TemporaryDirectory(prefix="nexer-record-") as directory:
            target = Path(directory) / "recipe.json"
            sys.argv = [sys.argv[0], "--url", configuration["login_url"], "--name", "Fluxo gravado", "--output", str(target)]
            with contextlib.redirect_stdout(io.StringIO()): record(stop_event=stop, finish_event=finish)
            recipe = json.loads(target.read_text(encoding="utf-8"))
            print(json.dumps({"type": "done", "recipe": recipe}), flush=True)
    except BaseException:
        print(json.dumps({"type": "error", "code": "FLOW_RECORDING_FAILED"}), flush=True)
if __name__ == "__main__": main()
