"""Authenticated, execution-bound access; no durable capability or credentials."""
import hmac
from threading import RLock
from app.security import credential_vault, resolve_session


class WorkerCredentialChannel:
    def __init__(self, *, vault, lookup_execution, session_valid):
        self._vault = vault
        self._lookup = lookup_execution
        self._session_valid = session_valid
        self._lock = RLock()
        self._worker_id = None
        self._capability = None
        self._owners = {}

    def __repr__(self):
        return "WorkerCredentialChannel()"

    def configure(self, worker_id, capability):
        if not worker_id or not capability:
            raise ValueError("INVALID_WORKER_CHANNEL")
        with self._lock:
            for execution_id in list(self._owners):
                self._vault.revoke(execution_id)
            self._owners.clear()
            self._worker_id = worker_id
            self._capability = capability

    def authorized(self, capability):
        with self._lock:
            return bool(isinstance(capability, str) and self._capability
                and hmac.compare_digest(capability.encode(), self._capability.encode()))

    def current_worker_id(self):
        with self._lock:
            if not self._worker_id or not self._capability:
                raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            return self._worker_id

    def bind(self, execution_id, owner, *, expected_worker_id=None):
        with self._lock:
            if expected_worker_id is not None and expected_worker_id != self._worker_id:
                raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            if execution_id in self._owners:
                raise RuntimeError("CREDENTIALS_ALREADY_BOUND")
            self._owners[execution_id] = owner

    def resolve(self, execution_id, system, capability):
        with self._lock:
            execution = self._lookup(execution_id) if self.authorized(capability) else None
            owner = self._owners.get(execution_id)
            if (execution is None or owner is None
                or execution.worker_id != self._worker_id or execution.status != "RUNNING"
                or execution.cancel_requested or not self._session_valid(owner)):
                raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            return self._vault.get(execution_id, owner, system)

    def sweep(self):
        """Remove obsolete bindings using channel -> session -> vault lock order."""
        with self._lock:
            removed = 0
            for execution_id, owner in list(self._owners.items()):
                execution = self._lookup(execution_id)
                # A binding is installed before the publishing commit; a
                # missing row may be an in-flight submission, not deletion.
                # Its session/vault lifetime still bounds retention.
                invalid_execution = execution is not None and (
                    execution.status not in {"QUEUED", "RUNNING"}
                    or execution.cancel_requested
                    or (execution.status == "RUNNING"
                        and execution.worker_id != self._worker_id))
                if (invalid_execution
                    or not self._session_valid(owner)
                    or not self._vault.contains(execution_id, owner)):
                    self.revoke(execution_id)
                    removed += 1
            return removed

    def revoke(self, execution_id):
        with self._lock:
            self._owners.pop(execution_id, None)
            self._vault.revoke(execution_id)

    def release(self, execution_id, capability):
        with self._lock:
            execution = self._lookup(execution_id) if self.authorized(capability) else None
            if execution is None or execution.worker_id != self._worker_id:
                raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            self.revoke(execution_id)


def _lookup_execution(execution_id):
    from app.database import SessionLocal
    from app.models import Execution
    with SessionLocal() as db:
        return db.get(Execution, execution_id)


worker_channel = WorkerCredentialChannel(vault=credential_vault,
    lookup_execution=_lookup_execution, session_valid=lambda owner: resolve_session(owner) is not None)
