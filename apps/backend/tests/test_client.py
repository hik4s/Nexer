"""Explicit authenticated transport for business-contract tests only."""
from fastapi.testclient import TestClient as NativeTestClient
from app.security import SESSION_COOKIE_NAME, issue_session


class AuthenticatedTestClient(NativeTestClient):
    def __init__(self, app, **kwargs):
        kwargs.setdefault("base_url", "http://127.0.0.1:8000")
        kwargs.setdefault("client", ("127.0.0.1", 50000))
        kwargs.setdefault("headers", {"Origin": "http://127.0.0.1:5173"})
        super().__init__(app, **kwargs)
        self.cookies.set(SESSION_COOKIE_NAME, issue_session("test-operator", 600))
