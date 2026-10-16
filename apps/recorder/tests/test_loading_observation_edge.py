"""Structural, scoped loading observations (no business text or network payloads).

These are evidence-only tests: the engine must not silently publish a wait step
until an executable, race-safe outcome contract is implemented and reviewed.
"""
import json
import os
import unittest

from playwright.sync_api import sync_playwright
from nexer_recorder.scripts import recorder_script


@unittest.skipUnless(os.getenv("NEXER_RUN_RECORDER_E2E") == "1", "Edge opt-in")
class LoadingObservationEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel="msedge", headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.addCleanup(self.page.close)
        self.events = []
        self.page.expose_binding("nexerCapture", lambda _source, event: self.events.append(event))

    def install(self, html):
        self.page.set_content(html)
        self.page.evaluate(recorder_script())

    def evidence(self):
        return self.page.evaluate("window.__nexerIntelligence.loadingEvidence()")

    def test_busy_then_ready_is_local_and_structural(self):
        self.install('''<section id="report"><button id="search" onclick="
            document.querySelector('#report').setAttribute('aria-busy','true');
            setTimeout(()=>{
              document.querySelector('#report').setAttribute('aria-busy','false');
              document.querySelector('#result').disabled=false;
            },80)">Pesquisar</button><button id="result" disabled>Export</button></section>''')
        self.page.locator("#search").click()
        self.page.wait_for_timeout(160)
        result = self.evidence()
        self.assertEqual(result, {"state": "completed", "busy_seen": True,
                                  "busy_ended": True, "ready_observed": True,
                                  "confidence": "high"})
        self.assertEqual([event["action"] for event in self.events], ["click"])
        self.assertNotIn("Pesquisar", json.dumps(result))
        self.assertNotIn("Export", json.dumps(result))

    def test_spinner_without_terminal_result_is_not_high_confidence(self):
        self.install('''<section id="region"><button id="go" onclick="
          document.querySelector('#progress').hidden=false;
          setTimeout(()=>document.querySelector('#progress').hidden=true,60)">Go</button>
          <div id="progress" role="progressbar" hidden></div></section>''')
        self.page.locator("#go").click()
        self.page.wait_for_timeout(125)
        self.assertEqual(self.evidence(), {"state": "completed", "busy_seen": True,
                         "busy_ended": True, "ready_observed": False, "confidence": "medium"})

    def test_unrelated_spinner_and_preexisting_busy_do_not_create_false_causality(self):
        self.install('''<section id="region"><button id="go" onclick="
            document.querySelector('#global-progress').hidden=false;
            setTimeout(()=>document.querySelector('#global-progress').hidden=true,35)">Go</button>
            </section><aside><div id="global-progress" role="progressbar" hidden></div></aside>''')
        self.page.locator("#go").click()
        self.page.wait_for_timeout(80)
        self.assertIsNone(self.evidence())

        self.page.set_content('''<section id="region" aria-busy="true"><button id="go" onclick="
            setTimeout(()=>document.querySelector('#region').setAttribute('aria-busy','false'),40)">Go</button></section>''')
        self.page.evaluate(recorder_script())
        self.page.locator("#go").click()
        self.page.wait_for_timeout(95)
        self.assertIsNone(self.evidence())

    def test_new_click_and_pause_reset_previous_busy_evidence(self):
        self.install('''<section id="region"><button id="go" onclick="
          document.querySelector('#region').setAttribute('aria-busy','true');
          setTimeout(()=>document.querySelector('#region').setAttribute('aria-busy','false'),50)">Go</button>
          <button id="other">Next</button></section>''')
        self.page.locator("#go").click()
        self.page.wait_for_timeout(105)
        self.assertEqual(self.evidence()["confidence"], "medium")
        self.page.locator("#other").click()
        self.assertIsNone(self.evidence())
        self.page.evaluate("window.__nexerRecorderActive=false;window.__nexerRecorderActive=true")
        self.assertIsNone(self.evidence())

    def test_secret_fields_and_loading_words_are_not_evidence(self):
        self.install('''<section><button id="go">Go</button>
          <label>Loading</label><input type="password" value="topsecret-canary">
          <p id="sentence">Carregando é apenas um texto no relatório</p></section>''')
        self.page.locator("#go").click()
        self.page.wait_for_timeout(25)
        self.assertIsNone(self.evidence())
        self.assertNotIn("topsecret-canary", json.dumps(self.events))

    def test_detached_busy_component_finishes_only_after_observed_active(self):
        self.install('''<section id="region"><button id="go" onclick="
          const item=document.createElement('div'); item.id='temporary';
          item.setAttribute('role','progressbar');
          document.querySelector('#region').append(item);
          setTimeout(()=>item.remove(),60)">Go</button></section>''')
        self.page.locator("#go").click()
        self.page.wait_for_timeout(120)
        self.assertEqual(self.evidence()["state"], "completed")
        self.assertEqual(self.evidence()["confidence"], "medium")

    def test_hidden_busy_does_not_prove_loading(self):
        self.install('''<section id="report">
            <button id="search" onclick="
              const hidden=document.querySelector('#indicator');
              hidden.setAttribute('aria-busy','true');
              setTimeout(()=>hidden.setAttribute('aria-busy','false'),40)">Search</button>
            <div id="indicator" hidden aria-busy="false">private-canary</div>
        </section>''')
        self.page.locator("#search").click()
        self.page.wait_for_timeout(90)
        self.assertIsNone(self.evidence())

    def test_large_removed_subtree_is_bounded_and_no_data_is_returned(self):
        self.install('''<section id="report"><button id="search" onclick="
          const box=document.createElement('div'); box.id='box';
          box.innerHTML='<div role=progressbar></div>' +
            '<div class=mass>' + '<span>private-canary</span>'.repeat(5000) + '</div>';
          document.querySelector('#report').appendChild(box);
          setTimeout(()=>box.remove(),40)">Search</button></section>''')
        self.page.locator("#search").click()
        self.page.wait_for_timeout(110)
        result = self.evidence()
        self.assertTrue(result is None or isinstance(result, dict))
        self.assertNotIn("private-canary", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
