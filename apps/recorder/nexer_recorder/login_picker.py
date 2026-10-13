"""Identify login locations in a fresh browser, never collect field values."""
import re
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

SCRIPT = Path(__file__).with_name("login_capture.js")
CORPORATE_HOST = "indicadoresenergisaess.scl.corp"


def pick_login(configuration, stop_event, on_target, *, headless=False, timeout=300):
    url = configuration["login_url"]
    parsed = urlsplit(url)
    if parsed.hostname and parsed.hostname.lower().rstrip(".") == CORPORATE_HOST:
        raise RuntimeError("CORPORATE_AUTH_NOT_VALIDATED")
    initial_origin = (parsed.scheme, parsed.hostname, parsed.port)
    targets = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=headless, args=["--disable-features=msDownloadsHub"])
        try:
            context = browser.new_context(accept_downloads=False, service_workers="block")
            page_count = []
            def new_page(opened):
                page_count.append(True)
                if len(page_count) > 1: stop_event.set()
            context.on("page", new_page)
            def route(request_route):
                target = urlsplit(request_route.request.url)
                if target.username or target.password or request_route.request.method not in {"GET", "HEAD"} or (target.scheme, target.hostname, target.port) != initial_origin:
                    request_route.abort(); return
                response = request_route.fetch(max_redirects=0, timeout=10000)
                if 300 <= response.status < 400: request_route.abort()
                else: request_route.fulfill(response=response)
            context.route("**/*", route)
            context.route_web_socket("**/*", lambda socket: None)
            def accept(source, event):
                if not isinstance(event, dict) or set(event) != {"field", "selector", "frames"} or event["field"] not in {"username_target", "password_target", "submit_target"}: return
                if not isinstance(event["selector"], str) or not event["selector"] or len(event["selector"]) > 1000: return
                if not isinstance(event["frames"], list) or len(event["frames"]) > 8 or any(not isinstance(frame, str) or not frame or len(frame) > 1000 for frame in event["frames"]): return
                token = r"[a-z][a-z0-9-]*:nth-of-type\([1-9][0-9]*\)"
                pattern = token + r"(?: (?:> )?" + token + r")*"
                if any(not re.fullmatch(pattern, selector) for selector in [event["selector"], *event["frames"]]): return
                target = {"selector": event["selector"], "frames": event["frames"]}
                targets[event["field"]] = target
                on_target(event["field"], target)
            context.expose_binding("nexerLoginTarget", accept)
            context.add_init_script(SCRIPT.read_text(encoding="utf-8"))
            page = context.new_page(); page.goto(url, wait_until="domcontentloaded", timeout=15000)
            deadline = monotonic() + timeout
            while not stop_event.is_set() and monotonic() < deadline and not page.is_closed():
                if len(targets) == 3: return targets
                page.wait_for_timeout(100)
            raise RuntimeError("LOGIN_PICKER_CANCELLED" if stop_event.is_set() or page.is_closed() else "LOGIN_PICKER_TIMEOUT")
        finally: browser.close()
