"""Local, isolated headless selector probe. Never return DOM text, HTML or secrets."""
from time import monotonic
from urllib.parse import urlsplit
from site_urls import validate_site_url, site_origin


def probe(url: str, selector: str) -> dict:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

    allowed_url = validate_site_url(url)
    if not isinstance(selector, str) or not selector.strip() or len(selector) > 2048:
        raise ValueError("DEVELOPER_SELECTOR_INVALID")
    start = monotonic()
    result = {"mode": "headless", "status": "PAGE_UNAVAILABLE", "matches": 0,
              "visible": False, "enabled": False}
    # Every probe uses an independent context. No saved cookies, storage state,
    # screenshots, network traces, headers, credentials or download artifacts.
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            try:
                context = browser.new_context(accept_downloads=False, service_workers="block")
                page = context.new_page()
                page.goto(allowed_url, wait_until="domcontentloaded", timeout=12000)
                # Reject a redirect to a different origin, including SSO pages.
                if site_origin(page.url) != site_origin(allowed_url):
                    result["status"] = "CROSS_ORIGIN_REDIRECT"
                else:
                    target = page.locator(selector)
                    try:
                        target.first.wait_for(state="attached", timeout=3000)
                    except PlaywrightTimeoutError:
                        pass
                    matches = min(target.count(), 2)
                    result["matches"] = matches
                    if matches == 1:
                        result["status"] = "FOUND"
                        result["visible"] = target.is_visible()
                        result["enabled"] = target.is_enabled()
                    else:
                        result["status"] = "AMBIGUOUS" if matches > 1 else "NOT_FOUND"
                context.close()
            finally:
                browser.close()
    except Exception:
        # Never echo exception details or target URL; corporate URLs can contain
        # path segments that should not become logs or API responses.
        result["status"] = "PAGE_UNAVAILABLE"
    result["elapsed_ms"] = min(30000, max(0, round((monotonic() - start) * 1000)))
    return result
