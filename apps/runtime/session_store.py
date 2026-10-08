"""OS-backed storage for reusable Playwright authentication state."""

import json
import re

import keyring


_REFERENCE_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")


class SessionStateError(RuntimeError):
    """Raised when an authentication session state cannot be stored safely."""


class SessionStateStore:
    SERVICE_NAME = "RelatPy.Session"

    def save(self, reference: str, state: dict) -> None:
        _validate_reference(reference)
        _validate_state(state)

        payload = json.dumps(
            state,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

        try:
            keyring.set_password(self.SERVICE_NAME, reference, payload)
        except Exception:
            raise SessionStateError("SESSION_STORE_UNAVAILABLE") from None

    def load(self, reference: str) -> dict | None:
        _validate_reference(reference)

        try:
            payload = keyring.get_password(self.SERVICE_NAME, reference)
        except Exception:
            raise SessionStateError("SESSION_STORE_UNAVAILABLE") from None

        if payload is None:
            return None

        try:
            state = json.loads(payload)
        except (TypeError, ValueError):
            raise SessionStateError("INVALID_SESSION_STATE") from None

        _validate_state(state)
        return state

    def delete(self, reference: str) -> None:
        _validate_reference(reference)

        try:
            keyring.delete_password(self.SERVICE_NAME, reference)
        except keyring.errors.PasswordDeleteError:
            return
        except Exception:
            raise SessionStateError("SESSION_STORE_UNAVAILABLE") from None


def _validate_reference(reference: str) -> None:
    if not isinstance(reference, str) or not _REFERENCE_PATTERN.fullmatch(reference):
        raise SessionStateError("INVALID_SESSION_REFERENCE")


def _validate_state(state: dict) -> None:
    if not isinstance(state, dict):
        raise SessionStateError("INVALID_SESSION_STATE")

    cookies = state.get("cookies", [])
    origins = state.get("origins", [])

    if not isinstance(cookies, list) or not isinstance(origins, list):
        raise SessionStateError("INVALID_SESSION_STATE")
