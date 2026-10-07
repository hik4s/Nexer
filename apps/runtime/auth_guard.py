class AuthenticationRequired(RuntimeError):
    """Raised when an authenticated session cannot be restored safely."""


class AuthenticationGuard:
    def __init__(self, *, login_selectors: list[str], renew=None):
        if not login_selectors:
            raise ValueError("login_selectors must not be empty")

        self.login_selectors = tuple(login_selectors)
        self.renew = renew
        self._renew_attempted = False

    def ensure_authenticated(self, page):
        if not self._login_detected(page):
            return page

        if self._renew_attempted or self.renew is None:
            raise AuthenticationRequired("AUTHENTICATION_REQUIRED")

        self._renew_attempted = True

        try:
            renewed = bool(self.renew(page))
        except Exception as exc:
            raise AuthenticationRequired("AUTHENTICATION_REQUIRED") from None

        if not renewed:
            raise AuthenticationRequired("AUTHENTICATION_REQUIRED")

        return page

    def _login_detected(self, page) -> bool:
        for selector in self.login_selectors:
            try:
                if page.locator(selector).is_visible():
                    return True
            except Exception:
                continue
        return False
