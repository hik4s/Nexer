class AuthenticationRequired(RuntimeError):
    """Raised when an authenticated session cannot be restored safely."""


class AuthenticationRenewalError(RuntimeError):
    """Raised when a generic form login cannot be completed safely."""


class FormAuthenticationRenewal:
    def __init__(
        self,
        *,
        login_url: str,
        username_selector: str,
        password_selector: str,
        submit_selector: str,
        success_selector: str,
        username_ref: str,
        password_ref: str,
        credential_provider,
        timeout: int = 30000,
    ):
        self.login_url = login_url
        self.username_selector = username_selector
        self.password_selector = password_selector
        self.submit_selector = submit_selector
        self.success_selector = success_selector
        self.username_ref = username_ref
        self.password_ref = password_ref
        self.credential_provider = credential_provider
        self.timeout = timeout

    def __call__(self, page) -> bool:
        try:
            username = self.credential_provider.get(self.username_ref)
            password = self.credential_provider.get(self.password_ref)
        except Exception:
            raise AuthenticationRenewalError("AUTHENTICATION_RENEWAL_FAILED") from None

        page.goto(
            self.login_url,
            wait_until="domcontentloaded",
        )
        page.locator(self.username_selector).fill(username)
        page.locator(self.password_selector).fill(password)
        page.locator(self.submit_selector).click()
        page.locator(self.success_selector).wait_for(
            state="visible",
            timeout=self.timeout,
        )
        return True


def build_auth_guard(authentication: dict | None, *, credential_provider):
    if authentication is None:
        return None

    login_selectors = authentication.get("login_selectors")
    if not isinstance(login_selectors, list) or not login_selectors:
        raise ValueError("AUTH_LOGIN_SELECTORS_REQUIRED")

    renewal_config = authentication.get("renewal")
    if renewal_config is None:
        return AuthenticationGuard(login_selectors=login_selectors)

    if not isinstance(renewal_config, dict):
        raise ValueError("AUTH_RENEWAL_CONFIG_INVALID")

    required = (
        "login_url",
        "username_selector",
        "password_selector",
        "submit_selector",
        "success_selector",
        "username_ref",
        "password_ref",
    )
    if any(not isinstance(renewal_config.get(key), str) or not renewal_config[key].strip() for key in required):
        raise ValueError("AUTH_RENEWAL_CONFIG_INVALID")

    renewal = FormAuthenticationRenewal(
        login_url=renewal_config["login_url"],
        username_selector=renewal_config["username_selector"],
        password_selector=renewal_config["password_selector"],
        submit_selector=renewal_config["submit_selector"],
        success_selector=renewal_config["success_selector"],
        username_ref=renewal_config["username_ref"],
        password_ref=renewal_config["password_ref"],
        credential_provider=credential_provider,
    )
    return AuthenticationGuard(
        login_selectors=login_selectors,
        renew=renewal,
    )


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
