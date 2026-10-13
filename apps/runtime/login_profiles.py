"""Versioned site login in monitored ephemeral contexts. No secret persistence."""
from time import monotonic
from urllib.parse import urlsplit
from corporate_browser import CorporateBrowserPolicy


def profile_key(profile_id, version):
    if type(profile_id) is not int or profile_id < 1 or type(version) is not int or version < 1:
        raise RuntimeError("LOGIN_PROFILE_INVALID")
    return f"profile-{profile_id}-v{version}"


def _origin(value):
    parsed = urlsplit(value)
    if parsed.username or parsed.password or not parsed.hostname or parsed.hostname.lower().rstrip(".") == "indicadoresenergisaess.scl.corp":
        raise ValueError()
    if parsed.scheme != "https" and not (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}): raise ValueError()
    return parsed.scheme, parsed.hostname.lower().rstrip("."), parsed.port or (443 if parsed.scheme == "https" else 80)


class LoginBrowserPolicy(CorporateBrowserPolicy):
    def __init__(self, configuration, *, authorize):
        if not callable(authorize): raise RuntimeError("LOGIN_CONTEXT_UNAVAILABLE")
        try:
            self._origins = {_origin(value) for value in configuration["allowed_origins"]}
            self._login_origin = _origin(configuration["login_url"])
            if self._login_origin not in self._origins: raise ValueError()
        except Exception: raise RuntimeError("LOGIN_PROFILE_INVALID") from None
        self._authorize = authorize; self._context = None; self._main_page = None; self._revoked = False
        self.configuration = configuration
        self.allowed_methods = None
    def validate_url(self, url):
        try:
            if _origin(url) not in self._origins: raise ValueError()
        except Exception: raise RuntimeError("LOGIN_DESTINATION_FORBIDDEN") from None
    def _request(self, route, _request=None):
        response = None
        try:
            self.check(); request = route.request; self.validate_url(request.url)
            if self.allowed_methods is not None and request.method not in self.allowed_methods: raise RuntimeError()
            if request.resource_type == "document" and request.frame.parent_frame is not None and _origin(request.url) != self._login_origin: raise RuntimeError()
            response = route.fetch(max_redirects=0, max_retries=0, timeout=5000)
            self.check()
            headers = dict(getattr(response, "headers", {}))
            origins = " ".join(self.configuration["allowed_origins"])
            restrictions = f"worker-src 'none'; object-src 'none'; base-uri 'none'; frame-src {origins}; form-action {origins}; connect-src {origins}"
            previous = headers.get("content-security-policy")
            headers["content-security-policy"] = previous + ", " + restrictions if previous else restrictions
            route.fulfill(response=response, headers=headers)
        except Exception:
            self._revoked = True
            try: route.abort("blockedbyclient")
            except Exception: pass
            self._revoke()
        finally:
            if response is not None:
                try: response.dispose()
                except Exception: pass


def target_locator(page, target):
    scope = page
    for selector in target.get("frames", []): scope = scope.frame_locator(selector)
    return scope.locator(target["selector"])

def target_visible(page, target):
    scope = page
    for selector in target.get("frames", []):
        if scope.locator(selector).count() == 0: return False
        scope = scope.frame_locator(selector)
    locator = scope.locator(target["selector"])
    return locator.count() > 0 and locator.is_visible()


def login_succeeded(page, configuration):
    page.corporate_policy.check()
    page.corporate_policy.validate_url(page.url)
    if password_visible(page, configuration): return False
    rule = configuration["success_rule"]
    if rule["kind"] == "url": return page.url == rule["url"]
    return target_visible(page, rule["target"])


def password_visible(page, configuration):
    target = configuration["password_target"]
    scope = page
    for selector in target.get("frames", []):
        if scope.locator(selector).count() == 0: return False
        scope = scope.frame_locator(selector)
    locator = scope.locator(target["selector"])
    return locator.count() > 0 and locator.get_attribute("type") == "password" and locator.is_visible()


def authenticate_profile(page, configuration, credentials, *, cancellation_requested):
    values = dict(credentials)
    try:
        page.corporate_policy.check()
        if cancellation_requested(): raise RuntimeError()
        page.goto(configuration["login_url"], wait_until="domcontentloaded", timeout=15000)
        page.corporate_policy.check()
        rule = configuration["success_rule"]
        if rule["kind"] == "url" and rule["url"] == configuration["login_url"]: raise RuntimeError()
        if rule["kind"] == "marker" and target_visible(page, rule["target"]): raise RuntimeError()
        username = target_locator(page, configuration["username_target"])
        password = target_locator(page, configuration["password_target"])
        if password.get_attribute("type") != "password": raise RuntimeError()
        if username.get_attribute("type") in {"password", "hidden", "file"}: raise RuntimeError()
        username.fill(values["username"], timeout=5000)
        page.corporate_policy.check()
        if cancellation_requested(): raise RuntimeError()
        password.fill(values["password"], timeout=5000)
        page.corporate_policy.check()
        target_locator(page, configuration["submit_target"]).click(timeout=5000)
        deadline = monotonic() + 15
        while monotonic() < deadline:
            page.corporate_policy.check()
            if cancellation_requested(): raise RuntimeError()
            if login_succeeded(page, configuration): return
            page.wait_for_timeout(100)
        raise RuntimeError()
    except Exception:
        raise RuntimeError("LOGIN_FAILED") from None
    finally: values.clear()


class LoginExecutionGuard:
    def __init__(self, configuration): self.configuration = configuration
    def ensure_authenticated(self, page):
        try:
            page.corporate_policy.check(); page.corporate_policy.validate_url(page.url)
            # After navigating to a report the login-success URL may differ;
            # returning to the login page or visible password always revokes.
            if password_visible(page, self.configuration): raise RuntimeError()
            if page.url == self.configuration["login_url"] and not login_succeeded(page, self.configuration): raise RuntimeError()
            return page
        except Exception:
            try: page.close()
            except Exception: pass
            raise RuntimeError("LOGIN_SESSION_REVOKED") from None
