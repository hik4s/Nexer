"""Loopback-only worker channel. Capability is supplied through inherited stdin."""
import json
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class ExecutionCredentialClient:
    def __init__(self, base_url, capability):
        try:
            parsed = urlsplit(base_url)
            valid = (parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
                and parsed.port is not None and parsed.username is None
                and parsed.password is None and not parsed.path and not parsed.query and not parsed.fragment)
        except (ValueError, TypeError):
            valid = False
        if not valid or not isinstance(capability, str) or not capability:
            raise ValueError("INVALID_WORKER_CHANNEL")
        self._base_url = base_url
        self._capability = capability
        self._opener = build_opener(ProxyHandler({}), NoRedirect())

    def __repr__(self):
        return "ExecutionCredentialClient()"

    def _request(self, path, method="GET"):
        request = Request(self._base_url + path, method=method, headers={
            "x-nexer-worker": self._capability,
            "Origin": "http://127.0.0.1:5173", "Accept": "application/json"})
        try:
            with self._opener.open(request, timeout=5) as response:
                raw = response.read(8193)
                if len(raw) > 8192:
                    raise RuntimeError()
                return json.loads(raw)
        except Exception:
            raise RuntimeError("CREDENTIALS_UNAVAILABLE") from None

    def resolve(self, execution_id, system):
        if type(execution_id) is not int or execution_id <= 0 or system not in {"SGIND", "IQOS"}:
            raise RuntimeError("CREDENTIALS_UNAVAILABLE")
        result = self._request(f"/internal/credentials/{execution_id}/{system}")
        if (not isinstance(result, dict) or set(result) != {"username", "password"}
            or any(not isinstance(value, str) or not value or len(value) > 1024 for value in result.values())):
            raise RuntimeError("CREDENTIALS_UNAVAILABLE")
        return result

    def release(self, execution_id):
        if type(execution_id) is not int or execution_id <= 0:
            raise RuntimeError("CREDENTIALS_UNAVAILABLE")
        return self._request(f"/internal/credentials/{execution_id}/release", method="POST")
