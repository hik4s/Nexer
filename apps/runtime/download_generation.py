"""Ephemeral correlation of a single request with a shared download collection."""
from functools import wraps
from fnmatch import fnmatchcase
from download_contract import SAFE_DOWNLOAD_ERRORS
import re
from time import monotonic
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


class DownloadGenerationError(RuntimeError):
    pass


def _fail(code):
    raise DownloadGenerationError(code if code in SAFE_DOWNLOAD_ERRORS or code == 'EXECUTION_CANCELLED' else 'DOWNLOAD_GENERATION_FAILED')


def _safe(operation):
    @wraps(operation)
    def wrapped(*args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except DownloadGenerationError:
            raise
        except Exception:
            _fail('DOWNLOAD_GENERATION_FAILED')
    return wrapped


def _remaining(deadline):
    return max(1, min(250, int((deadline - monotonic()) * 1000)))


def _check(context, deadline, code):
    if context.is_cancellation_requested():
        _fail('EXECUTION_CANCELLED')
    if context.auth_guard is not None:
        try:
            authorized_page = context.auth_guard.ensure_authenticated(context.page)
        except Exception:
            _fail('DOWNLOAD_AUTHORIZATION_REVOKED')
        if authorized_page is not None and authorized_page is not context.page:
            _fail("DOWNLOAD_CONTEXT_MISMATCH")
    if monotonic() >= deadline:
        _fail(code)


def _scope(step, context):
    scope = context.page
    for frame in step.get('frames', []):
        scope = scope.frame_locator(context.resolve(frame))
    return scope


def _collection(step, context):
    return {key: context.resolve(value) for key, value in step['collection'].items()}


def _state(context, reference, step):
    state = context.download_state.get(reference)
    if state is None:
        _fail('DOWNLOAD_GENERATION_UNAVAILABLE')
    if state['page'] is not context.page or state['frames'] != step.get('frames', []):
        _fail('DOWNLOAD_CONTEXT_MISMATCH')
    return state


_ROWS = r"""(root, c) => {
    const rows = Array.from(root.querySelectorAll(c.rows));
    const incomplete = !root.isConnected || root.ownerDocument.querySelectorAll(c.rows).length !== rows.length;
    if(rows.length > 1000) return {overflow:true, items:[]};
    return {overflow:false, incomplete, items:rows.map(row => {
        let nodes = c.name === ':scope' ? [row] : Array.from(row.querySelectorAll(c.name));
        if(nodes.length !== 1) return {invalid:true};
        const copy=nodes[0].cloneNode(true);
        copy.querySelectorAll('button,a,[role="button"],input,select,textarea,script,style').forEach(n=>n.remove());
        const name=(copy.textContent||'').replace(/\s+/g,' ').trim();
        const key=c.identity_attribute ? row.getAttribute(c.identity_attribute) : name;
        return {name,key};
    })};
}"""


def _rows(scope, collection, deadline, *, timeout_code='DOWNLOAD_BASELINE_UNAVAILABLE'):
    root = scope.locator(collection['container'])
    if root.count() != 1:
        _fail('DOWNLOAD_BASELINE_UNAVAILABLE')
    try:
        data = root.evaluate(_ROWS, collection, timeout=_remaining(deadline))
    except PlaywrightTimeoutError:
        _fail(timeout_code)
    if data['overflow'] or data.get('incomplete', False):
        _fail('DOWNLOAD_BASELINE_INCOMPLETE')
    for item in data['items']:
        if item.get('invalid') or not isinstance(item.get('key'), str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,256}', item['key']):
            _fail('DOWNLOAD_IDENTITY_INVALID')
    return data['items']


@_safe
def snapshot_downloads(step, context):
    context.event('action.started', action=step['action'], step_id=step['id'])
    if not context.dry_run:
        deadline = monotonic() + step.get('timeout_ms', 30000) / 1000
        _check(context, deadline, 'DOWNLOAD_BASELINE_UNAVAILABLE')
        collection = _collection(step, context)
        items = _rows(_scope(step, context), collection, deadline)
        _check(context, deadline, "DOWNLOAD_BASELINE_UNAVAILABLE")
        keys = [item['key'] for item in items]
        if collection.get('identity_attribute') and len(keys) != len(set(keys)):
            _fail('DOWNLOAD_IDENTITY_INVALID')
        if sum(state['kind'] == 'baseline' for state in context.download_state.values()) >= 50:
            _fail('DOWNLOAD_BASELINE_INCOMPLETE')
        context.download_state[step['id']] = dict(kind='baseline', page=context.page,
            frames=step.get('frames', []), collection=collection, identities=set(keys))
    context.event('action.finished', action=step['action'], step_id=step['id'])


def _confirmation(scope, source, context, deadline, *, require_visible=True):
    locator = scope.locator(context.resolve(source['selector']))
    count = locator.count()
    if count > 1:
        _fail('DOWNLOAD_CONFIRMATION_AMBIGUOUS')
    if not count or (require_visible and not locator.is_visible()):
        return None
    try:
        value = locator.get_attribute(source['attribute'], timeout=_remaining(deadline)) if 'attribute' in source else locator.text_content(timeout=_remaining(deadline))
    except PlaywrightTimeoutError:
        _check(context, deadline, 'DOWNLOAD_CONFIRMATION_TIMEOUT')
        if not require_visible:
            # Before the click, an unknown previous confirmation is never 'no confirmation'.
            _fail('DOWNLOAD_CONFIRMATION_TIMEOUT')
        # After the click, transient detachment is retried without dispatching another click.
        return None
    value = (value or '').strip()
    if not value:
        return None
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,256}', value):
        _fail('DOWNLOAD_IDENTITY_INVALID')
    return value


