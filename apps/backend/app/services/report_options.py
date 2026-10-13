"""Ephemeral option catalogs from a fresh, read-only loopback browser."""
from contextlib import contextmanager
import re
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from recipe import validate_recipe
from resolver import VariableResolver


class ReportOptionsError(ValueError):
    pass


READINESS_SCRIPT = """(() => {
    const timers = new Set(); let requests = 0;
    const nativeTimeout = window.setTimeout.bind(window);
    const nativeClear = window.clearTimeout.bind(window);
    window.setTimeout = (handler, delay, ...args) => {
        let id;
        id = nativeTimeout(typeof handler === 'function' ? () => {
            timers.delete(id); handler.apply(window, args);
        } : handler, delay, ...args);
        timers.add(id);
        // Keep string handlers native so the site's CSP still applies.
        if (typeof handler !== 'function') nativeTimeout(() => {timers.delete(id);}, delay);
        return id;
    };
    window.clearTimeout = id => {timers.delete(id); nativeClear(id);};
    const nativeFetch = window.fetch.bind(window);
    window.fetch = (...args) => {
        requests++;
        try {return nativeFetch(...args).finally(() => {requests--;});}
        catch (error) {requests--; throw error;}
    };
    const nativeSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function(...args) {
        requests++;
        let done = false;
        const finish = () => {if (!done) {done = true; requests--;}};
        this.addEventListener('loadend', finish, {once: true});
        try {return nativeSend.apply(this, args);} catch (error) {finish(); throw error;}
    };
    Object.defineProperty(window, '__nexerOptionsPending', {get: () => timers.size + requests});
})();"""


def _settle_form(page, locator):
    # Track pending site timers/requests as well as DOM quiet. A long-running
    # update fails closed instead of returning an earlier option catalog.
    locator.evaluate("""element => new Promise((resolve, reject) => {
        const root = element.ownerDocument.documentElement;
        const owner = element.ownerDocument.defaultView;
        const started = performance.now(); let changed = started;
        const observer = new MutationObserver(() => {changed = performance.now();});
        observer.observe(root, {subtree: true, childList: true, attributes: true, characterData: true});
        const timer = setInterval(() => {
            const now = performance.now();
            if (now - started >= 3000) {clearInterval(timer); observer.disconnect(); reject(new Error('OPTIONS_NOT_READY'));}
            else if (now - started >= 500 && now - changed >= 300 && owner.__nexerOptionsPending === 0) {
                clearInterval(timer); observer.disconnect(); resolve();
            }
        }, 50);
    })""")
    page.wait_for_load_state("networkidle", timeout=3000)


@contextmanager
def _option_page(origin, playwright_factory, page_factory):
    if page_factory is not None:
        page = page_factory()
        try:
            page.context.set_default_timeout(1500)
            page.context.add_init_script(READINESS_SCRIPT)
            yield page
        finally: page.close()
        return
    with playwright_factory() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True, args=["--disable-features=msDownloadsHub"])
        try:
            context = browser.new_context(accept_downloads=False, service_workers="block")
            context.set_default_timeout(1500); context.add_init_script(READINESS_SCRIPT)
            def route(request_route, _request=None):
                target = urlsplit(request_route.request.url)
                if request_route.request.method not in {"GET", "HEAD"} or (target.scheme, target.hostname, target.port) != origin:
                    request_route.abort(); return
                response = request_route.fetch(max_redirects=0, timeout=10000)
                if 300 <= response.status < 400: request_route.abort()
                else: request_route.fulfill(response=response)
            context.route("**/*", route); context.route_web_socket("**/*", lambda socket: None)
            yield context.new_page()
        finally: browser.close()


