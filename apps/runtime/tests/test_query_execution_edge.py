import json
import os
import tempfile
import time
import unittest

from playwright.sync_api import sync_playwright
from context import ExecutionContext
from runner import RecipeRunner
from test_query_recipe import query_recipe


@unittest.skipUnless(os.getenv('NEXER_RUN_RECORDER_E2E') == '1', 'Synthetic query Edge fixture')
class QueryEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(channel='msedge', headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.addCleanup(self.page.close)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.events = []
        self.context = ExecutionContext(self.page, {}, self.directory.name, emit=self.events.append)
        self.recipe = query_recipe()

    def fixture(self, script='', markup=''):
        self.page.set_content('''<button id="search">Consultar</button><button id="next">Next</button>
          <div id="confirmation" data-query-id="old" hidden></div>
          <div id="result" data-query-id="old"><span class="data">private-canary</span></div>''' + markup)
        self.page.evaluate('''script => {window.clicks=0; document.querySelector('#search').onclick=()=>{
            window.clicks++; const c=document.querySelector('#confirmation'), r=document.querySelector('#result');
            new Function('c','r',script)(c,r);
        };}''', script)

    def run_query(self, expected=None):
        result = RecipeRunner().run(self.recipe, self.context)
        self.assertEqual(result.error, expected)
        self.assertNotIn('private-canary', json.dumps(self.events) + str(result))
        self.assertNotIn('new-private-id', json.dumps(self.events) + str(result))
        return result

    def test_new_generation_with_identical_data_and_rebuilt_root(self):
        self.fixture("c.hidden=false; c.dataset.queryId='new-private-id'; setTimeout(()=>{r.outerHTML='<div id=\"result\" data-query-id=\"new-private-id\"><span class=\"data\">private-canary</span></div>';},150)")
        self.run_query()
        self.assertEqual(self.page.evaluate('clicks'), 1)

    def test_empty_and_error_interrupt_following_action(self):
        for outcome, code in [('empty', 'QUERY_NO_DATA'), ('error', 'QUERY_SITE_ERROR')]:
            with self.subTest(outcome=outcome):
                self.fixture(f"c.hidden=false;c.dataset.queryId='new-private-id';r.dataset.queryId='new-private-id';r.innerHTML='<span class={outcome}>private-canary</span>'")
                self.recipe['steps'] = self.recipe['steps'][:1] + [{'id': 'next', 'action': 'click', 'selector': '#missing-next'}]
                self.run_query(code)
                self.assertEqual(self.page.evaluate('clicks'), 1)

    def test_old_visible_result_does_not_complete(self):
        self.fixture("c.hidden=false;c.dataset.queryId='new-private-id'")
        self.run_query('QUERY_RESULT_TIMEOUT')
        self.assertEqual(self.page.evaluate('clicks'), 1)

    def test_hidden_old_confirmation_is_not_new(self):
        self.fixture('c.hidden=false')
        self.run_query('QUERY_CONFIRMATION_TIMEOUT')

    def test_ambiguous_outcomes_including_hidden_duplicates(self):
        for markup in ['<span class=data></span><span class=error></span>', '<span class=data></span><span hidden class=data></span>']:
            self.fixture("c.hidden=false;c.dataset.queryId='new-private-id';r.dataset.queryId='new-private-id';r.innerHTML=" + json.dumps(markup))
            self.run_query('QUERY_OUTCOME_AMBIGUOUS')

    def test_invalid_baseline_and_missing_or_duplicate_root_prevent_click(self):
        for change, code in [("document.querySelector('#result').remove()", 'QUERY_BASELINE_UNAVAILABLE'),
                             ("document.querySelector('#confirmation').dataset.queryId='invalid id'", 'QUERY_IDENTITY_INVALID'),
                             ("document.body.append(document.querySelector('#result').cloneNode(true))", 'QUERY_BASELINE_UNAVAILABLE')]:
            self.fixture()
            self.page.evaluate('change => {eval(change);}', change)
            self.run_query(code)
            self.assertEqual(self.page.evaluate('clicks'), 0)

    def test_other_generation_in_result_or_confirmation_is_rejected(self):
        for change in ["r.dataset.queryId='other'", "c.dataset.queryId='other'"]:
            self.fixture("c.hidden=false;c.dataset.queryId='new-private-id';setTimeout(()=>{" + change + "},120)")
            self.run_query('QUERY_SUPERSEDED')

    def test_cancel_during_wait_is_cancelled(self):
        self.fixture("c.hidden=false;c.dataset.queryId='new-private-id'")
        self.context.cancellation_requested = lambda: self.page.evaluate('clicks') > 0
        result = self.run_query()
        self.assertTrue(result.cancelled)
        self.assertEqual(self.page.evaluate('clicks'), 1)

    def test_cancel_during_preparation_prevents_effect(self):
        self.fixture()
        calls = [0]
        def cancelled():
            calls[0] += 1
            return calls[0] >= 3
        self.context.cancellation_requested = cancelled
        self.assertTrue(self.run_query().cancelled)
        self.assertEqual(self.page.evaluate('clicks'), 0)

    def test_authorization_revoked_during_wait(self):
        self.fixture("c.hidden=false;c.dataset.queryId='new-private-id'")
        page = self.page
        class Guard:
            def ensure_authenticated(self, current):
                if page.evaluate('clicks'):
                    raise RuntimeError('private-canary')
                return current
        self.context.auth_guard = Guard()
        self.run_query('QUERY_AUTHORIZATION_REVOKED')

    def test_final_check_can_cancel_before_accepting_data(self):
        self.fixture("c.hidden=false;c.dataset.queryId='new-private-id';r.dataset.queryId='new-private-id'")
        checks = [0]
        def cancelled():
            if self.page.evaluate('clicks'):
                checks[0] += 1
            return checks[0] >= 2
        self.context.cancellation_requested = cancelled
        self.assertTrue(self.run_query().cancelled)

    def test_final_authorization_cannot_replace_accepted_generation_or_document(self):
        cases = [(script, trigger) for trigger in (3, 4) for script in [
            "confirmation.dataset.queryId='other';result.dataset.queryId='other'",
            "document.open();document.write('<div>other document</div>');document.close()"]]
        for script, trigger in cases:
            with self.subTest(script=script, trigger=trigger):
                self.context.auth_guard = None
                self.fixture("c.hidden=false;c.dataset.queryId='new-private-id';r.dataset.queryId='new-private-id'")
                page = self.page
                class Guard:
                    after_click = 0
                    replaced = False
                    def ensure_authenticated(self, current):
                        if page.evaluate('clicks'):
                            self.after_click += 1
                            if self.after_click == trigger:
                                self.replaced = True
                                page.evaluate('script=>{eval(script)}', script)
                        return current
                guard = Guard()
                self.context.auth_guard = guard
                result = RecipeRunner().run(self.recipe, self.context)
                if guard.replaced:
                    self.assertIsNotNone(result.error)
                    self.assertEqual(result.completed_steps, 0)
                else:
                    self.assertEqual(page.locator('#result').get_attribute('data-query-id'), 'new-private-id')

    def test_same_task_confirmation_supersession_is_not_accepted(self):
        self.fixture("c.hidden=false;c.dataset.queryId='new-private-id';c.dataset.queryId='other';r.dataset.queryId='other'")
        self.run_query('QUERY_SUPERSEDED')

    def test_invalid_resolved_selector_is_sanitized_before_effect(self):
        for selector in ['[', '', 'x' * 2049]:
            self.fixture()
            self.recipe['variables'] = {'target': {'type': 'string', 'allow_empty': True}}
            self.recipe['steps'][0]['selector'] = '{{target}}'
            self.context.variables = {'target': selector}
            self.run_query('QUERY_EXECUTION_FAILED')
            self.assertEqual(self.page.evaluate('clicks'), 0)

    def test_unexpected_browser_errors_do_not_chain_private_details(self):
        import traceback
        from query_execution import execute_query, QueryExecutionError
        self.fixture()
        step = self.recipe['steps'][0]
        step['selector'] = '[private-canary=='
        try:
            execute_query(step, self.context)
        except QueryExecutionError as exc:
            self.assertEqual(str(exc), 'QUERY_EXECUTION_FAILED')
            self.assertNotIn('private-canary', ''.join(traceback.format_exception(exc)))
        else:
            self.fail('Invalid CSS must fail before clicking')

    def test_document_replaced_while_waiting_is_rejected(self):
        self.fixture("c.hidden=false;c.dataset.queryId='new-private-id';setTimeout(()=>location.href='data:text/html,replaced',120)")
        # Chromium blocks some data: navigations; use a same-page document rewrite.
        self.page.evaluate("() => {search.onclick=()=>{window.clicks++;setTimeout(()=>{document.open();document.write('<div>new document</div>');document.close()},120)};}")
        self.run_query('QUERY_CONTEXT_MISMATCH')

    def test_deadline_covers_unready_button_without_click_retry(self):
        self.fixture()
        self.page.locator('#search').evaluate('(b)=>b.disabled=true')
        started = time.monotonic()
        self.run_query('QUERY_CONFIRMATION_TIMEOUT')
        self.assertLess(time.monotonic() - started, 2.0)
        self.assertEqual(self.page.evaluate('clicks'), 0)

    def test_frame_document_navigation_is_rejected(self):
        self.page.set_content('<iframe></iframe>')
        frame = self.page.frames[1]
        frame.set_content('<button id="search">Go</button><div id="confirmation"></div><div id="result"></div>')
        frame.evaluate("() => {search.onclick=()=>{setTimeout(()=>{document.open();document.write('<div>replacement</div>');document.close()},100)};}")
        self.recipe['steps'][0]['frames'] = ['iframe']
        self.run_query('QUERY_CONTEXT_MISMATCH')

    def test_scope_outcome_and_success_continue(self):
        self.fixture("c.hidden=false;c.dataset.queryId='new-private-id';r.dataset.queryId='new-private-id';r.className='data'")
        self.recipe['steps'][0]['result']['outcomes']['data'] = ':scope'
        # Remove the child data signal; the root is the explicit terminal marker.
        self.page.locator('#result').evaluate('(r)=>r.replaceChildren()')
        self.recipe['steps'].append({'id': 'next', 'action': 'click', 'selector': '#next'})
        self.assertEqual(self.run_query().completed_steps, 2)

    def test_transient_confirmation_does_not_authorize_later_result(self):
        self.fixture("c.hidden=false;c.dataset.queryId='new-private-id';c.remove();r.dataset.queryId='new-private-id'")
        self.run_query('QUERY_CONFIRMATION_TIMEOUT')

    def test_preparation_time_is_not_excluded_from_deadline(self):
        self.fixture()
        page = self.page
        class SlowGuard:
            calls = 0
            def ensure_authenticated(self, current):
                self.calls += 1
                if self.calls == 2:
                    page.wait_for_timeout(1050)
                return current
        self.context.auth_guard = SlowGuard()
        self.run_query('QUERY_CONFIRMATION_TIMEOUT')
        self.assertEqual(self.page.evaluate('clicks'), 0)

    def test_authorization_replacing_page_is_context_loss(self):
        self.fixture()
        class Guard:
            calls = 0
            def ensure_authenticated(self, current):
                self.calls += 1
                return object() if self.calls >= 2 else current
        self.context.auth_guard = Guard()
        self.run_query('QUERY_CONTEXT_MISMATCH')
        self.assertEqual(self.page.evaluate('clicks'), 0)

    def test_observers_are_disconnected_after_success_and_failure(self):
        for script, code in [("c.hidden=false;c.dataset.queryId='new-private-id';r.dataset.queryId='new-private-id'", None), ('', 'QUERY_CONFIRMATION_TIMEOUT')]:
            self.fixture(script)
            self.page.evaluate('''() => {window.queryObservers=new Set();
                const Original=window.originalMutationObserver || window.MutationObserver;
                window.originalMutationObserver=Original;
                window.MutationObserver=class extends Original {
                    observe(node,options){if(node===document.documentElement) window.queryObservers.add(this);return super.observe(node,options)}
                    disconnect(){window.queryObservers.delete(this);return super.disconnect()}
                }}''')
            self.run_query(code)
            self.assertEqual(self.page.evaluate('queryObservers.size'), 0)
