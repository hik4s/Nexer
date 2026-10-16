"""Race-safe post-action wait for a structural outcome on the same document.

Only fixed, audited JavaScript is executed. Selectors come from a strictly
validated recipe. Neither DOM text nor field values are returned to Python.
"""
import time


class OutcomeWaitError(RuntimeError):
    pass


_ARM = r"""opts => {
  window.__nexerOutcomeProbe?.disconnect();
  const lookup = selector => {
    if (!selector) return null;
    const elements = document.querySelectorAll(selector);
    return elements.length === 1 ? elements[0] : null;
  };
  const visible = element => Boolean(element && element.isConnected &&
    !element.closest('[hidden],[inert],[aria-hidden="true"]') &&
    element.getClientRects().length && getComputedStyle(element).visibility === 'visible');
  const ready = () => {
    const element = lookup(opts.ready_selector);
    if (!visible(element)) return false;
    if (opts.ready_state === 'visible') return true;
    return !element.matches(':disabled') && element.getAttribute('aria-disabled') !== 'true';
  };
  const busy = () => visible(lookup(opts.busy_selector));
  const error = () => visible(lookup(opts.error_selector));
  let previousBusy = busy(), previousReady = ready();
  let busySeen = false, busyEnded = false, readyTransition = false, errorSeen = false;
  let invalid = false;
  const update = () => {
    try {
      const currentBusy = busy(), currentReady = ready();
      if (!previousBusy && currentBusy) busySeen = true;
      if (busySeen && previousBusy && !currentBusy) busyEnded = true;
      if (!previousReady && currentReady) readyTransition = true;
      if (error()) errorSeen = true;
      previousBusy = currentBusy; previousReady = currentReady;
    } catch (_) { invalid = true; }
  };
  try {
    if (!lookup(opts.ready_selector)) {
      // An initially absent target is acceptable, but the CSS must be valid.
      document.querySelectorAll(opts.ready_selector);
    }
    if (opts.busy_selector) document.querySelectorAll(opts.busy_selector);
    if (opts.error_selector) document.querySelectorAll(opts.error_selector);
  } catch (_) { return false; }
  const observer = new MutationObserver(update);
  observer.observe(document, {childList:true,subtree:true,attributes:true,
    attributeFilter:['hidden','style','class','disabled','aria-disabled','aria-hidden','inert']});
  const probe = {
    disconnect: () => observer.disconnect(),
    poll: () => {
      update();
      if (invalid) return 'invalid';
      if (errorSeen) return 'error';
      // Busy disappearance alone never proves a fresh result: require a
      // transition of the ready target from unready to ready.
      if (readyTransition && previousReady && !previousBusy &&
          (!busySeen || busyEnded)) return 'ready';
      return 'pending';
    }
  };
  window.__nexerOutcomeProbe = probe;
  return true;
}"""
_POLL = """() => window.__nexerOutcomeProbe?.poll() || 'not_armed'"""
_DISARM = """() => {window.__nexerOutcomeProbe?.disconnect();delete window.__nexerOutcomeProbe;}"""


def arm_outcome(context, wait_step: dict) -> None:
    """Must run immediately *before* the causal click, not after it."""
    if context.dry_run:
        context.outcome_pending = {"id": wait_step["id"], "page": context.page}
        return
    if context.is_cancellation_requested():
        raise OutcomeWaitError("EXECUTION_CANCELLED")
    selectors = {key: context.resolve(wait_step[key]) for key in
                 ("ready_selector", "busy_selector", "error_selector") if key in wait_step}
    selectors["ready_state"] = wait_step.get("ready_state", "visible")
    try:
        ok = context.page.evaluate(_ARM, selectors)
    except Exception:
        raise OutcomeWaitError("OUTCOME_ARM_FAILED") from None
    if not ok:
        raise OutcomeWaitError("OUTCOME_SELECTOR_INVALID")
    context.outcome_pending = {"id": wait_step["id"], "page": context.page}


def clear_outcome(context) -> None:
    previous = context.outcome_pending
    context.outcome_pending = None
    if previous and not context.dry_run:
        try:
            previous["page"].evaluate(_DISARM)
        except Exception:
            pass


def wait_for_outcome(step: dict, context) -> None:
    if not context.outcome_pending or context.outcome_pending["id"] != step["id"] or (
        context.outcome_pending["page"] is not context.page
    ):
        raise OutcomeWaitError("OUTCOME_NOT_ARMED")
    timeout = step.get("timeout_ms", 30000)
    deadline = time.monotonic() + timeout / 1000.0
    try:
        while True:
            if context.is_cancellation_requested():
                raise OutcomeWaitError("EXECUTION_CANCELLED")
            if context.dry_run:
                return
            try:
                state = context.page.evaluate(_POLL)
            except Exception:
                raise OutcomeWaitError("OUTCOME_CONTEXT_LOST") from None
            if state == "ready":
                return
            if state == "error":
                raise OutcomeWaitError("OUTCOME_ERROR_STATE")
            if state in {"invalid", "not_armed"}:
                raise OutcomeWaitError("OUTCOME_NOT_ARMED")
            if time.monotonic() >= deadline:
                raise OutcomeWaitError("OUTCOME_TIMEOUT")
            try:
                context.page.wait_for_timeout(min(100, max(1, int((deadline - time.monotonic()) * 1000))))
            except Exception:
                raise OutcomeWaitError("OUTCOME_CONTEXT_LOST") from None
    finally:
        clear_outcome(context)
