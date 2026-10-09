"""Fail-closed corporate context policy, independent from automation recipes."""
from corporate_auth import get_login_definition, validate_corporate_url


class CorporateBrowserPolicy:
    def __init__(self, system, *, authorize):
        get_login_definition(system)
        if not callable(authorize):
            raise RuntimeError("CORPORATE_CONTEXT_UNAVAILABLE")
        self.system = system
        self._authorize = authorize
        self._context = None
        self._main_page = None
        self._revoked = False

    def install(self, context):
        if self._context is not None:
            raise RuntimeError("CORPORATE_CONTEXT_UNAVAILABLE")
        self._context = context
        try:
            if context.pages:
                raise RuntimeError()
            context.route("**/*", self._request)
            context.route_web_socket("**/*", self._websocket)
            context.on("page", self._page)
        except Exception:
            self._revoke()
            raise RuntimeError("CORPORATE_CONTEXT_UNAVAILABLE") from None

    def check(self):
        try:
            if self._revoked:
                raise RuntimeError()
            self._authorize()
        except Exception:
            self._revoke()
            raise RuntimeError("CORPORATE_CONTEXT_REVOKED") from None

    def _revoke(self):
        self._revoked = True
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass

    def _page(self, page):
        if self._main_page is None and not self._revoked:
            self._main_page = page
        else:
            self._revoke()

    def _websocket(self, socket):
        # The installed sync WebSocket callback runs on the dispatcher greenlet.
        # Calling sync close here deadlocks. Never connect_to_server; revoke
        # now and close from the next outer worker/policy check instead.
        self._revoked = True

    def _request(self, route):
        response = None
        try:
            self.check()
            request = route.request
            validate_corporate_url(self.system, request.url)
            if request.resource_type == "document" and request.frame.parent_frame is not None:
                raise RuntimeError()
            # continue_ may follow redirects without a new policy callback.
            # Do not follow HTTP redirects, even to another permitted path.
            response = route.fetch(max_redirects=0, max_retries=0, timeout=5000)
            if 300 <= response.status < 400 and response.status != 304:
                raise RuntimeError()
            self.check()
            headers = dict(getattr(response, "headers", {}))
            restrictions = (
                "frame-src 'none'; child-src 'none'; worker-src 'none'; "
                "object-src 'none'; base-uri 'none'; form-action "
                + get_login_definition(self.system).login_url.split("#")[0])
            existing = headers.get("content-security-policy")
            headers["content-security-policy"] = (
                existing + ", " + restrictions if existing else restrictions)
            route.fulfill(response=response, headers=headers)
        except Exception:
            self._revoked = True
            try:
                route.abort("blockedbyclient")
            except Exception:
                pass
            self._revoke()
        finally:
            if response is not None:
                try:
                    response.dispose()
                except Exception:
                    pass
