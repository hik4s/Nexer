"""Private picker subprocess; stdout carries only fixed state/errors and structural target."""
import json
from pathlib import Path
import sys
from threading import Event, Thread

ROOT = Path(__file__).resolve().parents[1]
for directory in ('apps/runtime', 'apps/recorder'):
    sys.path.insert(0, str(ROOT / directory))
from target_picker_contract import SAFE_PICKER_ERRORS, validate_configuration
from nexer_recorder.target_picker import pick_target


def main():
    stop = Event()
    try:
        line = sys.stdin.readline(8192)
        if len(line) >= 8192: raise ValueError()
        cfg = validate_configuration(json.loads(line))
        def monitor():
            sys.stdin.readline(); stop.set()
        Thread(target=monitor, daemon=True).start()
        def phase(value):
            print(json.dumps({'type': 'phase', 'phase': value}), flush=True)
        target = pick_target(cfg, stop, phase)
        print(json.dumps({'type': 'done', 'target': target}), flush=True)
    except Exception as exc:
        code = str(exc) if str(exc) in SAFE_PICKER_ERRORS else 'TARGET_PICKER_FAILED'
        print(json.dumps({'type': 'error', 'code': code}), flush=True)


if __name__ == '__main__': main()