def read_options(recipe, inputs, *, playwright_factory=sync_playwright, page_factory=None):
    recipe = validate_recipe(recipe)
    if recipe.get("authentication") or any(item.get("secret") for item in recipe.get("variables", {}).values()):
        raise ReportOptionsError("OPTIONS_CREDENTIALS_UNAVAILABLE")
    resolver = VariableResolver(declarations=recipe.get("variables", {}), values=inputs)
    try:
        initial = next(step for step in recipe["steps"] if step["action"] == "navigate")
        url = resolver.resolve(initial["url"])
        parsed = urlsplit(url)
        origin = (parsed.scheme, parsed.hostname, parsed.port)
        if parsed.username or parsed.password or parsed.query or parsed.fragment: raise ValueError()
        if page_factory is None and (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}): raise ValueError()
    except Exception:
        raise ReportOptionsError("OPTIONS_LOCAL_PAGE_REQUIRED") from None
    sources = {}
    tab = 0
    for step in recipe["steps"]:
        if step["action"] == "switch_tab":
            tab = step["index"]
        match = re.fullmatch(r"{{\s*(\w+)\s*}}", str(step.get("value", "")))
        if match and step["action"] in {"select", "choose", "choose_radio"}:
            sources.setdefault(match[1], (step, tab))
    if len(sources) > 100:
        raise ReportOptionsError("OPTIONS_TOO_MANY_FIELDS")
    fields = {}
    deadline = time.monotonic() + 20
    try:
        with _option_page(origin, playwright_factory, page_factory) as page:
            page.goto(url, wait_until="domcontentloaded", timeout=10000)
            _settle_form(page, page.locator("html"))
            # Apply supplied initial-form filters only. No recorded clicks, downloads,
            # authentication, submissions or popup-opening actions are replayed here.
            tab = 0
            for step in recipe["steps"]:
                if time.monotonic() > deadline:
                    break
                if step["action"] == "switch_tab":
                    tab = step["index"]
                if tab or step["action"] not in {"fill", "select", "check", "set_value", "choose_radio"}:
                    continue
                match = re.fullmatch(r"{{\s*(\w+)\s*}}", str(step.get("value", "")))
                if not match or match[1] not in inputs:
                    continue
                try:
                    value = resolver.resolve(step["value"])
                    scope = page
                    for selector in step.get("frames", []):
                        scope = scope.frame_locator(resolver.resolve(selector))
                    locator = scope.locator(resolver.resolve(step["selector"]))
                    if locator.locator('xpath=ancestor-or-self::form').locator('input[type="password"]').count() or locator.get_attribute("type") == "password":
                        raise ReportOptionsError("OPTIONS_CREDENTIALS_UNAVAILABLE")
                    if step["action"] == "fill":
                        locator.fill(str(value))
                        locator.dispatch_event("change")
                    elif step["action"] == "check":
                        if type(value) is not bool:
                            raise ValueError()
                        locator.set_checked(value)
                    elif step["action"] == "set_value":
                        locator.evaluate("(element, value) => {element.value = value; element.dispatchEvent(new Event('input', {bubbles: true})); element.dispatchEvent(new Event('change', {bubbles: true}));}", str(value))
                    elif step["action"] == "choose_radio":
                        radios = locator.locator('input[type="radio"]')
                        indices = radios.evaluate_all("""(elements, requested) => {
                            const groups = [];
                            return elements.flatMap((element, index) => {
                                const identity = element.name || element;
                                if (!groups.includes(identity)) groups.push(identity);
                                return groups.indexOf(identity) === requested.group && element.value === requested.value ? [index] : [];
                            });
                        }""", {"group": step.get("group_index", 0), "value": str(value)})
                        if len(indices) != 1:
                            raise ValueError()
                        radios.nth(indices[0]).check()
                    else:
                        values = value if isinstance(value, list) else [str(value)]
                        available = locator.locator("option:not([disabled])").evaluate_all("elements => elements.filter(element => !element.closest('optgroup[disabled]')).map(element => element.value)")
                        if all(item in available for item in values):
                            locator.select_option(values)
                    _settle_form(page, locator)
                except ReportOptionsError:
                    raise
                except Exception:
                    raise ReportOptionsError("OPTIONS_FILTER_INVALID") from None
            settled_documents = set()
            for name, (step, source_tab) in sources.items():
                try:
                    if source_tab or time.monotonic() > deadline:
                        raise ValueError()
                    scope = page
                    for selector in step.get("frames", []):
                        scope = scope.frame_locator(resolver.resolve(selector))
                    locator = scope.locator(resolver.resolve(step["selector"]))
                    document_key = tuple(step.get("frames", []))
                    if document_key not in settled_documents:
                        _settle_form(page, locator)
                        settled_documents.add(document_key)
                    if step["action"] == "select":
                        options = locator.locator("option").evaluate_all("elements => elements.map(element => ({value: element.value, label: element.label, disabled: element.disabled || Boolean(element.closest('optgroup[disabled]'))}))")
                    elif step["action"] == "choose":
                        options = locator.get_by_role("option", include_hidden=True).evaluate_all("elements => elements.map(element => ({value: element.getAttribute('aria-label') || element.textContent.trim(), label: element.getAttribute('aria-label') || element.textContent.trim(), disabled: element.getAttribute('aria-disabled') === 'true'}))")
                    else:
                        options = locator.locator('input[type="radio"]').evaluate_all("""(elements, group) => {
                            const groups = [];
                            return elements.flatMap(element => {
                                const identity = element.name || element;
                                if (!groups.includes(identity)) groups.push(identity);
                                if (groups.indexOf(identity) !== group) return [];
                                const label = [...(element.labels || [])].map(label => label.textContent.trim()).join(' ') || element.value;
                                return [{value: element.value, label, disabled: element.disabled}];
                            });
                        }""", step.get("group_index", 0))
                    if len(options) > 500 or any(len(item["value"]) > 2000 or len(item["label"]) > 2000 for item in options):
                        raise ValueError()
                    fields[name] = {"options": options, "error": None}
                except Exception:
                    fields[name] = {"options": [], "error": "OPTIONS_FIELD_UNAVAILABLE"}
    except ReportOptionsError:
        raise
    except Exception:
        raise ReportOptionsError("OPTIONS_PAGE_UNAVAILABLE") from None
    return {"fields": fields}
