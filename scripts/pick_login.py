"""Private subprocess protocol. stdout contains target metadata only."""
import json
from pathlib import Path
import sys
from threading import Event, Thread
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/recorder"))
from nexer_recorder.login_picker import pick_login

def main():
    stop = Event()
    try:
        configuration = json.loads(sys.stdin.readline())
        def monitor():
            sys.stdin.readline(); stop.set()
        Thread(target=monitor, daemon=True).start()
        def target(field, location):
            print(json.dumps({"type": "target", "field": field, "target": location}), flush=True)
        targets = pick_login(configuration, stop, target)
        print(json.dumps({"type": "done", "targets": targets}), flush=True)
    except Exception as exc:
        code = str(exc) if str(exc) in {"CORPORATE_AUTH_NOT_VALIDATED", "LOGIN_PICKER_CANCELLED", "LOGIN_PICKER_TIMEOUT"} else "LOGIN_PICKER_FAILED"
        print(json.dumps({"type": "error", "code": code}), flush=True)

if __name__ == "__main__": main()
