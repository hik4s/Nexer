"""Local backend authentication primitives; no plaintext password storage."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass

PASSWORD_ITERATIONS = 310_000
SESSION_COOKIE_NAME = "nexer_session"
from app.ephemeral_credentials import EphemeralCredentialVault
credential_vault = EphemeralCredentialVault()
_sessions: dict[str, tuple[str, float]] = {}
_sessions_lock = threading.RLock()


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    if not isinstance(password, str) or len(password) < 12:
        raise ValueError("PASSWORD_MUST_HAVE_AT_LEAST_12_CHARACTERS")
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), actual_salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${actual_salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_hex, digest_hex = encoded.split("$", 3)
        iterations = int(iterations_text)
        if algorithm != "pbkdf2_sha256" or not 100_000 <= iterations <= 1_000_000:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        if len(salt) < 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError):
        return False


def is_auth_configured(username: str | None, password_hash: str | None) -> bool:
    if not username or not username.strip() or not password_hash:
        return False
    try:
        algorithm, iterations_text, salt_hex, digest_hex = password_hash.split("$", 3)
        iterations = int(iterations_text)
        return (
            algorithm == "pbkdf2_sha256"
            and 100_000 <= iterations <= 1_000_000
            and len(bytes.fromhex(salt_hex)) >= 16
            and len(bytes.fromhex(digest_hex)) == 32
        )
    except (TypeError, ValueError):
        return False


def authenticate(username: str, password: str, configured_username: str | None,
                 configured_hash: str | None) -> bool:
    if not configured_username or not configured_hash:
        return False
    username_matches = hmac.compare_digest(username.strip(), configured_username)
    password_matches = verify_password(password, configured_hash)
    return username_matches and password_matches


def issue_session(username: str, ttl_seconds: int) -> str:
    token = secrets.token_urlsafe(32)
    with _sessions_lock:
        _sessions[token] = (username, time.monotonic() + ttl_seconds)
    return token


def resolve_session(token: str | None) -> str | None:
    if not token:
        return None
    now = time.monotonic()
    with _sessions_lock:
        record = _sessions.get(token)
        if record is None:
            return None
        username, expires_at = record
        if expires_at <= now:
            _sessions.pop(token, None)
            credential_vault.revoke_owner(token)
            return None
        return username


def revoke_session(token: str | None) -> None:
    if token:
        with _sessions_lock:
            _sessions.pop(token, None)
            credential_vault.revoke_owner(token)

def sweep_sessions():
    with _sessions_lock:
        now = time.monotonic()
        for token, record in list(_sessions.items()):
            if record[1] <= now:
                revoke_session(token)
    credential_vault.purge_expired()


def put_session_credentials(execution_id: int, owner: str | None, systems: dict) -> None:
    """Serialize storing with logout; never give credentials a longer session lifetime."""
    with _sessions_lock:
        record = _sessions.get(owner) if owner else None
        remaining = record[1] - time.monotonic() if record else 0
        if remaining <= 0:
            if owner:
                revoke_session(owner)
            raise RuntimeError("CREDENTIALS_UNAVAILABLE")
        credential_vault.put(execution_id, owner, systems,
                             ttl_seconds=min(3600, remaining))
