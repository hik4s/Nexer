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
  let busyStates = new WeakMap(), pendingLoading = null;
  let generation = 0, previousActionAt = 0, lastActive = false, controller = null;
  const observers = new Map();
  const active = () => controller && !controller.signal.aborted && window.__nexerRecorderActive !== false;
  const budget = () => ({records: 0, controls: 0, nodes: 0, exceeded: false});
  const clear = () => {
    observed = new WeakMap(); changes = new WeakMap(); busyStates = new WeakMap();
    pendingLoading = null; generation = 0; previousActionAt = 0;
  };
  // Busy is a DOM state, not a word that may appear in private report data.
  const busyCandidate = element => element.matches(
    '[aria-busy],[role="progressbar"],[data-pc-name="progressspinner"]'
  );
  const busyNow = element => {
    if (!element.isConnected) return false;
    if (element.hasAttribute('aria-busy')) return element.getAttribute('aria-busy') === 'true' &&
      !element.closest('[hidden],[inert],[aria-hidden="true"]') && inspect(element).visible;
    if (!element.matches('[role="progressbar"],[data-pc-name="progressspinner"]')) return false;
    if (element.closest('[hidden],[inert],[aria-hidden="true"]')) return false;
    return inspect(element).visible;
  };
  const inScope = element => Boolean(pendingLoading?.scope && (
    pendingLoading.scope === element || pendingLoading.scope.contains(element)
  ));
  const observeBusy = (element, added) => {
    if (!busyCandidate(element) || forbidden(element)) return;
    const current = busyNow(element);
    const previous = busyStates.get(element);
    busyStates.set(element, current);
    if (!pendingLoading || !inScope(element) ||
        performance.now() - previousActionAt > 30000) return;
    if (current && (previous === false || (previous === undefined && added))) {
      // Bound the number of tracked active indicators per action.
      if (pendingLoading.active.size >= 32) { pendingLoading = null; return; }
      pendingLoading.busySeen = true;
      if (!pendingLoading.busySelector)
        pendingLoading.busySelector = window.__nexerStructuralSelector?.(element) || null;
      pendingLoading.active.add(element);
      pendingLoading.busyEnded = false;
    } else if (previous === true && !current && pendingLoading.active.has(element)) {
      pendingLoading.active.delete(element);
      if (pendingLoading.active.size === 0) pendingLoading.busyEnded = true;
    }
  };
  const observeRemoved = node => {
    if (!(node instanceof Element) || !pendingLoading) return;
    // Large virtualized tables and SPA route changes can detach huge subtrees;
    // inspect only the bounded set of already observed busy nodes.
    for (const activeNode of [...pendingLoading.active]) {
      if (node === activeNode || node.contains(activeNode)) pendingLoading.active.delete(activeNode);
    }
    if (pendingLoading.busySeen && pendingLoading.active.size === 0)
      pendingLoading.busyEnded = true;
  };
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
    if (state) {
      changes.set(element, {generation, state, at: performance.now()});
      // Newly enabled or visible controls are meaningful only in the region
      // where the immediately preceding action was performed.
      if (pendingLoading?.busySeen && inScope(element)) {
        pendingLoading.readyObserved = true;
        pendingLoading.readyElement = element;
        pendingLoading.readyState = state;
      }
    }
  };
  const observeRoot = root => {
    if (observers.has(root)) return;
    const observer = new MutationObserver(process);
    observer.observe(root, {subtree: true, childList: true, attributes: true,
      attributeFilter: ['disabled', 'aria-disabled', 'hidden', 'style', 'class',
        'aria-busy', 'aria-hidden', 'inert', 'role']});
    observers.set(root, observer);
  };
  const walk = (root, added, limits) => {
    if (limits.exceeded) return;
    if (root instanceof Element) {
      if (++limits.nodes > 1000) { limits.exceeded = true; return; }
      if (forbidden(root)) return;
      observeBusy(root, added);
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
      if (record.type === 'attributes') {
        // An aria-busy attribute may be created only after the action. Its
        // absence in the baseline is an idle state, not missing evidence.
        if (record.attributeName === 'aria-busy' || record.attributeName === 'role')
          observeBusy(record.target, true);
        walk(record.target, false, limits);
      }
      else {
        for (const node of record.removedNodes) observeRemoved(node);
        for (const node of record.addedNodes) if (node instanceof Element) walk(node, true, limits);
      }
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
  const recordAction = (element, action) => {
    if (!sync()) return;
    flush(); generation++; previousActionAt = performance.now();
    const scope = element instanceof Element && !forbidden(element)
      ? (element.closest('[data-nexer-scope],section,[role="region"],article,form,main') ||
        element.parentElement) : null;
    pendingLoading = scope ? {scope, action, generation, busySeen: false, busyEnded: false,
      readyObserved: false, active: new Set()} : null;
  };
  const outcomeForFinish = () => {
    if (!sync() || window !== window.top) return null;
    flush();
    const record = pendingLoading;
    if (!record || record.action !== 'click' || !record.busySeen || !record.busyEnded ||
        record.active.size || !record.readyObserved || !record.readyElement?.isConnected ||
        performance.now() - previousActionAt > 30000) return null;
    const readySelector = window.__nexerStructuralSelector?.(record.readyElement) || null;
    if (!record.busySelector || !readySelector) return null;
    // No text, attribute values, HTML, request payload or typed data.
    return {busy_selector: record.busySelector, ready_selector: readySelector,
      ready_state: record.readyState, confidence: 'high'};
  };
  const outcomeForNext = element => {
    if (!(element instanceof Element) || !pendingLoading ||
        pendingLoading.readyElement !== element) return null;
    return outcomeForFinish();
  };
  // No page text, control value, arbitrary HTML, selector or network payload is returned.
  // This is evidence for a future reviewable wait, not an executable recipe step.
  const loadingEvidence = () => {
    if (!sync()) return null;
    flush();
    if (!pendingLoading?.busySeen || performance.now() - previousActionAt > 30000) return null;
    const completed = pendingLoading.busyEnded && pendingLoading.active.size === 0;
    return {state: completed ? 'completed' : 'busy', busy_seen: true,
      busy_ended: completed, ready_observed: pendingLoading.readyObserved,
      confidence: completed ? (pendingLoading.readyObserved ? 'high' : 'medium') : 'low'};
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
  window.__nexerIntelligence = {install, reset, recordAction, readinessFor,
    loadingEvidence, outcomeForNext, outcomeForFinish};
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
