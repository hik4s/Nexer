"""Synthetic process probe: visible picker code, headless test browser and clicks."""
from pathlib import Path
import sys
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "apps/recorder"))
from playwright.sync_api import BrowserType, Page
import pick_login

launch = BrowserType.launch
goto = Page.goto
def headless(self, *args, **kwargs):
    return launch(self, *args, **{**kwargs, "headless": True})
def interact(self, url, **kwargs):
    result = goto(self, url, **kwargs)
    self.locator("#user").click()
    self.locator("#pass").click()
    self.locator("#submit").click()
    return result

with patch.object(BrowserType, "launch", headless), patch.object(Page, "goto", interact):
    pick_login.main()
