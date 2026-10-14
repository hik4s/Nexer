"""One-shot, document-pinned query execution with ephemeral correlation."""
from copy import deepcopy
from time import monotonic

from query_contract import SAFE_QUERY_ERRORS, validate_query_step


class QueryExecutionError(RuntimeError):
    pass


def _fail(code):
    raise QueryExecutionError(code if code in SAFE_QUERY_ERRORS or code == 'EXECUTION_CANCELLED'
                              else 'QUERY_EXECUTION_FAILED')


def _remaining(deadline):
    return max(1, min(250, int((deadline - monotonic()) * 1000)))


# Only CSS queries in this document: no shadow piercing, arbitrary scripts, text or HTML extraction.
_PREPARE = r"""(root, cfg) => {
    const doc=root.ownerDocument;
    const visible = n => !!n && n.isConnected && n.getClientRects().length > 0 &&
        !['hidden','collapse'].includes(getComputedStyle(n).visibility);
    const identity = n => n == null || n === '' || /^[A-Za-z0-9_.-]{1,256}$/.test(n);
    const unique = selector => {
        const nodes=doc.querySelectorAll(selector);
        return nodes.length===1 ? nodes[0] : null;
    };
    // Parse every selector before allowing any effect, even when its target is not yet present.
    for(const selector of [cfg.selector,cfg.confirmation.selector,cfg.result.container,...Object.values(cfg.result.outcomes)])
        doc.querySelectorAll(selector);
    const c=unique(cfg.confirmation.selector), r=unique(cfg.result.container);
    if(!c || !r) return {error:'QUERY_BASELINE_UNAVAILABLE'};
    const old=[c.getAttribute(cfg.confirmation.attribute),r.getAttribute(cfg.result.attribute)];
    if(!old.every(identity)) return {error:'QUERY_IDENTITY_INVALID'};
    const state={root,doc,cfg,old,seen:null,error:null,armed:false,observer:null};
    state.check=()=>{
        if(!root.isConnected || doc.documentElement!==root) return {error:'QUERY_CONTEXT_MISMATCH'};
        const cs=doc.querySelectorAll(cfg.confirmation.selector), rs=doc.querySelectorAll(cfg.result.container);
        if(cs.length>1 || rs.length>1) return {error:'QUERY_OUTCOME_AMBIGUOUS'};
        const c=cs[0], r=rs[0];
        const cid=c?.getAttribute(cfg.confirmation.attribute), rid=r?.getAttribute(cfg.result.attribute);
        if(!identity(cid) || !identity(rid)) return {error:'QUERY_IDENTITY_INVALID'};
        if(state.error) return {error:state.error};
        if(state.armed && c && visible(c) && cid && !old.includes(cid)) {
            if(state.seen && state.seen!==cid) state.error='QUERY_SUPERSEDED';
            else state.seen=cid;
        }
        if(state.seen && cid && cid!==state.seen) state.error='QUERY_SUPERSEDED';
        if(state.seen && rid && rid!==state.seen && !old.includes(rid)) state.error='QUERY_SUPERSEDED';
        if(state.error) return {error:state.error};
        if(!c || !visible(c) || cid!==state.seen || !state.seen) return {confirmed:false};
        if(!r || !visible(r) || rid!==state.seen) return {confirmed:true};
        const active=[];
        for(const [name,selector] of Object.entries(cfg.result.outcomes)) {
            const nodes=selector.trim()===':scope' ? [r] : [...r.querySelectorAll(selector)];
            if(nodes.length>1) return {error:'QUERY_OUTCOME_AMBIGUOUS'};
            if(visible(nodes[0])) active.push(name);
        }
        if(!r.isConnected || r.getAttribute(cfg.result.attribute)!==state.seen) return {confirmed:true};
        if(active.length>1) return {error:'QUERY_OUTCOME_AMBIGUOUS'};
        return {confirmed:true,outcome:active[0]||null};
    };
    state.observer=new MutationObserver(()=>{if(state.armed) state.check()});
    state.observer.observe(root,{subtree:true,attributes:true,childList:true});
    return state;
}"""


