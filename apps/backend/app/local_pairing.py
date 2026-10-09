"""One-time local pairing; codes are never returned by an HTTP endpoint."""
import hashlib
import hmac
import secrets
from threading import RLock
from time import monotonic


class PairingAuthority:
    def __init__(self, *, clock=monotonic):
        self._clock = clock
        self._lock = RLock()
        self._digest = None
        self._expires = 0
        self._attempts = 0

    def __repr__(self):
        return "PairingAuthority()"

    def issue(self, ttl_seconds=300):
        if type(ttl_seconds) is not int or not 0 < ttl_seconds <= 300:
            raise ValueError("INVALID_PAIRING_TTL")
        code = secrets.token_urlsafe(32)
        with self._lock:
            self._digest = hashlib.sha256(code.encode()).digest()
            self._expires = self._clock() + ttl_seconds
            self._attempts = 0
        return code

    def consume(self, code):
        with self._lock:
            if self._digest is None or self._clock() >= self._expires:
                self._digest = None
                return False
            self._attempts += 1
            candidate = hashlib.sha256(code.encode()).digest() if isinstance(code, str) else b""
            accepted = hmac.compare_digest(candidate, self._digest)
            if accepted or self._attempts >= 5:
                self._digest = None
            return accepted


pairing_authority = PairingAuthority()
