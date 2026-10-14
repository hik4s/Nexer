"""Owner-bound, ephemeral visual target sessions. No database or recorded values."""
import json
import os
import subprocess
import sys
from threading import Thread
from app.services.login_recordings import LoginRecordings, ROOT
from target_picker_contract import validate_configuration, validate_target, SAFE_PICKER_ERRORS


def start_process():
    return subprocess.Popen([sys.executable, str(ROOT / 'scripts/pick_target.py')], cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)


class TargetPickings(LoginRecordings):
    def _validate_configuration(self, configuration):
        return validate_configuration(configuration)

    def _new_entry(self, *args):
        entry = super()._new_entry(*args)
        entry.update(phase='PREPARING', target=None, reaper=None)
        return entry

    def start_target(self, owner, url, kind):
        return self.start(owner, 0, 1, {'url': url, 'kind': kind})

    def _read(self, entry):
        process = entry['process']
        try:
            while True:
                line = process.stdout.readline(16384)
                if not line or len(line) >= 16384: raise ValueError()
                message = json.loads(line)
                with self._lock:
                    if entry['status'] != 'RECORDING': break
                    if set(message) == {'type', 'phase'} and message['type'] == 'phase' and message['phase'] in {'PREPARING', 'SELECTING'}:
                        entry['phase'] = message['phase']
                    elif set(message) == {'type', 'target'} and message['type'] == 'done' and entry['phase'] == 'SELECTING':
                        entry['target'] = validate_target(message['target'])
                        entry['status'] = 'DONE'; entry['expires'] = self._clock() + 300
                        break
                    elif set(message) == {'type', 'code'} and message['type'] == 'error':
                        code = message['code']
                        entry['error'] = code if isinstance(code, str) and code in SAFE_PICKER_ERRORS else 'TARGET_PICKER_FAILED'
                        entry['status'] = 'CANCELLED' if entry['error'] == 'TARGET_PICKER_CANCELLED' else 'FAILED'
                        break
                    else:
                        raise ValueError()
        except Exception:
            with self._lock:
                if entry['status'] == 'RECORDING':
                    entry['status'] = 'FAILED'; entry['error'] = 'TARGET_PICKER_FAILED'
        finally:
            self._reap(process)

    def get(self, session_id, owner):
        with self._lock:
            super().get(session_id, owner)
            entry = self._entries[session_id]
            return {key: json.loads(json.dumps(entry[key])) for key in ('id', 'status', 'phase', 'target', 'error')}

    def _cancel(self, entry):
        active = entry['status'] == 'RECORDING'
        super()._cancel(entry)
        if active and entry['process'] is not None and entry['reaper'] is None:
            entry['reaper'] = Thread(target=self._reap, args=(entry['process'],), daemon=True)
            entry['reaper'].start()


target_pickings = TargetPickings(start_process=start_process)
