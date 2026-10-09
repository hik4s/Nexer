"""Credential references backed by the operating system credential store."""

import keyring


class CredentialResolutionError(RuntimeError):
    """Raised when a credential reference cannot be resolved safely."""


class KeyringCredentialProvider:
    SERVICE_NAME = "Nexer"

    def get(self, reference: str) -> str:
        if not isinstance(reference, str) or not reference.strip():
            raise CredentialResolutionError("INVALID_CREDENTIAL_REFERENCE")

        try:
            value = keyring.get_password(self.SERVICE_NAME, reference)
        except Exception as exc:
            raise CredentialResolutionError("CREDENTIAL_STORE_UNAVAILABLE") from exc

        if value is None:
            raise CredentialResolutionError("CREDENTIAL_NOT_FOUND")

        return value
