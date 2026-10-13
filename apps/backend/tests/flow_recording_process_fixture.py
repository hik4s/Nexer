"""Headless local fixture around the production private recorder process."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from playwright.sync_api import BrowserType, Page
launch, goto = BrowserType.launch, Page.goto
def headless(self, *args, **kwargs):
    kwargs["headless"] = True; return launch(self, *args, **kwargs)
def interact(self, *args, **kwargs):
    result = goto(self, *args, **kwargs)
    self.locator("#company").fill("recorded-value-canary")
    self.locator("#button").click()
    self.get_by_role("button", name="Parar gravação", exact=True).click()
    return result
BrowserType.launch = headless
Page.goto = interact
from record_flow import main
main()