@_safe
def request_download(step, context):
    context.event('action.started', action=step['action'], step_id=step['id'])
    if not context.dry_run:
        baseline = _state(context, step['baseline'], step)
        deadline = monotonic() + step.get('timeout_ms', 180000) / 1000
        _check(context, deadline, 'DOWNLOAD_CONFIRMATION_TIMEOUT')
        scope = _scope(step, context)
        old = _confirmation(scope, step['confirmation'], context, deadline, require_visible=False)
        trigger = scope.locator(context.resolve(step['selector']))
        while True:
            _check(context, deadline, 'DOWNLOAD_CONFIRMATION_TIMEOUT')
            if trigger.count() == 1 and trigger.is_visible() and trigger.is_enabled(timeout=_remaining(deadline)):
                _check(context, deadline, 'DOWNLOAD_CONFIRMATION_TIMEOUT')
                # One dispatch only: even a click timeout must never resubmit a request.
                trigger.click(timeout=_remaining(deadline), no_wait_after=True)
                break
            context.page.wait_for_timeout(100)
        while True:
            _check(context, deadline, 'DOWNLOAD_CONFIRMATION_TIMEOUT')
            key = _confirmation(scope, step['confirmation'], context, deadline)
            _check(context, deadline, 'DOWNLOAD_CONFIRMATION_TIMEOUT')
            if key is not None and key != old and key not in baseline['identities']:
                context.download_state[step['id']] = dict(kind='generation', page=context.page,
                    frames=step.get('frames', []), baseline=step['baseline'], key=key)
                break
            context.page.wait_for_timeout(100)
    context.event('action.finished', action=step['action'], step_id=step['id'])


_CLICK = r"""(root, data) => {
    if(!root.isConnected) return false;
    const c=data.collection;
    const nameOf=row=>{
        const nodes=c.name === ':scope' ? [row] : Array.from(row.querySelectorAll(c.name));
        if(nodes.length!==1) return null;
        const copy=nodes[0].cloneNode(true);
        copy.querySelectorAll('button,a,[role="button"],input,select,textarea,script,style').forEach(n=>n.remove());
        return (copy.textContent||'').replace(/\s+/g,' ').trim();
    };
    const rows=Array.from(root.querySelectorAll(c.rows));
    if(rows.length>1000) return 'DOWNLOAD_BASELINE_INCOMPLETE';
    const matching=rows.filter(row=>(c.identity_attribute?row.getAttribute(c.identity_attribute):nameOf(row))===data.key);
    if(matching.length>1) return 'DOWNLOAD_MATCH_AMBIGUOUS';
    if(matching.length!==1) return false;
    const row=matching[0];
    if(!row.isConnected || nameOf(row)!==data.name) return false;
    const buttons=Array.from(row.querySelectorAll(c.button));
    if(buttons.length>1) return 'DOWNLOAD_BUTTON_AMBIGUOUS';
    if(buttons.length!==1) return false;
    const button=buttons[0];
    const style=getComputedStyle(button);
    if(!row.getClientRects().length || !button.getClientRects().length || ['hidden','collapse'].includes(style.visibility) ||
       button.matches(':disabled') || button.closest('[aria-disabled="true"]')) return false;
    button.click();
    return true;
}"""


@_safe
def correlated_download(step, context):
    generation = _state(context, step['generation'], step)
    baseline = _state(context, generation['baseline'], step)
    collection = _collection(step, context)
    if baseline['collection'] != collection:
        _fail('DOWNLOAD_CONTEXT_MISMATCH')
    deadline = monotonic() + step.get('timeout_ms', 180000) / 1000
    scope = _scope(step, context)
    while True:
        _check(context, deadline, 'DOWNLOAD_GENERATION_TIMEOUT')
        items = _rows(scope, collection, deadline, timeout_code='DOWNLOAD_GENERATION_TIMEOUT')
        matches = [(index, item) for index, item in enumerate(items)
                   if item['key'] == generation['key'] and item['key'] not in baseline['identities']
                   and fnmatchcase(item['name'], collection['pattern'])]
        if len(matches) > 1:
            _fail('DOWNLOAD_MATCH_AMBIGUOUS')
        if matches:
            _, item = matches[0]
            _check(context, deadline, 'DOWNLOAD_GENERATION_TIMEOUT')
            received = []
            def capture(download):
                received.append(download)
            context.page.on('download', capture)
            try:
                root = scope.locator(collection['container']).element_handle(timeout=_remaining(deadline))
                if root is None:
                    _fail('DOWNLOAD_BASELINE_UNAVAILABLE')
                try:
                    _check(context, deadline, 'DOWNLOAD_GENERATION_TIMEOUT')
                    clicked = root.evaluate(_CLICK, dict(collection=collection, key=generation['key'], name=item['name']))
                finally:
                    root.dispose()
                if isinstance(clicked, str):
                    _fail(clicked)
                if clicked:
                    while not received:
                        _check(context, deadline, 'DOWNLOAD_GENERATION_TIMEOUT')
                        context.page.wait_for_timeout(100)
                    _check(context, deadline, 'DOWNLOAD_GENERATION_TIMEOUT')
                    if len(received) != 1:
                        _fail('DOWNLOAD_MATCH_AMBIGUOUS')
                    return received[0]
            finally:
                context.page.remove_listener('download', capture)
        context.page.wait_for_timeout(100)
