"""Authenticated, execution-bound access; no durable capability or credentials."""
import hmac
from threading import RLock
from app.security import credential_vault, resolve_session


class WorkerCredentialChannel:
    def __init__(self, *, vault, lookup_execution, session_valid):
        self._vault = vault; self._lookup = lookup_execution; self._session_valid = session_valid
        self._lock = RLock(); self._worker_id = None; self._capability = None
        self._owners = {}; self._expected_workers = {}; self._workers = {}; self._incarnations = {}
        self._generation = 0; self._cursor = 0
    def __repr__(self): return "WorkerCredentialChannel()"
    def configure(self, worker_id, capability):
        with self._lock:
            for execution_id in list(self._owners): self.revoke(execution_id)
            self._workers.clear(); self._incarnations.clear(); self._worker_id = None; self._capability = None
            self.register(worker_id, capability)
    def register(self, worker_id, capability):
        if not isinstance(worker_id, str) or not worker_id or not isinstance(capability, str) or not capability:
            raise ValueError("INVALID_WORKER_CHANNEL")
        with self._lock:
            if any(identity != worker_id and hmac.compare_digest(value.encode(), capability.encode()) for identity, value in self._workers.items()):
                raise ValueError("INVALID_WORKER_CHANNEL")
            if worker_id in self._workers: self.unregister(worker_id)
            self._generation += 1; self._workers[worker_id] = capability; self._incarnations[worker_id] = self._generation
            if self._worker_id is None: self._worker_id = worker_id; self._capability = capability
    def unregister(self, worker_id):
        with self._lock:
            for execution_id, expected in list(self._expected_workers.items()):
                if expected == worker_id: self.revoke(execution_id)
            self._workers.pop(worker_id, None); self._incarnations.pop(worker_id, None)
            if self._worker_id == worker_id:
                self._worker_id = next(iter(self._workers), None); self._capability = self._workers.get(self._worker_id)
    def worker_ids(self):
        with self._lock: return tuple(self._workers) if self._capability else ()
    def incarnation(self, worker_id):
        with self._lock:
            if not self._capability or worker_id not in self._incarnations: raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            return self._incarnations[worker_id]
    def choose_worker(self, available):
        with self._lock:
            choices = [worker for worker in available if worker in self.worker_ids()]
            if not choices: raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            worker = choices[self._cursor % len(choices)]; self._cursor += 1
            return worker
    def _worker_for(self, capability):
        if not isinstance(capability, str) or not self._capability: return None
        return next((worker for worker, value in self._workers.items() if hmac.compare_digest(value.encode(), capability.encode())), None)
    def authorized(self, capability):
        with self._lock: return self._worker_for(capability) is not None
    def current_worker_id(self):
        with self._lock:
            if not self._worker_id or not self._capability: raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            return self._worker_id
    def bind(self, execution_id, owner, *, expected_worker_id=None, expected_incarnation=None):
        with self._lock:
            worker = expected_worker_id or self.current_worker_id()
            if worker not in self._workers or (expected_incarnation is not None and self._incarnations.get(worker) != expected_incarnation):
                raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            if execution_id in self._owners: raise RuntimeError("CREDENTIALS_ALREADY_BOUND")
            self._owners[execution_id] = owner; self._expected_workers[execution_id] = worker
    def resolve(self, execution_id, system, capability):
        with self._lock:
            worker = self._worker_for(capability)
            execution = self._lookup(execution_id) if worker is not None else None
            owner = self._owners.get(execution_id)
            if (execution is None or owner is None or execution.worker_id != worker
                or self._expected_workers.get(execution_id) != worker or execution.status != "RUNNING"
                or execution.cancel_requested or not self._session_valid(owner)):
                raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            return self._vault.get(execution_id, owner, system)
    def sweep(self):
        with self._lock:
            removed = 0
            for execution_id, owner in list(self._owners.items()):
                execution = self._lookup(execution_id)
                expected = self._expected_workers.get(execution_id)
                invalid = execution is not None and (execution.status not in {"QUEUED", "RUNNING"} or execution.cancel_requested
                    or (execution.worker_id is not None and execution.worker_id != expected))
                if expected not in self._workers or invalid or not self._session_valid(owner) or not self._vault.contains(execution_id, owner):
                    self.revoke(execution_id); removed += 1
            return removed
    def revoke(self, execution_id):
        with self._lock:
            self._owners.pop(execution_id, None); self._expected_workers.pop(execution_id, None); self._vault.revoke(execution_id)
    def release(self, execution_id, capability):
        with self._lock:
            worker = self._worker_for(capability); execution = self._lookup(execution_id) if worker is not None else None
            if execution is None or execution.worker_id != worker: raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            self.revoke(execution_id)


def _lookup_execution(execution_id):
    from app.database import SessionLocal
    from app.models import Execution
    with SessionLocal() as db:
        return db.get(Execution, execution_id)


worker_channel = WorkerCredentialChannel(vault=credential_vault,
    lookup_execution=_lookup_execution, session_valid=lambda owner: resolve_session(owner) is not None)
