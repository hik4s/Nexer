"""Trusted corporate destinations and login evidence, independent from recipes."""
from dataclasses import dataclass
from urllib.parse import urlsplit

SGIND_ORIGIN = "https://indicadoresenergisaess.scl.corp"


@dataclass(frozen=True)
class CorporateLoginDefinition:
    login_url: str
    home_url: str
    form_selector: str
    username_selector: str
    password_selector: str
    submit_selector: str
    home_selector: str = "app-home-page"


def get_login_definition(system):
    if system == "SGIND":
        application = "sgind"
        form = "form#idFormLogin"
    elif system == "IQOS":
        application = "iqos"
        form = 'form[name="form"]'
    else:
        raise RuntimeError("CORPORATE_DESTINATION_FORBIDDEN")
    return CorporateLoginDefinition(
        login_url=f"{SGIND_ORIGIN}/{application}/#/login",
        home_url=f"{SGIND_ORIGIN}/{application}/#/home",
        form_selector=form,
        username_selector=f'{form} input[name="cre_username"]',
        password_selector=f'{form} input[name="cre_password"][type="password"]',
        submit_selector=f'{form} button[type="submit"]',
    )


def validate_corporate_url(system, url):
    try:
        definition = get_login_definition(system)
        parsed = urlsplit(url)
        application_path = urlsplit(definition.login_url).path
        permitted = (
            isinstance(url, str)
            and parsed.scheme == "https"
            and parsed.hostname == "indicadoresenergisaess.scl.corp"
            and parsed.port in (None, 443)
            and parsed.username is None and parsed.password is None
            and parsed.path.startswith(application_path)
            and "%" not in parsed.path
            and not any(segment in (".", "..") for segment in parsed.path.split("/"))
            and "\\" not in url
            and not any(character.isspace() for character in url)
        )
    except (RuntimeError, TypeError, ValueError, AttributeError):
        permitted = False
    if not permitted:
        raise RuntimeError("CORPORATE_DESTINATION_FORBIDDEN")


def matches_authenticated_home(system, url, *, home_visible, login_form_present):
    """Evidence predicate; callers must obtain visibility from the live page."""
    try:
        validate_corporate_url(system, url)
        definition = get_login_definition(system)
    except RuntimeError:
        return False
    return (url == definition.home_url and home_visible is True
            and login_form_present is False)


def require_validated_adapter(system):
    # Login and home evidence are now known, including an anonymous Edge probe.
    # Worker login/context restrictions and credential lifecycle must be wired
    # and tested before enabling the end-to-end corporate execution flow.
    # Recipes cannot opt themselves into trusted credential access.
    raise RuntimeError("CORPORATE_AUTH_NOT_VALIDATED")


def authenticate_corporate(page, credential_client, execution_id, system, *,
                          timeout_ms=30000, cancellation_requested=None):
    """Login primitive for a restricted, fresh context owned by the caller.

    The caller must install context restrictions before invoking this function
    and close the context on failure. Production gates remain closed until the
    worker implements that contract. Recipes cannot supply login definitions.
    """
    import time
    from urllib.parse import urljoin

    values = None
    deadline = None

    def check_page():
        if cancellation_requested and cancellation_requested():
            raise RuntimeError()
        validate_corporate_url(system, page.url)

    def check_login_form():
        check_page()
        if page.url != definition.login_url:
            raise RuntimeError()
        form = page.locator(definition.form_selector)
        if form.count() != 1:
            raise RuntimeError()
        action = form.get_attribute("action")
        validate_corporate_url(system, urljoin(page.url, action or page.url))

    def resolve():
        nonlocal values
        if values is not None:
            values.clear()
        values = credential_client.resolve(execution_id, system)
        if (not isinstance(values, dict) or set(values) != {"username", "password"}
                or any(not isinstance(value, str) or not value or len(value) > 1024
                       for value in values.values())):
            raise RuntimeError()
        return values

    def remaining():
        milliseconds = int((deadline - time.monotonic()) * 1000)
        if milliseconds <= 0:
            raise RuntimeError()
        return milliseconds

    try:
        if type(timeout_ms) is not int or not 0 < timeout_ms <= 60000:
            raise RuntimeError()
        deadline = time.monotonic() + timeout_ms / 1000
        definition = get_login_definition(system)
        if cancellation_requested and cancellation_requested():
            raise RuntimeError()
        page.goto(definition.login_url, wait_until="domcontentloaded",
                  timeout=remaining())
        check_login_form()
        page.locator(definition.username_selector).fill(
            resolve()["username"], timeout=remaining())
        check_login_form()
        page.locator(definition.password_selector).fill(
            resolve()["password"], timeout=remaining())
        check_login_form()
        resolve()  # Confirm current reservation/TTL immediately before submit.
        values.clear()
        page.locator(definition.submit_selector).click(timeout=remaining())
        while True:
            check_page()
            resolve()  # Fail closed if session, reservation or credentials expire.
            values.clear()
            if matches_authenticated_home(
                    system, page.url,
                    home_visible=page.locator(definition.home_selector).is_visible(),
                    login_form_present=page.locator(definition.form_selector).count() != 0):
                return
            page.wait_for_timeout(min(100, remaining()))
    except Exception:
        raise RuntimeError("CORPORATE_LOGIN_FAILED") from None
    finally:
        if isinstance(values, dict):
            values.clear()
