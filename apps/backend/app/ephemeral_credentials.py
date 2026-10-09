"""Process-local credentials. No persistence, logging or secret-bearing repr."""

from copy import deepcopy
from math import isfinite
from threading import RLock
from time import monotonic


class EphemeralCredentialVault:
    def __init__(self, *, clock=monotonic, capacity=128):
        if type(capacity) is not int or capacity < 1:
            raise ValueError("INVALID_CREDENTIAL_CAPACITY")
        self._capacity = capacity
        self._clock = clock
        self._lock = RLock()
        self._records = {}

    def __repr__(self):
        return "EphemeralCredentialVault()"

    def put(self, execution_id, owner, systems, *, ttl_seconds):
        if (
            type(execution_id) is not int or execution_id <= 0
            or not isinstance(owner, str) or not owner
            or type(ttl_seconds) not in (int, float)
            or not isfinite(ttl_seconds) or not 0 < ttl_seconds <= 3600
            or not isinstance(systems, dict) or not systems
            or not set(systems).issubset({"SGIND", "IQOS"})
        ):
            raise ValueError("INVALID_CREDENTIAL_PAYLOAD")
        for values in systems.values():
            if (
                not isinstance(values, dict)
                or set(values) != {"username", "password"}
                or any(not isinstance(v, str) or not v or len(v) > 1024 for v in values.values())
            ):
                raise ValueError("INVALID_CREDENTIAL_PAYLOAD")
        with self._lock:
            self._purge_expired()
            if execution_id in self._records:
                raise RuntimeError("CREDENTIALS_ALREADY_BOUND")
            if len(self._records) >= self._capacity:
                raise RuntimeError("CREDENTIAL_CAPACITY_EXCEEDED")
            self._records[execution_id] = (
                owner, self._clock() + ttl_seconds, deepcopy(systems)
            )

    def get(self, execution_id, owner, system):
        with self._lock:
            self._purge_expired()
            record = self._records.get(execution_id)
            if record is None or record[0] != owner or system not in record[2]:
                raise RuntimeError("CREDENTIALS_UNAVAILABLE")
            return dict(record[2][system])

    def contains(self, execution_id, owner):
        """Check lifetime without copying or exposing credentials."""
        with self._lock:
            self._purge_expired()
            record = self._records.get(execution_id)
            return record is not None and record[0] == owner

    def revoke(self, execution_id):
        with self._lock:
            self._drop(execution_id)

    def revoke_owner(self, owner):
        with self._lock:
            for execution_id, record in list(self._records.items()):
                if record[0] == owner:
                    self._drop(execution_id)

    def purge_expired(self):
        with self._lock:
            before = len(self._records)
            self._purge_expired()
            return before - len(self._records)

    def _purge_expired(self):
        now = self._clock()
        for execution_id, record in list(self._records.items()):
            if record[1] <= now:
                self._drop(execution_id)

    def _drop(self, execution_id):
        record = self._records.pop(execution_id, None)
        if record is not None:
            for values in record[2].values():
                values.clear()
            record[2].clear()
