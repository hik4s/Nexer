"""Visual inspection of the empty pairing page; never captures credentials."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
output = ROOT / "docs" / "development" / "previews"
output.mkdir(parents=True, exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto("http://127.0.0.1:5173", wait_until="networkidle")
    page.get_by_label("Código de pareamento").wait_for()
    assert page.get_by_label("Código de pareamento").input_value() == ""
    page.screenshot(path=str(output / "pairing-login.png"))
    print("PAIRING_UI_RENDERED")
    browser.close()