def _resolved_step(step, context):
    resolved = deepcopy(step)
    resolved['selector'] = context.resolve(step['selector'])
    resolved['frames'] = [context.resolve(item) for item in step.get('frames', [])]
    resolved['confirmation']['selector'] = context.resolve(step['confirmation']['selector'])
    resolved['result']['container'] = context.resolve(step['result']['container'])
    resolved['result']['outcomes'] = {key: context.resolve(value) for key, value in step['result']['outcomes'].items()}
    validate_query_step(resolved)
    return resolved


def execute_query(step: dict, context) -> None:
    if context.dry_run:
        return
    deadline = monotonic() + step.get('timeout_ms', 180000) / 1000
    page, state, pin = context.page, None, None
    frame = None
    phase = 'QUERY_CONFIRMATION_TIMEOUT'

    def check():
        if context.is_cancellation_requested():
            _fail('EXECUTION_CANCELLED')
        if context.page is not page or page.is_closed():
            _fail('QUERY_CONTEXT_MISMATCH')
        if context.auth_guard is not None:
            try:
                authorized = context.auth_guard.ensure_authenticated(page)
            except Exception:
                _fail('QUERY_AUTHORIZATION_REVOKED')
            if authorized is not None and authorized is not page:
                _fail('QUERY_CONTEXT_MISMATCH')
        if monotonic() >= deadline:
            _fail(phase)

    def snapshot():
        check()
        try:
            data = frame.locator(':root').evaluate(
                '(root,s)=>root===s.root ? s.check() : {error:"QUERY_CONTEXT_MISMATCH"}',
                state, timeout=_remaining(deadline))
        except Exception:
            _fail('QUERY_CONTEXT_MISMATCH')
        if data.get('error'):
            _fail(data['error'])
        return data

    try:
        cfg = _resolved_step(step, context)
        check()
        frame = page.main_frame
        for selector in cfg['frames']:
            check()
            handle = frame.locator('css=' + selector).element_handle(timeout=_remaining(deadline))
            try:
                frame = handle.content_frame() if handle is not None else None
            finally:
                if handle is not None:
                    handle.dispose()
            if frame is None:
                _fail('QUERY_CONTEXT_MISMATCH')
        state = frame.locator(':root').evaluate_handle(_PREPARE, cfg, timeout=_remaining(deadline))
        error = state.evaluate('s=>s.error')
        if error:
            _fail(error)
        # Wait for native actionability without retrying a side effect. One native click follows.
        while True:
            snapshot()
            ready = state.evaluate('''s=>{const nodes=s.doc.querySelectorAll(s.cfg.selector);
                if(nodes.length!==1) return false; const b=nodes[0];
                return b.isConnected && b.getClientRects().length>0 && !b.disabled &&
                    b.getAttribute('aria-disabled')!=='true' && !['hidden','collapse'].includes(getComputedStyle(b).visibility)}''')
            if ready:
                break
            page.wait_for_timeout(min(100, _remaining(deadline)))
        check()
        pin = state.evaluate_handle('s=>s.doc.querySelector(s.cfg.selector)')
        state.evaluate('s=>{s.armed=true}')
        check()
        try:
            pin.as_element().click(button='left', click_count=1, timeout=_remaining(deadline), no_wait_after=True)
        except Exception:
            check()
            _fail('QUERY_EXECUTION_FAILED')
        while True:
            data = snapshot()
            if data.get('confirmed'):
                phase = 'QUERY_RESULT_TIMEOUT'
            if data.get('outcome'):
                check()
                final = snapshot()
                if final.get('outcome') != data['outcome']:
                    _fail('QUERY_OUTCOME_AMBIGUOUS')
                check()
                if data['outcome'] == 'empty':
                    _fail('QUERY_NO_DATA')
                if data['outcome'] == 'error':
                    _fail('QUERY_SITE_ERROR')
                return
            page.wait_for_timeout(min(100, _remaining(deadline)))
    except QueryExecutionError:
        raise
    except Exception:
        _fail('QUERY_EXECUTION_FAILED')
    finally:
        if state is not None:
            try:
                state.evaluate('s=>{s.observer?.disconnect();s.seen=null;s.old=null}')
            except Exception:
                pass  # A destroyed document has already removed its observers.
            try:
                state.dispose()
            except Exception:
                pass
        if pin is not None:
            try:
                pin.dispose()
            except Exception:
                pass
