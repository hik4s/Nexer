/* Local structural transitions. No values, text or network inspection. */
(() => {
  window.__nexerIntelligenceController?.abort();
  const controls = 'button,a,input,select,textarea,fieldset,form,[role="button"],[role="option"],[role="listbox"],[role="radiogroup"],[contenteditable]';
  const parent = element => element.parentElement || element.getRootNode().host || null;
  const forbidden = element => {
    for (let node = element; node instanceof Element; node = parent(node)) {
      if (node.matches('[data-nexer-recorder],input[type="password"],input[type="hidden"],input[type="file"]') ||
          /password|passwd|username|cre_username|cre_password|token|secret|credential/i.test(
            [node.getAttribute('name') || '', node.id || '', node.getAttribute('autocomplete') || ''].join(' ')) ||
          (node.matches('form') && node.querySelector('input[type="password"]'))) return true;
    }
    return false;
  };
  const inspect = element => {
    const visible = Boolean(element.isConnected && element.getClientRects().length &&
      !['hidden', 'collapse'].includes(getComputedStyle(element).visibility));
    let enabled = !element.matches(':disabled');
    for (let node = element; node instanceof Element; node = parent(node)) {
      if (node.getAttribute('aria-disabled') === 'true') enabled = false;
    }
    return {visible, enabled};
  };
  let observed = new WeakMap(), changes = new WeakMap();
  let generation = 0, previousActionAt = 0, lastActive = false, controller = null;
  const observers = new Map();
  const active = () => controller && !controller.signal.aborted && window.__nexerRecorderActive !== false;
  const budget = () => ({records: 0, controls: 0, nodes: 0, exceeded: false});
  const clear = () => { observed = new WeakMap(); changes = new WeakMap(); generation = 0; previousActionAt = 0; };
  const watch = (element, added, limits) => {
    if (!element.matches(controls) || forbidden(element)) return;
    if (++limits.controls > 250) { limits.exceeded = true; return; }
    const current = inspect(element), before = observed.get(element);
    observed.set(element, current);
    if (!generation || performance.now() - previousActionAt > 30000) return;
    let state = null;
    // An observed enable is stronger than visibility when both change together.
    if (before && !before.enabled && current.enabled && current.visible) state = 'enabled';
    else if (current.visible && ((before && !before.visible) || (!before && added))) state = 'visible';
    if (state) changes.set(element, {generation, state, at: performance.now()});
  };
  const observeRoot = root => {
    if (observers.has(root)) return;
    const observer = new MutationObserver(process);
    observer.observe(root, {subtree: true, childList: true, attributes: true,
      attributeFilter: ['disabled', 'aria-disabled', 'hidden', 'style', 'class']});
    observers.set(root, observer);
  };
  const walk = (root, added, limits) => {
    if (limits.exceeded) return;
    if (root instanceof Element) {
      if (++limits.nodes > 1000) { limits.exceeded = true; return; }
      if (forbidden(root)) return;
      watch(root, added, limits);
      if (root.shadowRoot) { observeRoot(root.shadowRoot); walk(root.shadowRoot, added, limits); }
    }
    for (let child = root.firstElementChild; child && !limits.exceeded; child = child.nextElementSibling) walk(child, added, limits);
  };
  const prune = () => {
    for (const [root, observer] of observers) if (root !== document && !root.host?.isConnected) {
      observer.disconnect(); observers.delete(root);
    }
  };
  const reset = () => {
    clear(); lastActive = Boolean(active());
    if (!lastActive) return;
    const limits = budget();
    walk(document, false, limits);
    // A bounded baseline is safe for the sampled controls. Unvisited controls
    // have no prior state, so they cannot produce a learned enable transition.
  };
  const sync = () => {
    const nowActive = Boolean(active());
    if (lastActive !== nowActive) reset();
    return nowActive;
  };
  function process(records) {
    prune();
    if (!sync()) return;
    const limits = budget();
    for (const record of records) {
      if (++limits.records > 200) { limits.exceeded = true; break; }
      if (record.type === 'attributes') walk(record.target, false, limits);
      else for (const node of record.addedNodes) if (node instanceof Element) walk(node, true, limits);
      if (limits.exceeded) break;
    }
    // A partial batch cannot substantiate a high-confidence inference.
    if (limits.exceeded) reset();
  }
  const flush = () => {
    const pending = [];
    for (const observer of observers.values()) pending.push(...observer.takeRecords());
    if (pending.length) process(pending);
  };
  const install = signal => {
    controller?.abort();
    controller = new AbortController();
    window.__nexerIntelligenceController = controller;
    if (signal.aborted) { controller.abort(); return; }
    signal.addEventListener('abort', () => controller.abort(), {once: true, signal: controller.signal});
    controller.signal.addEventListener('abort', () => {
      for (const observer of observers.values()) observer.disconnect();
      observers.clear(); clear(); lastActive = false;
    }, {once: true});
    observeRoot(document);
    window.addEventListener('blur', reset, {signal: controller.signal});
    reset();
  };
  const recordAction = () => {
    if (!sync()) return;
    flush(); generation++; previousActionAt = performance.now();
  };
  const readinessFor = element => {
    if (!sync() || !(element instanceof Element) || forbidden(element)) return null;
    flush();
    const observation = changes.get(element);
    if (!observation || observation.generation !== generation || !generation ||
        performance.now() - previousActionAt > 30000 || performance.now() - observation.at > 30000) return null;
    const now = inspect(element);
    changes.delete(element);
    return now.visible && (observation.state !== 'enabled' || now.enabled) ? {state: observation.state} : null;
  };
  window.__nexerIntelligence = {install, reset, recordAction, readinessFor};
  // Invalidate on the transition even when a pause/resume has no DOM event.
  let recorderActive = window.__nexerRecorderActive;
  Object.defineProperty(window, '__nexerRecorderActive', {configurable: true,
    get: () => recorderActive,
    set: value => {
      const wasActive = recorderActive !== false;
      recorderActive = value;
      if (wasActive !== (value !== false)) window.__nexerIntelligence?.reset();
    }
  });
})();
